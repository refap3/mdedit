#!/usr/bin/env bash
# Update MDEdit to the latest version.
# Usage: bash update.sh
set -euo pipefail

DEST="${MDEDIT_DIR:-$HOME/mdedit}"
VENV="$DEST/.venv"

if [ ! -d "$DEST/.git" ]; then
    echo "MDEdit not found at $DEST"
    echo "Install first:"
    echo "  bash <(curl -fsSL https://raw.githubusercontent.com/refap3/mdedit/main/install.sh)"
    exit 1
fi

echo "Updating MDEdit ..."
git -C "$DEST" pull

echo "Updating dependencies ..."
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$DEST/requirements.txt"

echo ""
echo "Done. $(git -C "$DEST" log -1 --format='%h — %s')"
