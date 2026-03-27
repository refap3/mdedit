#!/usr/bin/env python3
"""
MDEdit — A cross-platform Markdown editor built with PyQt6.
"""

import re
import sys
import os
from pathlib import Path

# Must be set before any Qt import — the WebEngine GPU process is spawned at import time.
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-logging --log-level=3")
os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;qt.webenginecontext.info=false")

from PyQt6.QtCore import (
    Qt, QTimer, QSettings, QSize, QPoint, QRect, QFileSystemWatcher,
)
from PyQt6.QtGui import (
    QAction, QColor, QFont, QIcon, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QShortcut, QSyntaxHighlighter, QTextCharFormat,
    QTextCursor, QTextDocument,
)
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QCheckBox,
    QMessageBox, QPushButton, QSplitter, QStatusBar, QTabWidget,
    QTextEdit, QToolButton, QVBoxLayout, QWidget, QScrollArea,
    QDialogButtonBox, QMenu,
)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

APP_NAME = "MDEdit"
ORG_NAME = "MDEdit"
VERSION = "1.4.0"
MAX_RECENT = 10


# ---------------------------------------------------------------------------
# Markdown Syntax Highlighter
# ---------------------------------------------------------------------------

class MarkdownHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for the Markdown editor pane."""

    def __init__(self, document, dark_mode=False):
        super().__init__(document)
        self.dark_mode = dark_mode
        self._build_rules()

    def _fmt(self, color, bold=False, italic=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(700)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def _build_rules(self):
        dm = self.dark_mode
        rules = []

        # Headings
        heading_color = "#569cd6" if dm else "#0550ae"
        for level in range(6, 0, -1):
            pattern = r"^#{" + str(level) + r"}(?!#)\s.*$"
            rules.append((re.compile(pattern, re.MULTILINE),
                          self._fmt(heading_color, bold=True)))

        # Bold+italic
        rules.append((re.compile(r"\*{3}.+?\*{3}|_{3}.+?_{3}"),
                      self._fmt("#c586c0" if dm else "#8250df", bold=True, italic=True)))

        # Bold
        rules.append((re.compile(r"\*{2}.+?\*{2}|_{2}.+?_{2}"),
                      self._fmt("#569cd6" if dm else "#0550ae", bold=True)))

        # Italic
        rules.append((re.compile(r"(?<!\*)\*(?!\*).+?(?<!\*)\*(?!\*)|(?<!_)_(?!_).+?(?<!_)_(?!_)"),
                      self._fmt("#9cdcfe" if dm else "#1a7f37", italic=True)))

        # Strikethrough
        strike_fmt = self._fmt("#808080" if dm else "#57606a")
        strike_fmt.setFontStrikeOut(True)
        rules.append((re.compile(r"~~.+?~~"), strike_fmt))

        # Inline code
        code_fmt = self._fmt("#ce9178" if dm else "#d97706")
        code_fmt.setFontFamily("monospace")
        rules.append((re.compile(r"`[^`]+`"), code_fmt))

        # Code fence lines
        fence_fmt = self._fmt("#6a9955" if dm else "#6e7781")
        fence_fmt.setFontFamily("monospace")
        rules.append((re.compile(r"^```.*$", re.MULTILINE), fence_fmt))

        # Blockquote
        rules.append((re.compile(r"^>.*$", re.MULTILINE),
                      self._fmt("#6a9955" if dm else "#57606a", italic=True)))

        # Links and images
        rules.append((re.compile(r"!?\[([^\]]*)\]\([^\)]*\)"),
                      self._fmt("#4ec9b0" if dm else "#0969da")))

        # Horizontal rule
        rules.append((re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE),
                      self._fmt("#808080")))

        # Unordered list bullets
        rules.append((re.compile(r"^[ \t]*[-*+] ", re.MULTILINE),
                      self._fmt("#dcdcaa" if dm else "#953800", bold=True)))

        # Ordered list numbers
        rules.append((re.compile(r"^[ \t]*\d+\. ", re.MULTILINE),
                      self._fmt("#dcdcaa" if dm else "#953800", bold=True)))

        # HTML tags
        rules.append((re.compile(r"<[^>]+>"),
                      self._fmt("#808080")))

        self._rules = rules

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

    def set_dark_mode(self, dark):
        self.dark_mode = dark
        self._build_rules()
        self.rehighlight()


# ---------------------------------------------------------------------------
# Editor Pane
# ---------------------------------------------------------------------------

class EditorPane(QTextEdit):
    """Plain-text editor for Markdown input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Menlo" if sys.platform == "darwin" else "Consolas")
        font.setPointSize(13)
        font.setFixedPitch(True)
        self.setFont(font)
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setTabStopDistance(28)


# ---------------------------------------------------------------------------
# Preview Pane
# ---------------------------------------------------------------------------

