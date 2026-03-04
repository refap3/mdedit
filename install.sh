#!/usr/bin/env bash
# One-line install:
#   bash <(curl -fsSL https://raw.githubusercontent.com/refap3/mdedit/main/install.sh)
set -euo pipefail

DEST="${MDEDIT_DIR:-$HOME/mdedit}"
VENV="$DEST/.venv"
BIN="${MDEDIT_BIN:-$HOME/.local/bin}"

# Already installed?
if [ -d "$DEST/.git" ]; then
    echo "MDEdit already installed at $DEST"
    echo "To update: bash $DEST/update.sh"
    exit 0
fi

# Clone
echo "Cloning mdedit into $DEST ..."
git clone --depth 1 https://github.com/refap3/mdedit "$DEST"

# Virtual environment
echo "Creating virtual environment ..."
python3 -m venv "$VENV"

# Dependencies
echo "Installing dependencies ..."
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$DEST/requirements.txt"

# Launcher scripts
mkdir -p "$BIN"
cat > "$BIN/mdedit" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/python" "$DEST/mdedit.py" "\$@"
EOF
chmod +x "$BIN/mdedit"

cat > "$BIN/mdedit-update" <<EOF
#!/usr/bin/env bash
exec bash "$DEST/update.sh"
EOF
chmod +x "$BIN/mdedit-update"
echo "Launchers: $BIN/mdedit, $BIN/mdedit-update"

# PATH hint if needed
case ":${PATH}:" in
    *":$BIN:"*) ;;
    *) echo "" && echo "NOTE: Add to your shell profile:  export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac

echo ""
echo "Done. Run: mdedit [file.md]"
