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
    Qt, QTimer, QSettings, QSize, QPoint, QRect,
)
from PyQt6.QtGui import (
    QAction, QColor, QFont, QKeySequence, QPalette,
    QShortcut, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextDocument,
)
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QCheckBox,
    QMessageBox, QPushButton, QSplitter, QStatusBar,
    QTextEdit, QVBoxLayout, QWidget, QScrollArea,
    QDialogButtonBox,
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
        # Drop the active selection so it doesn't paint over the extra selection
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
            # Wrap around
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(term, self._flags())
        self._highlight_current()

    def replace_one(self):
        term = self.find_edit.text()
        replacement = self.replace_edit.text()
        # Use the extra selection's cursor (which holds the match) for replacement
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

        # Render via preview pane helper
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
    ("File",        "New",                  "Ctrl+N"),
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
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file: str | None = None
        self.is_modified = False
        self._find_dialog: FindReplaceDialog | None = None
        self._dark_mode = False

        self.settings = QSettings(ORG_NAME, APP_NAME)
        self._recent_files: list[str] = self.settings.value("recentFiles", []) or []

        self._build_ui()
        self._build_menus()
        self._build_toolbar()
        self._build_status_bar()
        self._restore_state()
        self._update_title()
        self._apply_theme()

        # Debounce timer for live preview
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(300)
        self._preview_timer.timeout.connect(self._refresh_preview)
        self.editor.textChanged.connect(self._on_text_changed)

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        hbox = QHBoxLayout(central)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor = EditorPane()
        self.preview = PreviewPane()

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        hbox.addWidget(self.splitter)

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
        self.editor.cursorPositionChanged.connect(self._update_status)

    # ---------------------------------------------------------------- Menus

    def _build_menus(self):
        mb = self.menuBar()

        # ---- File ----
        file_menu = mb.addMenu("&File")
        self._add_action(file_menu, "&New", self.action_new,
                         QKeySequence("Ctrl+N"))
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

    def _add_action(self, menu, label, slot, shortcut=None):
        act = QAction(label, self)
        if shortcut:
            act.setShortcut(shortcut)
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))

        for label, slot in [
            ("New", self.action_new),
            ("Open", self.action_open),
            ("Save", self.action_save),
        ]:
            act = QAction(label, self)
            act.triggered.connect(slot)
            tb.addAction(act)

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

    # -------------------------------------------------------- State / Title

    def _restore_state(self):
        geom = self.settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        else:
            self.resize(1100, 720)

        splitter_state = self.settings.value("splitterState")
        if splitter_state:
            self.splitter.restoreState(splitter_state)

        dark = self.settings.value("darkMode", False, type=bool)
        self._dark_mode = dark
        self.dark_mode_action.setChecked(dark)
        if hasattr(self, "_toolbar_dark_action"):
            self._toolbar_dark_action.setChecked(dark)

        preview_visible = self.settings.value("previewVisible", True, type=bool)
        if not preview_visible:
            self.action_toggle_preview(False)

        word_wrap = self.settings.value("wordWrap", True, type=bool)
        self.word_wrap_action.setChecked(word_wrap)
        self.action_toggle_wrap()

    def _save_state(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitterState", self.splitter.saveState())
        self.settings.setValue("darkMode", self._dark_mode)
        self.settings.setValue("recentFiles", self._recent_files)
        self.settings.setValue("previewVisible", self.preview.isVisible())
        self.settings.setValue("wordWrap", self.word_wrap_action.isChecked())

    def _update_title(self):
        name = Path(self.current_file).name if self.current_file else "Untitled"
        mod = " *" if self.is_modified else ""
        self.setWindowTitle(f"{name}{mod} — {APP_NAME}")

    def _update_status(self):
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
            return
        for path in self._recent_files:
            act = QAction(self._shorten_path(path), self)
            act.setData(path)
            act.triggered.connect(self._open_recent)
            self.recent_menu.addAction(act)
        self.recent_menu.addSeparator()
        clear_act = QAction("Clear Recent Files", self)
        clear_act.triggered.connect(self._clear_recent)
        self.recent_menu.addAction(clear_act)

    def _open_recent(self):
        act = self.sender()
        path = act.data()
        if not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found",
                                f"The file could not be found:\n{path}")
            self._recent_files.remove(path)
            self._rebuild_recent_menu()
            return
        if self._check_unsaved():
            self._load_file(path)

    def _clear_recent(self):
        self._recent_files.clear()
        self._rebuild_recent_menu()

    # ------------------------------------------------ File operations

    def _check_unsaved(self) -> bool:
        """Return True if safe to proceed (discard or saved)."""
        if not self.is_modified:
            return True
        name = Path(self.current_file).name if self.current_file else "Untitled"
        btn = QMessageBox.question(
            self, "Unsaved Changes",
            f"'{name}' has unsaved changes. Save before continuing?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
        )
        if btn == QMessageBox.StandardButton.Save:
            return self.action_save()
        elif btn == QMessageBox.StandardButton.Discard:
            return True
        return False

    def _load_file(self, path: str):
        try:
            text = Path(path).read_text(encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Open Error", str(exc))
            return
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self.current_file = path
        self.is_modified = False
        self._add_recent(path)
        self._update_title()
        self._update_status()
        self._refresh_preview()

    def action_new(self):
        if not self._check_unsaved():
            return
        self.editor.clear()
        self.current_file = None
        self.is_modified = False
        self._update_title()
        self._update_status()
        self._refresh_preview()

    def action_open(self):
        if not self._check_unsaved():
            return
        last_dir = self.settings.value("lastDir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Markdown File", last_dir,
            "Markdown Files (*.md *.markdown *.txt);;All Files (*)")
        if path:
            self.settings.setValue("lastDir", str(Path(path).parent))
            self._load_file(path)

    def action_save(self) -> bool:
        if not self.current_file:
            return self.action_save_as()
        try:
            Path(self.current_file).write_text(
                self.editor.toPlainText(), encoding="utf-8")
            self.is_modified = False
            self._update_title()
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            return False

    def action_save_as(self) -> bool:
        last_dir = self.settings.value("lastDir", str(Path.home()))
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Markdown File", last_dir,
            "Markdown Files (*.md *.markdown);;All Files (*)")
        if not path:
            return False
        self.settings.setValue("lastDir", str(Path(path).parent))
        self.current_file = path
        return self.action_save()

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

    def _on_text_changed(self):
        self.is_modified = True
        self._update_title()
        self._preview_timer.start()

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
            # Very basic fallback: escape HTML
            import html as html_lib
            return f"<pre>{html_lib.escape(text)}</pre>"

    def _refresh_preview(self):
        self.preview.set_html(self._render_markdown())

    # ------------------------------------------------- View actions

    def action_toggle_preview(self, checked=None):
        # `checked` is passed by checkable QAction's triggered(bool) signal.
        # When called without it (e.g. from shortcut via non-checkable path),
        # derive the desired state from current visibility.
        if checked is None:
            checked = not self.preview.isVisible()
        if checked:
            self.preview.show()
            total = self.splitter.width()
            saved = getattr(self, "_saved_preview_size", total // 2)
            self.splitter.setSizes([total - saved, saved])
        else:
            sizes = self.splitter.sizes()
            self._saved_preview_size = sizes[1] if sizes[1] > 10 else self.splitter.width() // 2
            self.preview.hide()
        self.toggle_preview_action.setChecked(checked)
        if hasattr(self, "_toolbar_preview_action"):
            self._toolbar_preview_action.setChecked(checked)

    def action_toggle_wrap(self):
        if self.word_wrap_action.isChecked():
            self.editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

    def action_zoom_in(self):
        self.editor.zoomIn(2)

    def action_zoom_out(self):
        self.editor.zoomOut(2)

    def action_zoom_reset(self):
        font = self.editor.font()
        font.setPointSize(13)
        self.editor.setFont(font)

    def action_toggle_dark(self):
        self._dark_mode = not self._dark_mode
        self.dark_mode_action.setChecked(self._dark_mode)
        if hasattr(self, "_toolbar_dark_action"):
            self._toolbar_dark_action.setChecked(self._dark_mode)
        self._apply_theme()
        self._refresh_preview()

    def _apply_theme(self):
        self.preview.set_dark_mode(self._dark_mode)
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

        # Rebuild highlighter with new theme
        if hasattr(self, "_highlighter"):
            self._highlighter.set_dark_mode(self._dark_mode)
        else:
            self._highlighter = MarkdownHighlighter(
                self.editor.document(), self._dark_mode)

    # ------------------------------------------------ Format actions

    def _wrap_selection(self, before: str, after: str):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            # Toggle: unwrap if already wrapped, otherwise wrap
            if text.startswith(before) and text.endswith(after) and len(text) > len(before) + len(after):
                cursor.insertText(text[len(before):-len(after)])
            else:
                cursor.insertText(f"{before}{text}{after}")
        else:
            cursor.insertText(f"{before}text{after}")
            # Move cursor back to select placeholder
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
        # Strip any existing heading prefix then apply the new one
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
        if self._find_dialog is None:
            self._find_dialog = FindReplaceDialog(self.editor, self)
        self._find_dialog.show()
        self._find_dialog.raise_()
        self._find_dialog.find_edit.setFocus()

    def action_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def action_shortcuts(self):
        dlg = ShortcutsDialog(self)
        dlg.exec()

    def action_about(self):
        has_web = "yes" if HAS_WEBENGINE else "no (using QTextBrowser)"
        has_md = "yes" if HAS_MARKDOWN else "no (install: pip install markdown)"
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<b>{APP_NAME}</b><br>"
            f"A cross-platform Markdown editor<br><br>"
            f"PyQt6 WebEngine: {has_web}<br>"
            f"markdown library: {has_md}<br><br>"
            f"<a href='https://daringfireball.net/projects/markdown/'>Markdown Spec</a>",
        )

    # --------------------------------------------------- Close event

    def closeEvent(self, event):
        if self._check_unsaved():
            self._save_state()
            event.accept()
        else:
            event.ignore()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setStyle("Fusion")

    window = MainWindow()

    # Open file passed as argument
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isfile(path):
            window._load_file(os.path.abspath(path))

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
