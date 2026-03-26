# MDEdit

A lightweight, cross-platform Markdown editor built with Python and PyQt6.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4%2B-green)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)

## Features

- **Side-by-side live preview** — rendered HTML updates as you type (300 ms debounce)
- **GitHub-style CSS** — clean preview with dark/light mode support
- **Syntax highlighting** in the editor — headings, bold, italic, strikethrough, code, links, lists
- **Auto-reload** — detects external file changes and silently reloads (like VS Code); skips reload if you have unsaved edits
- **File operations** — New, Open (split toolbar button with Recent Files dropdown), Save, Save As, Export HTML, Open Recent (last 10, shortened paths)
- **Find & Replace** — case-sensitive and whole-word options, live match count, highlighted current match
- **Format helpers** — Bold, Italic, Inline Code, Code Block, Link, Image, Table, HR (re-applying a format toggles it off)
- **Markdown extensions** — tables, fenced code blocks, TOC, syntax-highlighted code (Pygments)
- **Persistent state** — window size, splitter position, dark mode, preview visibility, word wrap, recent files
- **Command-line** — open a file directly: `python3 mdedit.py file.md`

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

| Action | Shortcut |
|---|---|
| New | `Ctrl+N` |
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
