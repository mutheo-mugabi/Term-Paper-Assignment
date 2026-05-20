#!/usr/bin/env bash
# Install Fast Downward planner
# Usage: bash scripts/install_fd.sh [install_dir]
set -e
INSTALL_DIR="${1:-$(dirname "$0")/../fast-downward}"
echo "Installing Fast Downward to: $INSTALL_DIR"
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory already exists. Skipping clone."
else
    git clone https://github.com/aibasel/downward.git "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
python3 build.py
echo ""
echo "Done. Set your environment:"
echo "  export FD_PATH=$(realpath fast-downward.py)"