class PreviewPane(QWidget):
    """HTML preview, using QWebEngineView when available."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if HAS_WEBENGINE:
            self._view = QWebEngineView()
            layout.addWidget(self._view)
            self._use_web = True
        else:
            self._view = QTextEdit()
            self._view.setReadOnly(True)
            layout.addWidget(self._view)
            self._use_web = False

        self._dark_mode = False

    def set_dark_mode(self, dark):
        self._dark_mode = dark

    def set_html(self, html: str):
        full = self._wrap(html)
        if self._use_web:
            self._view.setHtml(full)
        else:
            self._view.setHtml(full)

    def _wrap(self, body: str) -> str:
        if self._dark_mode:
            bg, fg, code_bg, border = "#1e1e1e", "#d4d4d4", "#2d2d2d", "#3e3e3e"
            link = "#4ec9b0"
        else:
            bg, fg, code_bg, border = "#ffffff", "#24292f", "#f6f8fa", "#d0d7de"
            link = "#0969da"

        css = f"""
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            font-size: 15px;
            line-height: 1.7;
            color: {fg};
            background-color: {bg};
            max-width: 860px;
            margin: 0 auto;
            padding: 24px 32px;
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 1.2em;
            margin-bottom: 0.4em;
            font-weight: 600;
            line-height: 1.25;
        }}
        h1 {{ font-size: 2em; border-bottom: 1px solid {border}; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid {border}; padding-bottom: 0.3em; }}
        a {{ color: {link}; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        code {{
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 0.9em;
            background: {code_bg};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 0.15em 0.4em;
        }}
        pre {{
            background: {code_bg};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 14px 16px;
            overflow-x: auto;
            line-height: 1.5;
        }}
        pre code {{
            background: transparent;
            border: none;
            padding: 0;
            font-size: 0.88em;
        }}
        blockquote {{
            margin: 0;
            padding: 0 1em;
            color: {"#8b8b8b" if self._dark_mode else "#57606a"};
            border-left: 4px solid {border};
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        th, td {{
            border: 1px solid {border};
            padding: 6px 13px;
            text-align: left;
        }}
        th {{ background: {code_bg}; font-weight: 600; }}
        tr:nth-child(even) {{ background: {"#252525" if self._dark_mode else "#f6f8fa"}; }}
        img {{ max-width: 100%; }}
        hr {{ border: none; border-top: 1px solid {border}; margin: 1.5em 0; }}
        ul, ol {{ padding-left: 2em; }}
        li {{ margin: 0.25em 0; }}
        """

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Tab Data  (per-tab state + widgets)
# ---------------------------------------------------------------------------

class TabData:
    """Holds all state and widgets for a single editor tab."""

    def __init__(self):
        self.file_path: str | None = None
        self.is_modified: bool = False
        self.saving: bool = False
        self.file_mtime: float | None = None
        self.find_dialog: "FindReplaceDialog | None" = None
        self.saved_preview_size: int | None = None
        self.highlighter: "MarkdownHighlighter | None" = None

        self.editor = EditorPane()
        self.preview = PreviewPane()
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(300)


# ---------------------------------------------------------------------------
# Find & Replace Dialog
# ---------------------------------------------------------------------------

class FindReplaceDialog(QDialog):
    def __init__(self, editor: EditorPane, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Find & Replace")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.resize(420, 160)

        layout = QVBoxLayout(self)

        # Find row
        find_row = QHBoxLayout()
        find_row.addWidget(QLabel("Find:"))
        self.find_edit = QLineEdit()
        self.find_edit.returnPressed.connect(self.find_next)
        find_row.addWidget(self.find_edit)
        layout.addLayout(find_row)

        # Replace row
        replace_row = QHBoxLayout()
        replace_row.addWidget(QLabel("Replace:"))
        self.replace_edit = QLineEdit()
        replace_row.addWidget(self.replace_edit)
        layout.addLayout(replace_row)

        # Options
        opts_row = QHBoxLayout()
        self.case_cb = QCheckBox("Case sensitive")
        self.whole_cb = QCheckBox("Whole words")
        opts_row.addWidget(self.case_cb)
        opts_row.addWidget(self.whole_cb)
        opts_row.addStretch()
        self._match_label = QLabel("")
        opts_row.addWidget(self._match_label)
        layout.addLayout(opts_row)

        self.find_edit.textChanged.connect(self._update_match_count)
        self.case_cb.toggled.connect(self._update_match_count)
        self.whole_cb.toggled.connect(self._update_match_count)
        self.editor.document().contentsChanged.connect(self._update_match_count)

        # Buttons
        btn_row = QHBoxLayout()
        for label, slot in [
            ("Find Next", self.find_next),
            ("Replace", self.replace_one),
            ("Replace All", self.replace_all),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self.find_edit.setFocus()

    def _flags(self):
        flags = QTextDocument.FindFlag(0)
        if self.case_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.whole_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        return flags

    def _update_match_count(self):
        term = self.find_edit.text()
        if not term:
            self._match_label.setText("")
            return
        doc = self.editor.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        flags = self._flags()
        count = 0
        while True:
            cursor = doc.find(term, cursor, flags)
            if cursor.isNull():
                break
            count += 1
        if count == 0:
            self._match_label.setText("No matches")
        elif count == 1:
            self._match_label.setText("1 match")
        else:
            self._match_label.setText(f"{count} matches")

    def _highlight_current(self):
        match_cursor = self.editor.textCursor()
        if not match_cursor.hasSelection():
            self.editor.setExtraSelections([])
            return
        nav_cursor = QTextCursor(match_cursor)
        nav_cursor.setPosition(match_cursor.selectionEnd())
        self.editor.setTextCursor(nav_cursor)
        extra = QTextEdit.ExtraSelection()
        extra.cursor = match_cursor
        dark = getattr(self.parent(), "_dark_mode", False)
        if dark:
            extra.format.setBackground(QColor("#ffffff"))
            extra.format.setForeground(QColor("#000000"))
        else:
            extra.format.setBackground(QColor("#ffff00"))
            extra.format.setForeground(QColor("#000000"))
        self.editor.setExtraSelections([extra])

    def showEvent(self, event):
        super().showEvent(event)
        self._update_match_count()

    def closeEvent(self, event):
        self.editor.setExtraSelections([])
        super().closeEvent(event)

    def find_next(self):
        term = self.find_edit.text()
        if not term:
            return
        found = self.editor.find(term, self._flags())
        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(term, self._flags())
        self._highlight_current()

    def replace_one(self):
        term = self.find_edit.text()
        replacement = self.replace_edit.text()
        selections = self.editor.extraSelections()
        if selections and selections[0].cursor.hasSelection():
            c = selections[0].cursor
            if c.selectedText() == term:
                c.insertText(replacement)
                self.editor.setTextCursor(c)
        self.find_next()

    def replace_all(self):
        term = self.find_edit.text()
        replacement = self.replace_edit.text()
        if not term:
            return
        doc = self.editor.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        count = 0
        cursor.beginEditBlock()
        flags = self._flags()
        while True:
            cursor = doc.find(term, cursor, flags)
            if cursor.isNull():
                break
            cursor.insertText(replacement)
            count += 1
        cursor.endEditBlock()
        QMessageBox.information(self, "Replace All", f"Replaced {count} occurrence(s).")


# ---------------------------------------------------------------------------
# Help / Markdown Reference Dialog
# ---------------------------------------------------------------------------

HELP_MD = """\
# Markdown Reference

| Element | Syntax |
|---|---|
| H1 … H6 | `# H1` `## H2` `### H3` |
| **Bold** | `**text**` or `__text__` |
| *Italic* | `*text*` or `_text_` |
| ***Bold italic*** | `***text***` |
| ~~Strikethrough~~ | `~~text~~` |
| `Inline code` | `` `code` `` |
| Blockquote | `> text` |
| Horizontal rule | `---` |
| Link | `[label](url)` |
| Image | `![alt](url)` |
| Unordered list | `- item` or `* item` |
| Ordered list | `1. item` |
| Task list | `- [x] done` `- [ ] todo` |

## Code block
````
```bash
echo "hello"
```
````

## Table
```
| Col 1 | Col 2 |
|-------|-------|
| A     | B     |
```
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Markdown Reference")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.resize(700, 600)

        layout = QVBoxLayout(self)

        if HAS_WEBENGINE:
            view = QWebEngineView()
        else:
            view = QTextEdit()
            view.setReadOnly(True)

        pane = PreviewPane()
        if HAS_MARKDOWN:
            html_body = markdown.markdown(
                HELP_MD, extensions=["tables", "fenced_code"])
        else:
            html_body = f"<pre>{HELP_MD}</pre>"
        full_html = pane._wrap(html_body)

        if HAS_WEBENGINE:
            view.setHtml(full_html)
        else:
            view.setHtml(full_html)

        layout.addWidget(view)

        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        QShortcut(QKeySequence("Escape"), self, self.close)
        QShortcut(QKeySequence("Return"), self, self.close)


# ---------------------------------------------------------------------------
# Keyboard Shortcuts Dialog
# ---------------------------------------------------------------------------

SHORTCUTS = [
    ("File",        "New Tab",              "Ctrl+T"),
    ("File",        "Close Tab",            "Ctrl+W"),
    ("File",        "Open",                 "Ctrl+O"),
    ("File",        "Save",                 "Ctrl+S"),
    ("File",        "Save As",              "Ctrl+Shift+S"),
    ("File",        "Quit",                 "Ctrl+Q"),
    ("Edit",        "Undo",                 "Ctrl+Z"),
    ("Edit",        "Redo",                 "Ctrl+Y"),
    ("Edit",        "Cut",                  "Ctrl+X"),
    ("Edit",        "Copy",                 "Ctrl+C"),
    ("Edit",        "Paste",                "Ctrl+V"),
    ("Edit",        "Select All",           "Ctrl+A"),
    ("Edit",        "Find & Replace",       "Ctrl+F"),
    ("View",        "Toggle Preview",       "Ctrl+Shift+P"),
    ("View",        "Next Tab",             "Ctrl+Tab"),
    ("View",        "Prev Tab",             "Ctrl+Shift+Tab"),
    ("View",        "Zoom In",              "Ctrl+Shift+Up"),
    ("View",        "Zoom Out",             "Ctrl+Shift+Down"),
    ("View",        "Reset Zoom",           "Ctrl+0"),
    ("Format",      "Bold",                 "Ctrl+Shift+B"),
    ("Format",      "Italic",               "Ctrl+Shift+I"),
    ("Help",        "Markdown Reference",   "F1"),
    ("Help",        "Keyboard Shortcuts",   "Shift+F1"),
]


class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.resize(380, 480)

        layout = QVBoxLayout(self)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Menlo" if sys.platform == "darwin" else "Consolas", 12))

        rows = "\n".join(
            f"  {menu:<10} {action:<22} {keys}"
            for menu, action, keys in SHORTCUTS
        )
        text.setPlainText(f"{'Menu':<12} {'Action':<22} Shortcut\n"
                          f"{'-'*52}\n"
                          f"{rows}")
        layout.addWidget(text)

        btn = QPushButton("Close")
        btn.setDefault(True)
        btn.clicked.connect(self.close)
        layout.addWidget(btn)

        QShortcut(QKeySequence("Escape"), self, self.close)
        QShortcut(QKeySequence("Return"), self, self.close)


# ---------------------------------------------------------------------------
# App Icon
# ---------------------------------------------------------------------------

def _make_app_icon() -> QIcon:
    """Blue rounded-rect with 'MD' over 'edit' — used as window and dock icon."""
    size = 256
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#1e40af"))
    grad.setColorAt(1.0, QColor("#3b82f6"))
    p.setBrush(grad)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, size, size, 48, 48)

    f1 = QFont("Arial", 108, QFont.Weight.Bold)
    p.setFont(f1)
    p.setPen(QColor("#ffffff"))
    p.drawText(QRect(0, -18, size, size), Qt.AlignmentFlag.AlignCenter, "MD")

    f2 = QFont("Arial", 36, QFont.Weight.Normal)
    p.setFont(f2)
    p.setPen(QColor("#93c5fd"))
    p.drawText(QRect(0, 104, size, size), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "edit")

    p.end()
    return QIcon(pix)


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._dark_mode = False
        self._tabs: list[TabData] = []
        self._default_splitter_state: bytes | None = None

        # Single shared file watcher for all tabs — avoids PyQt6 lambda GC issues
        self._watcher = QFileSystemWatcher()
        self._watcher.fileChanged.connect(self._on_file_changed_externally)

        # Poll timer: checks current tab's mtime every 2s as a reliable fallback
        # (handles atomic-rename saves from vim etc. where watcher may miss the event)
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(2000)
        self._poll_timer.timeout.connect(self._poll_current_tab)
        self._poll_timer.start()

        self.settings = QSettings(ORG_NAME, APP_NAME)
        self._recent_files: list[str] = self.settings.value("recentFiles", []) or []

        self._build_ui()
        self._build_menus()
        self._build_toolbar()
        self._rebuild_open_recent_tb_menu()
        self._build_status_bar()
        self._restore_state()
        self._update_title()
        self._apply_theme()
        icon = _make_app_icon()
        self.setWindowIcon(icon)
        QApplication.instance().setWindowIcon(icon)

    # ---------------------------------------------------------------- Properties

    @property
    def _current_tab(self) -> TabData:
        idx = self._tab_widget.currentIndex()
        if 0 <= idx < len(self._tabs):
            return self._tabs[idx]
        return self._tabs[0]

    @property
    def editor(self) -> EditorPane:
        return self._current_tab.editor

    @property
    def preview(self) -> PreviewPane:
        return self._current_tab.preview

    @property
    def splitter(self) -> QSplitter:
        return self._current_tab.splitter

    @property
    def current_file(self) -> "str | None":
        return self._current_tab.file_path

    @current_file.setter
    def current_file(self, v: "str | None"):
        self._current_tab.file_path = v

    @property
    def is_modified(self) -> bool:
        return self._current_tab.is_modified

    @is_modified.setter
    def is_modified(self, v: bool):
        self._current_tab.is_modified = v

    @property
    def _saving(self) -> bool:
        return self._current_tab.saving

    @_saving.setter
    def _saving(self, v: bool):
        self._current_tab.saving = v

    @property
    def _saved_preview_size(self) -> "int | None":
        return self._current_tab.saved_preview_size

    @_saved_preview_size.setter
    def _saved_preview_size(self, v):
        self._current_tab.saved_preview_size = v

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        self._tab_widget = QTabWidget()
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.setMovable(True)
        self._tab_widget.tabCloseRequested.connect(self._close_tab)
        self._tab_widget.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tab_widget)
        self._new_tab()

    def _new_tab(self) -> TabData:
        tab = TabData()
        tab.preview.set_dark_mode(self._dark_mode)
        tab.highlighter = MarkdownHighlighter(tab.editor.document(), self._dark_mode)

        # Apply current word-wrap setting if available
        if hasattr(self, "word_wrap_action"):
            mode = (QTextEdit.LineWrapMode.WidgetWidth
                    if self.word_wrap_action.isChecked()
                    else QTextEdit.LineWrapMode.NoWrap)
            tab.editor.setLineWrapMode(mode)

        # Apply saved splitter proportion
        if self._default_splitter_state:
            tab.splitter.restoreState(self._default_splitter_state)

        # Connect per-tab signals using lambda captures
        tab.preview_timer.timeout.connect(lambda: self._refresh_preview_for(tab))
        tab.editor.textChanged.connect(lambda: self._on_text_changed_for(tab))
        tab.editor.cursorPositionChanged.connect(self._update_status)

        self._tabs.append(tab)
        idx = self._tab_widget.addTab(tab.splitter, "Untitled")
        self._tab_widget.setCurrentIndex(idx)
        return tab

    def _tab_label(self, tab: TabData) -> str:
        name = Path(tab.file_path).name if tab.file_path else "Untitled"
        return name + (" *" if tab.is_modified else "")

    def _update_tab_title(self, tab: TabData | None = None):
        if tab is None:
            tab = self._current_tab
        idx = self._tabs.index(tab)
        self._tab_widget.setTabText(idx, self._tab_label(tab))

    def _close_tab(self, idx: int):
        tab = self._tabs[idx]

        if tab.is_modified:
            self._tab_widget.setCurrentIndex(idx)
            name = Path(tab.file_path).name if tab.file_path else "Untitled"
            btn = QMessageBox.question(
                self, "Unsaved Changes",
                f"'{name}' has unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if btn == QMessageBox.StandardButton.Cancel:
                return
            if btn == QMessageBox.StandardButton.Save:
                if not self._save_tab(tab):
                    return

        # Clean up
        if tab.file_path and tab.file_path in self._watcher.files():
            self._watcher.removePath(tab.file_path)
        if tab.find_dialog:
            tab.find_dialog.close()

        self._tab_widget.removeTab(idx)
        self._tabs.pop(idx)

        if not self._tabs:
            self._new_tab()

    def _on_tab_changed(self, idx: int):
        if 0 <= idx < len(self._tabs):
            tab = self._tabs[idx]
            if tab.file_path and not tab.is_modified:
                self._check_external_change(tab)
        self._update_title()
        self._update_status()
        self._refresh_preview()

    def _check_external_change(self, tab: TabData):
        if not tab.file_path or not os.path.exists(tab.file_path):
            return
        try:
            mtime = os.path.getmtime(tab.file_path)
        except OSError:
            return
        if tab.file_mtime is not None and mtime > tab.file_mtime:
            self._reload_tab_silently(tab)

    def _poll_current_tab(self):
        """Fallback mtime poll — catches atomic-rename saves that confuse the watcher."""
        tab = self._current_tab
        if tab.file_path and not tab.is_modified and not tab.saving:
            self._check_external_change(tab)

    def _reload_tab_silently(self, tab: TabData):
        try:
            text = Path(tab.file_path).read_text(encoding="utf-8")
            mtime = os.path.getmtime(tab.file_path)
        except Exception:
            return
        tab.editor.blockSignals(True)
        tab.editor.setPlainText(text)
        tab.editor.blockSignals(False)
        tab.file_mtime = mtime
        tab.is_modified = False
        self._update_tab_title(tab)
        if tab is self._current_tab:
            self._update_title()
            self._update_status()
            self._refresh_preview()

    def _build_status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_pos = QLabel()
        self._status_words = QLabel()
        self._status_file = QLabel()
        sb.addWidget(self._status_pos)
        sb.addWidget(QLabel(" | "))
        sb.addWidget(self._status_words)
        sb.addWidget(QLabel(" | "))
        sb.addPermanentWidget(self._status_file)
        # cursorPositionChanged is connected per-tab in _new_tab

    # ---------------------------------------------------------------- Menus

    def _build_menus(self):
        mb = self.menuBar()

        # ---- File ----
        file_menu = mb.addMenu("&File")
        self._add_action(file_menu, "New &Tab", self.action_new,
                         QKeySequence("Ctrl+T"))
        self._add_action(file_menu, "&Close Tab", self.action_close_tab,
                         QKeySequence("Ctrl+W"))
        file_menu.addSeparator()
        self._add_action(file_menu, "&Open…", self.action_open,
                         QKeySequence("Ctrl+O"))
        self.recent_menu = file_menu.addMenu("Open &Recent")
        self._rebuild_recent_menu()
        file_menu.addSeparator()
        self._add_action(file_menu, "&Save", self.action_save,
                         QKeySequence("Ctrl+S"))
        self._add_action(file_menu, "Save &As…", self.action_save_as,
                         QKeySequence("Ctrl+Shift+S"))
        file_menu.addSeparator()
        self._add_action(file_menu, "Export &HTML…", self.action_export_html)
        file_menu.addSeparator()
        self._add_action(file_menu, "&Quit", self.close,
                         QKeySequence("Ctrl+Q"))

        # ---- Edit ----
        edit_menu = mb.addMenu("&Edit")
        self._add_action(edit_menu, "&Undo", self.editor.undo,
                         QKeySequence("Ctrl+Z"))
        self._add_action(edit_menu, "&Redo", self.editor.redo,
                         QKeySequence("Ctrl+Y"))
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Cu&t", self.editor.cut,
                         QKeySequence("Ctrl+X"))
        self._add_action(edit_menu, "&Copy", self.editor.copy,
                         QKeySequence("Ctrl+C"))
        self._add_action(edit_menu, "&Paste", self.editor.paste,
                         QKeySequence("Ctrl+V"))
        self._add_action(edit_menu, "Select &All", self.editor.selectAll,
                         QKeySequence("Ctrl+A"))
        edit_menu.addSeparator()
        self._add_action(edit_menu, "&Find & Replace…", self.action_find,
                         QKeySequence("Ctrl+F"))

        # ---- View ----
        view_menu = mb.addMenu("&View")
        self.toggle_preview_action = self._add_action(
            view_menu, "Toggle &Preview", self.action_toggle_preview,
            QKeySequence("Ctrl+Shift+P"))
        self.toggle_preview_action.setCheckable(True)
        self.toggle_preview_action.setChecked(True)

        self.word_wrap_action = self._add_action(
            view_menu, "&Word Wrap", self.action_toggle_wrap)
        self.word_wrap_action.setCheckable(True)
        self.word_wrap_action.setChecked(True)

        view_menu.addSeparator()
        self._add_action(view_menu, "Zoom &In", self.action_zoom_in,
                         QKeySequence("Ctrl+Shift+Up"))
        self._add_action(view_menu, "Zoom &Out", self.action_zoom_out,
                         QKeySequence("Ctrl+Shift+Down"))
        self._add_action(view_menu, "Reset &Zoom", self.action_zoom_reset,
                         QKeySequence("Ctrl+0"))
        view_menu.addSeparator()
        self.dark_mode_action = self._add_action(
            view_menu, "&Dark Mode", self.action_toggle_dark)
        self.dark_mode_action.setCheckable(True)

        # ---- Format ----
        fmt_menu = mb.addMenu("F&ormat")
        self._add_action(fmt_menu, "**Bold**", lambda: self._wrap_selection("**", "**"),
                         QKeySequence("Ctrl+Shift+B"))
        self._add_action(fmt_menu, "*Italic*", lambda: self._wrap_selection("*", "*"),
                         QKeySequence("Ctrl+Shift+I"))
        self._add_action(fmt_menu, "`Inline Code`", lambda: self._wrap_selection("`", "`"))
        self._add_action(fmt_menu, "Code Block", self._insert_code_block)
        fmt_menu.addSeparator()
        self._add_action(fmt_menu, "[Link](url)", self._insert_link)
        self._add_action(fmt_menu, "![Image](url)", self._insert_image)
        fmt_menu.addSeparator()
        self._add_action(fmt_menu, "Table", self._insert_table)
        self._add_action(fmt_menu, "Horizontal Rule", lambda: self._insert_text("\n---\n"))

        # ---- Help ----
        help_menu = mb.addMenu("&Help")
        self._add_action(help_menu, "Markdown &Reference", self.action_help,
                         QKeySequence("F1"))
        self._add_action(help_menu, "&Keyboard Shortcuts", self.action_shortcuts,
                         QKeySequence("Shift+F1"))
        help_menu.addSeparator()
        self._add_action(help_menu, "&About", self.action_about)

        # Tab navigation shortcuts — on macOS, Qt's "Ctrl" = Cmd, so use Meta for Ctrl key
        if sys.platform == "darwin":
            QShortcut(QKeySequence("Meta+Tab"), self, lambda: self._cycle_tab(1))
            QShortcut(QKeySequence("Meta+Shift+Tab"), self, lambda: self._cycle_tab(-1))
        else:
            QShortcut(QKeySequence("Ctrl+Tab"), self, lambda: self._cycle_tab(1))
            QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, lambda: self._cycle_tab(-1))

    def _add_action(self, menu, label, slot, shortcut=None):
        act = QAction(label, self)
        if shortcut:
            act.setShortcut(shortcut)
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    def _cycle_tab(self, direction: int):
        n = self._tab_widget.count()
        if n < 2:
            return
        idx = (self._tab_widget.currentIndex() + direction) % n
        self._tab_widget.setCurrentIndex(idx)

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))

        for label, slot in [("New Tab", self.action_new), ("Save", self.action_save)]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            tb.addAction(act)

        # Open split-button: click → open dialog, arrow → recent files
        open_btn = QToolButton()
        open_btn.setText("Open")
        open_btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        open_btn.clicked.connect(self.action_open)
        self._open_recent_tb_menu = QMenu(self)
        open_btn.setMenu(self._open_recent_tb_menu)
        self._open_tb_btn = open_btn
        tb.insertWidget(tb.actions()[1], open_btn)  # between New Tab and Save

        tb.addSeparator()

        for label, slot in [
            ("H1",  lambda: self._insert_heading(1)),
            ("H2",  lambda: self._insert_heading(2)),
            ("H3",  lambda: self._insert_heading(3)),
        ]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            tb.addAction(act)

        tb.addSeparator()

        for label, slot in [
            ("B",   lambda: self._wrap_selection("**", "**")),
            ("I",   lambda: self._wrap_selection("*", "*")),
            ("` `", lambda: self._wrap_selection("`", "`")),
        ]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            tb.addAction(act)

        tb.addSeparator()

        for label, slot in [
            ("bash",  self._insert_bash_block),
            ("tbl",   self._insert_table),
            ("1.",    self._insert_numbered_list),
            ("-",     self._insert_bullet_list),
            ("---",   lambda: self._insert_text("\n---\n")),
        ]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            tb.addAction(act)

        tb.addSeparator()
        act = QAction("Preview", self)
        act.setCheckable(True)
        act.setChecked(True)
        act.triggered.connect(self.action_toggle_preview)
        self._toolbar_preview_action = act
        tb.addAction(act)

        tb.addSeparator()
        act = QAction("Dark", self)
        act.setCheckable(True)
        act.triggered.connect(self.action_toggle_dark)
        self._toolbar_dark_action = act
        tb.addAction(act)

        tb.addSeparator()
        help_btn = QToolButton()
        help_btn.setText("Help")
        help_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        help_menu = QMenu(self)
        for label, slot in [
            ("Markdown Reference", self.action_help),
            ("Keyboard Shortcuts", self.action_shortcuts),
            ("About",              self.action_about),
        ]:
            a = QAction(label, self)
            a.triggered.connect(slot)
            help_menu.addAction(a)
        help_btn.setMenu(help_menu)
        tb.addWidget(help_btn)

    # -------------------------------------------------------- State / Title

    def _restore_state(self):
        geom = self.settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        else:
            self.resize(1100, 720)

        splitter_state = self.settings.value("splitterState")
        self._default_splitter_state = splitter_state

        dark = self.settings.value("darkMode", False, type=bool)
        self._dark_mode = dark
        self.dark_mode_action.setChecked(dark)
        if hasattr(self, "_toolbar_dark_action"):
            self._toolbar_dark_action.setChecked(dark)

        word_wrap = self.settings.value("wordWrap", True, type=bool)
        self.word_wrap_action.setChecked(word_wrap)
        self.action_toggle_wrap()

        # Restore open tabs
        open_tabs = self.settings.value("openTabs", []) or []
        active_file = self.settings.value("activeTabFile", None)
        valid_paths = [p for p in open_tabs if os.path.exists(p)]

        if valid_paths:
            # Load first file into the already-created initial empty tab
            self._load_file(valid_paths[0])
            for path in valid_paths[1:]:
                self._new_tab()
                self._load_file(path)
            # Restore active tab
            if active_file:
                for i, tab in enumerate(self._tabs):
                    if tab.file_path == active_file:
                        self._tab_widget.setCurrentIndex(i)
                        break

        # Apply splitter state to current tab
        if splitter_state:
            self.splitter.restoreState(splitter_state)

        preview_visible = self.settings.value("previewVisible", True, type=bool)
        if not preview_visible:
            self.action_toggle_preview(False)

    def _save_state(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitterState", self.splitter.saveState())
        self.settings.setValue("darkMode", self._dark_mode)
        self.settings.setValue("recentFiles", self._recent_files)
        self.settings.setValue("previewVisible", self.preview.isVisible())
        self.settings.setValue("wordWrap", self.word_wrap_action.isChecked())
        open_tabs = [tab.file_path for tab in self._tabs if tab.file_path]
        self.settings.setValue("openTabs", open_tabs)
        active = self._current_tab.file_path
        self.settings.setValue("activeTabFile", active)

    def _update_title(self):
        name = Path(self.current_file).name if self.current_file else "Untitled"
        mod = " *" if self.is_modified else ""
        self.setWindowTitle(f"{name}{mod} — {APP_NAME}")

    def _update_status(self):
        if not hasattr(self, "_status_pos"):
            return
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        text = self.editor.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        self._status_pos.setText(f"Ln {line}  Col {col}")
        self._status_words.setText(f"Words: {words}  Chars: {chars}")
        self._status_file.setText(self.current_file or "Untitled")

    # -------------------------------------------------- Recent Files

    def _add_recent(self, path: str):
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:MAX_RECENT]
        self._rebuild_recent_menu()

    def _shorten_path(self, path: str) -> str:
        try:
            return "~" + os.sep + str(Path(path).relative_to(Path.home()))
        except ValueError:
            return path

    def _rebuild_recent_menu(self):
        self.recent_menu.clear()
        if not self._recent_files:
            self.recent_menu.addAction("(none)").setEnabled(False)
        else:
            for path in self._recent_files:
                act = QAction(self._shorten_path(path), self)
                act.setData(path)
                act.triggered.connect(self._open_recent)
                self.recent_menu.addAction(act)
            self.recent_menu.addSeparator()
            clear_act = QAction("Clear Recent Files", self)
            clear_act.triggered.connect(self._clear_recent)
            self.recent_menu.addAction(clear_act)
        self._rebuild_open_recent_tb_menu()

    def _rebuild_open_recent_tb_menu(self):
        if not hasattr(self, "_open_recent_tb_menu"):
            return
        menu = self._open_recent_tb_menu
        menu.clear()
        if not self._recent_files:
            menu.addAction("(no recent files)").setEnabled(False)
            return
        for path in self._recent_files:
            act = QAction(self._shorten_path(path), self)
            act.setData(path)
            act.triggered.connect(self._open_recent)
            menu.addAction(act)

    def _open_recent(self):
        act = self.sender()
        path = act.data()
        if not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found",
                                f"The file could not be found:\n{path}")
            self._recent_files.remove(path)
            self._rebuild_recent_menu()
            return
        self._open_path(path)

    def _clear_recent(self):
        self._recent_files.clear()
        self._rebuild_recent_menu()

    # ------------------------------------------------ File operations

    def _open_path(self, path: str):
        """Open file, reusing current tab if empty+untitled, else a new tab."""
        tab = self._current_tab
        if tab.file_path is None and not tab.is_modified and not tab.editor.toPlainText().strip():
            self._load_file(path)
        else:
            self._new_tab()
            self._load_file(path)

    def _load_file(self, path: str):
        try:
            text = Path(path).read_text(encoding="utf-8")
            mtime = os.path.getmtime(path)
        except Exception as exc:
            QMessageBox.critical(self, "Open Error", str(exc))
            return
        tab = self._current_tab
        tab.editor.blockSignals(True)
        tab.editor.setPlainText(text)
        tab.editor.blockSignals(False)
        # Unwatch previous file if not open in any other tab
        old_path = tab.file_path
        if old_path and old_path != path:
            if not any(t.file_path == old_path for t in self._tabs if t is not tab):
                self._watcher.removePath(old_path)
        self._watcher.addPath(path)
        tab.file_path = path
        tab.file_mtime = mtime
        tab.is_modified = False
        self._add_recent(path)
        self._update_tab_title(tab)
        self._update_title()
        self._update_status()
        self._refresh_preview()

    def action_new(self):
        self._new_tab()

    def action_close_tab(self):
        self._close_tab(self._tab_widget.currentIndex())

    def action_open(self):
        last_dir = self.settings.value("lastDir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Markdown File", last_dir,
            "Markdown Files (*.md *.markdown *.txt);;All Files (*)")
        if path:
            self.settings.setValue("lastDir", str(Path(path).parent))
            self._open_path(path)

    def _save_tab(self, tab: TabData) -> bool:
        if not tab.file_path:
            # Need save-as: switch to this tab first
            self._tab_widget.setCurrentIndex(self._tabs.index(tab))
            return self.action_save_as()
        try:
            tab.saving = True
            QTimer.singleShot(500, lambda: setattr(tab, "saving", False))
            Path(tab.file_path).write_text(tab.editor.toPlainText(), encoding="utf-8")
            tab.file_mtime = os.path.getmtime(tab.file_path)
            tab.is_modified = False
            self._update_tab_title(tab)
            if tab is self._current_tab:
                self._update_title()
            return True
        except Exception as exc:
            tab.saving = False
            QMessageBox.critical(self, "Save Error", str(exc))
            return False

    def action_save(self) -> bool:
        tab = self._current_tab
        if not tab.file_path:
            return self.action_save_as()
        return self._save_tab(tab)

    def action_save_as(self) -> bool:
        last_dir = self.settings.value("lastDir", str(Path.home()))
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Markdown File", last_dir,
            "Markdown Files (*.md *.markdown);;All Files (*)")
        if not path:
            return False
        self.settings.setValue("lastDir", str(Path(path).parent))
        self._current_tab.file_path = path
        return self._save_tab(self._current_tab)

    def action_export_html(self):
        last_dir = self.settings.value("lastDir", str(Path.home()))
        path, _ = QFileDialog.getSaveFileName(
            self, "Export HTML", last_dir, "HTML Files (*.html);;All Files (*)")
        if not path:
            return
        html_body = self._render_markdown()
        full_html = self.preview._wrap(html_body)
        try:
            Path(path).write_text(full_html, encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))

    # -------------------------------------------------- Preview

    def _on_text_changed_for(self, tab: TabData):
        tab.is_modified = True
        self._update_tab_title(tab)
        if tab is self._current_tab:
            self._update_title()
        tab.preview_timer.start()

    def _on_file_changed_externally(self, path: str):
        # Re-watch: some editors delete+recreate files on save
        if path not in self._watcher.files() and os.path.exists(path):
            self._watcher.addPath(path)
        # Find which tab owns this path
        for tab in self._tabs:
            if tab.file_path == path:
                if tab.saving or tab.is_modified or not os.path.exists(path):
                    return
                if tab is self._current_tab:
                    self._reload_tab_silently(tab)
                # Background tabs: reloaded in _check_external_change on switch
                return

    def _render_markdown(self) -> str:
        text = self.editor.toPlainText()
        if HAS_MARKDOWN:
            extensions = [
                "tables", "fenced_code", "toc",
                "nl2br", "sane_lists",
            ]
            try:
                extensions.append("codehilite")
            except Exception:
                pass
            return markdown.markdown(text, extensions=extensions)
        else:
            import html as html_lib
            return f"<pre>{html_lib.escape(text)}</pre>"

    def _refresh_preview(self):
        self.preview.set_html(self._render_markdown())

    def _refresh_preview_for(self, tab: TabData):
        if tab is self._current_tab:
            self._refresh_preview()

    # ------------------------------------------------- View actions

    def action_toggle_preview(self, checked=None):
        if checked is None:
            checked = not self.preview.isVisible()
        if checked:
            self.preview.show()
            total = self.splitter.width()
            saved = self._saved_preview_size or (total // 2)
            self.splitter.setSizes([total - saved, saved])
        else:
            sizes = self.splitter.sizes()
            self._saved_preview_size = sizes[1] if sizes[1] > 10 else self.splitter.width() // 2
            self.preview.hide()
        self.toggle_preview_action.setChecked(checked)
        if hasattr(self, "_toolbar_preview_action"):
            self._toolbar_preview_action.setChecked(checked)

    def action_toggle_wrap(self):
        mode = (QTextEdit.LineWrapMode.WidgetWidth
                if self.word_wrap_action.isChecked()
                else QTextEdit.LineWrapMode.NoWrap)
        for tab in self._tabs:
            tab.editor.setLineWrapMode(mode)

    def action_zoom_in(self):
        for tab in self._tabs:
            tab.editor.zoomIn(2)

    def action_zoom_out(self):
        for tab in self._tabs:
            tab.editor.zoomOut(2)

    def action_zoom_reset(self):
        for tab in self._tabs:
            font = tab.editor.font()
            font.setPointSize(13)
            tab.editor.setFont(font)

    def action_toggle_dark(self):
        self._dark_mode = not self._dark_mode
        self.dark_mode_action.setChecked(self._dark_mode)
        if hasattr(self, "_toolbar_dark_action"):
            self._toolbar_dark_action.setChecked(self._dark_mode)
        self._apply_theme()
        self._refresh_preview()

    def _apply_theme(self):
        for tab in self._tabs:
            tab.preview.set_dark_mode(self._dark_mode)
            if tab.highlighter:
                tab.highlighter.set_dark_mode(self._dark_mode)
            else:
                tab.highlighter = MarkdownHighlighter(tab.editor.document(), self._dark_mode)

        if self._dark_mode:
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#d4d4d4"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#252525"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#d4d4d4"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#2d2d2d"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#d4d4d4"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#264f78"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            QApplication.instance().setPalette(palette)
        else:
            QApplication.instance().setPalette(QApplication.style().standardPalette())

    # ------------------------------------------------ Format actions

    def _wrap_selection(self, before: str, after: str):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            if text.startswith(before) and text.endswith(after) and len(text) > len(before) + len(after):
                cursor.insertText(text[len(before):-len(after)])
            else:
                cursor.insertText(f"{before}{text}{after}")
        else:
            cursor.insertText(f"{before}text{after}")
            pos = cursor.position()
            cursor.setPosition(pos - len(after) - len("text"))
            cursor.setPosition(pos - len(after), QTextCursor.MoveMode.KeepAnchor)
            self.editor.setTextCursor(cursor)

    def _insert_text(self, text: str):
        self.editor.textCursor().insertText(text)

    def _insert_code_block(self):
        cursor = self.editor.textCursor()
        sel = cursor.selectedText() if cursor.hasSelection() else "code here"
        cursor.insertText(f"\n```\n{sel}\n```\n")

    def _insert_link(self):
        cursor = self.editor.textCursor()
        sel = cursor.selectedText() if cursor.hasSelection() else "link text"
        cursor.insertText(f"[{sel}](url)")

    def _insert_image(self):
        cursor = self.editor.textCursor()
        sel = cursor.selectedText() if cursor.hasSelection() else "alt text"
        cursor.insertText(f"![{sel}](image.png)")

    def _insert_bash_block(self):
        cursor = self.editor.textCursor()
        sel = cursor.selectedText() if cursor.hasSelection() else 'echo "hello"'
        cursor.insertText(f"\n```bash\n{sel}\n```\n")

    def _insert_bullet_list(self):
        cursor = self.editor.textCursor()
        cursor.insertText("\n- item\n- item\n- item\n")

    def _insert_numbered_list(self):
        cursor = self.editor.textCursor()
        cursor.insertText("\n1. item\n2. item\n3. item\n")

    def _insert_heading(self, level: int):
        prefix = "#" * level + " "
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                            QTextCursor.MoveMode.KeepAnchor)
        line = cursor.selectedText()
        stripped = re.sub(r"^#{1,6}\s*", "", line)
        cursor.insertText(f"{prefix}{stripped}")

    def _insert_table(self):
        table = (
            "\n| Col 1 | Col 2 |\n"
            "|-------|-------|\n"
            "| A     | B     |\n"
        )
        self.editor.textCursor().insertText(table)

    # -------------------------------------------------- Help / About

    def action_find(self):
        tab = self._current_tab
        if tab.find_dialog is None:
            tab.find_dialog = FindReplaceDialog(tab.editor, self)
        tab.find_dialog.show()
        tab.find_dialog.raise_()
        tab.find_dialog.find_edit.setFocus()

    def action_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def action_shortcuts(self):
        dlg = ShortcutsDialog(self)
        dlg.exec()

    def action_about(self):
        has_web = "yes" if HAS_WEBENGINE else "no (using QTextBrowser)"
        has_md = "yes" if HAS_MARKDOWN else "no (install: pip install markdown)"
        import PyQt6.QtCore as _qtc
        qt_ver = _qtc.QT_VERSION_STR
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<b>{APP_NAME}</b> &nbsp; v{VERSION}<br>"
            f"A cross-platform Markdown editor<br><br>"
            f"Python: {py_ver}<br>"
            f"Qt: {qt_ver}<br>"
            f"WebEngine: {has_web}<br>"
            f"markdown library: {has_md}<br><br>"
            f"<a href='https://daringfireball.net/projects/markdown/'>Markdown Spec</a>",
        )

    # --------------------------------------------------- Close event

    def closeEvent(self, event):
        for i, tab in enumerate(self._tabs):
            if tab.is_modified:
                self._tab_widget.setCurrentIndex(i)
                name = Path(tab.file_path).name if tab.file_path else "Untitled"
                btn = QMessageBox.question(
                    self, "Unsaved Changes",
                    f"'{name}' has unsaved changes. Save before quitting?",
                    QMessageBox.StandardButton.Save |
                    QMessageBox.StandardButton.Discard |
                    QMessageBox.StandardButton.Cancel,
                )
                if btn == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return
                if btn == QMessageBox.StandardButton.Save:
                    if not self._save_tab(tab):
                        event.ignore()
                        return
        self._save_state()
        event.accept()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setStyle("Fusion")

    window = MainWindow()

    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path):
            window._open_path(os.path.abspath(path))

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
