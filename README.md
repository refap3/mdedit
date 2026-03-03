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

```bash
git clone https://github.com/rainers/mdedit.git
cd mdedit
pip install -r requirements.txt
python3 mdedit.py
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
python3 build.py
```

Produces `dist/MDEdit.app` and `dist/MDEdit-1.0.0.dmg`.
Requires `pyinstaller` (installed automatically by the script).

## Project Structure

```
mdedit/
├── mdedit.py          # Main application (single file)
├── mdedit.spec        # PyInstaller bundle config
├── build.py           # Mac .app + .dmg build script
└── requirements.txt   # Python dependencies
```

## License

MIT
