# MDEdit

A lightweight, cross-platform Markdown editor built with Python and PyQt6.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4%2B-green)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)

## Version

Current release: **v1.5.0**

## Features

- **Multi-tab interface** — open multiple files simultaneously; tabs are closable and reorderable
- **Session restore** — all open tabs are re-opened automatically on next launch
- **Side-by-side live preview** — rendered HTML updates as you type (300 ms debounce)
- **GitHub-style CSS** — clean preview with dark/light mode support
- **Syntax highlighting** in the editor — headings, bold, italic, strikethrough, code, links, lists
- **Auto-reload** — detects external file changes and silently reloads (watcher + 2 s mtime poll); skips reload if you have unsaved edits; also checks on tab switch
- **File operations** — New Tab, Open (split toolbar button with Recent Files dropdown), Save, Save As, Export HTML, Export PDF, Open Recent (last 10, shortened paths)
- **Find & Replace** — per-tab dialog; case-sensitive and whole-word options, live match count, highlighted current match
- **Format helpers** — Bold, Italic, Inline Code, Code Block, Link, Image, Table, HR (re-applying a format toggles it off)
- **Markdown extensions** — tables, fenced code blocks, TOC, syntax-highlighted code (Pygments)
- **Persistent state** — window size, splitter position, dark mode, preview visibility, word wrap, recent files, open tabs
- **Toolbar Help menu** — Markdown Reference, Keyboard Shortcuts, and About accessible from a single toolbar dropdown
- **Custom app icon** — programmatic blue gradient icon, shown in window title bar and dock/taskbar
- **PDF export** — File › Export PDF… renders the preview to PDF (always light theme, so it prints cleanly)
- **Command-line** — open files, or export to PDF/HTML headlessly (see [Command line](#command-line))

## Command line

```
mdedit [OPTIONS] [FILE...]
```

| Command | Result |
|---|---|
| `mdedit` | Open the editor, restoring the last session |
| `mdedit notes.md` | Open `notes.md` in the editor |
| `mdedit --export-pdf notes.md` | Write `notes.pdf` next to the source, then exit |
| `mdedit --export-pdf notes.md -o /tmp/out.pdf` | Explicit output path |
| `mdedit --export-pdf *.md --out-dir ~/pdfs` | Batch export into a directory |
| `cat notes.md \| mdedit --export-pdf - -o out.pdf` | Read Markdown from stdin |
| `mdedit --export-html notes.md` | Same, but writes HTML |

| Option | Description |
|---|---|
| `-o`, `--output PATH` | Output file (single input only; conflicts with `--out-dir`) |
| `--out-dir DIR` | Output directory for batch exports (created if missing) |
| `--theme light\|dark` | Export colour theme (default: `light`) |
| `--page-size SIZE` | `A4`, `Letter` or `Legal` (default: `A4`) |
| `--margins MM` | Page margins in millimetres (default: `15`) |
| `--landscape` | Landscape orientation |
| `-v`, `--version` | Print version |
| `-h`, `--help` | Show help |

Export runs headless — no window is shown. Each written path is printed to stdout.
Exit codes: `0` success, `1` a file failed, `2` bad arguments.

PDF rendering uses WebEngine, so the output matches the preview. Without
PyQt6-WebEngine installed it falls back to Qt's `QTextDocument` renderer, which
supports a smaller subset of CSS.

## Screenshots

| Light mode | Dark mode |
|---|---|
| *(editor left, preview right)* | *(toggle via View › Dark Mode)* |

## Requirements

- Python 3.10+
- PyQt6
- PyQt6-WebEngine *(optional — falls back to QTextBrowser)*
- markdown
- Pygments

## Installation

**One-line install** (clones repo, creates venv, installs deps, adds `mdedit` command):

macOS / Linux:
```bash
curl -fsSL https://raw.githubusercontent.com/refap3/mdedit/main/install.sh | bash
```

Windows (PowerShell):
```powershell
irm https://raw.githubusercontent.com/refap3/mdedit/main/install.ps1 | iex
```

> **Windows:** open a new terminal after install for `mdedit` to be on PATH.

Then run:

```
mdedit [file.md]
```

**Update to latest version:**

```
mdedit-update
```

**Complete wipe (if install or update is broken):**

```bash
rm -rf ~/mdedit ~/.local/bin/mdedit ~/.local/bin/mdedit-update
```

Then re-run the one-line installer above.

**Manual install:**

```bash
git clone https://github.com/refap3/mdedit.git
cd mdedit
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python mdedit.py
```

## Keyboard Shortcuts

On macOS `Ctrl` = `⌘` except where noted with `^` (physical Control key).

| Action | Shortcut |
|---|---|
| New Tab | `Ctrl+T` |
| Close Tab | `Ctrl+W` |
| Next Tab | `^Tab` (Control+Tab) |
| Prev Tab | `^Shift+Tab` |
| Open | `Ctrl+O` |
| Save | `Ctrl+S` |
| Save As | `Ctrl+Shift+S` |
| Quit | `Ctrl+Q` |
| Undo / Redo | `Ctrl+Z` / `Ctrl+Y` |
| Cut / Copy / Paste | `Ctrl+X` / `Ctrl+C` / `Ctrl+V` |
| Select All | `Ctrl+A` |
| Find & Replace | `Ctrl+F` |
| Toggle Preview | `Ctrl+Shift+P` |
| Zoom In / Out | `Ctrl+Shift+Up` / `Ctrl+Shift+Down` |
| Reset Zoom | `Ctrl+0` |
| Bold | `Ctrl+Shift+B` |
| Italic | `Ctrl+Shift+I` |

## Man page

```bash
man mdedit
```

Requires the [alias](https://github.com/refap3/alias) repo to be installed (it sets `MANPATH`).
Or directly: `man ~/mdedit/man/man1/mdedit.1`

## Building a Mac .app + .dmg

```bash
./build.sh
```

Produces `dist/MDEdit.app` and `dist/MDEdit.dmg`.
`pyinstaller` is installed automatically into `.venv` if not present.

## Cleanup

After a build, these folders can be safely deleted:

```bash
rm -rf build/ dist/ __pycache__/
```

To also remove the virtual environment (~300 MB):

```bash
rm -rf build/ dist/ __pycache__/ .venv/
```

## Project Structure

```
mdedit/
├── mdedit.py          # Main application (single file)
├── mdedit.spec        # PyInstaller bundle config
├── build.sh           # Mac .app + .dmg build script
├── install.sh         # One-line installer (macOS/Linux)
├── install.ps1        # One-line installer (Windows)
├── update.sh          # Updater (macOS/Linux)
├── update.ps1         # Updater (Windows)
└── requirements.txt   # Python dependencies
```

## License

MIT
