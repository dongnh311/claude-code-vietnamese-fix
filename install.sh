#!/usr/bin/env bash
#
# Claude Code Vietnamese IME Fix - Installer
# Clone repo va chay interactive menu
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/dongnh311/claude-code-vietnamese-fix/main/install.sh | bash
#

set -euo pipefail

REPO_URL="https://github.com/dongnh311/claude-code-vietnamese-fix.git"
INSTALL_DIR="$HOME/.claude-vn-fix"

echo ""
echo "Claude Code Vietnamese IME Fix - Installer"
echo ""

# Check git
if ! command -v git &> /dev/null; then
    echo "[ERROR] git khong tim thay"
    echo "Cai dat: https://git-scm.com/downloads"
    exit 1
fi

# Check python
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &> /dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "[ERROR] Python khong tim thay"
    echo "Cai dat: https://python.org/downloads"
    exit 1
fi

# Clone or update
echo "-> Cai dat vao $INSTALL_DIR..."
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR"
    # Update remote URL if it changed (e.g. fork migration)
    CURRENT_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [ "$CURRENT_URL" != "$REPO_URL" ]; then
        echo "   Updating remote: $REPO_URL"
        git remote set-url origin "$REPO_URL"
    fi
    git pull origin main 2>/dev/null || true
else
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi
echo "   Done"
echo ""

# Run interactive menu (stdin from terminal for piped install)
cd "$INSTALL_DIR"
"$PYTHON_CMD" patcher.py < /dev/tty

echo ""
echo "================================================"
echo "Commands:"
echo "  Menu:    $PYTHON_CMD $INSTALL_DIR/patcher.py"
echo "  Auto:    $PYTHON_CMD $INSTALL_DIR/patcher.py --auto"
echo "  Restore: $PYTHON_CMD $INSTALL_DIR/patcher.py --restore"
echo "  Scan:    $PYTHON_CMD $INSTALL_DIR/patcher.py --scan"
echo "  Update:  cd $INSTALL_DIR && git pull"
echo "================================================"
echo ""
