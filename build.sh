#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PYINSTALLER="$VENV/bin/pyinstaller"

# Install PyInstaller if not present
if [ ! -f "$PYINSTALLER" ]; then
    echo "Installing PyInstaller..."
    "$VENV/bin/pip" install pyinstaller
fi

cd "$SCRIPT_DIR"

# Build .app bundle using spec (required for WebEngine configuration)
"$PYINSTALLER" --clean --noconfirm mdedit.spec

# Create .dmg
echo ""
echo "Creating .dmg..."
STAGING="$(mktemp -d)"
cp -r dist/MDEdit.app "$STAGING/"
ln -s /Applications "$STAGING/Applications"
hdiutil create \
    -volname MDEdit \
    -srcfolder "$STAGING" \
    -ov -format UDZO \
    dist/MDEdit.dmg
rm -rf "$STAGING"

echo ""
echo "Done."
echo "  App bundle : dist/MDEdit.app"
echo "  Disk image : dist/MDEdit.dmg"
echo ""
echo "Run with: open dist/MDEdit.app"
