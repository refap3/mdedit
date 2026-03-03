# MDEdit

A lightweight, cross-platform Markdown editor built with Python and PyQt6.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4%2B-green)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)

## Features

- **Side-by-side live preview** — rendered HTML updates as you type (300 ms debounce)
- **GitHub-style CSS** — clean preview with dark/light mode support
- **Syntax highlighting** in the editor — headings, bold, italic, code, links, lists
- **File operations** — New, Open, Save, Save As, Export HTML, Open Recent (last 10 files)
- **Find & Replace** — with case-sensitive and whole-word options
- **Format helpers** — Bold, Italic, Inline Code, Code Block, Link, Image, Table, HR
- **Markdown extensions** — tables, fenced code blocks, TOC, syntax-highlighted code (Pygments)
- **Persistent state** — window size, splitter position, dark mode, recent files
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

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/refap3/mdedit/main/install.sh)
```

Then run:

```bash
mdedit [file.md]
```

**Update to latest version:**

```bash
bash ~/mdedit/update.sh
```

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

## Building a Mac .app + .dmg

```bash
./build.sh
```

Produces `dist/MDEdit.app` and `dist/MDEdit.dmg`.
`pyinstaller` is installed automatically into `.venv` if not present.

## Project Structure

```
mdedit/
├── mdedit.py          # Main application (single file)
├── mdedit.spec        # PyInstaller bundle config
├── build.sh           # Mac .app + .dmg build script
├── install.sh         # One-line installer
├── update.sh          # Updater
└── requirements.txt   # Python dependencies
```

## License

MIT
