#!/bin/bash
# Install TrnsLate CPU-only (no GPU required)

set -e

# Check for Visual C++ Redistributable on Windows (needed by PyTorch)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    if ! ls /c/Windows/System32/vcruntime140.dll &>/dev/null && \
       ! ls /c/Windows/System32/VCRUNTIME140.dll &>/dev/null; then
        echo "[!] Microsoft Visual C++ Redistributable not found."
        echo "    PyTorch requires it to run on Windows."
        echo "    Download: https://aka.ms/vs/17/release/vc_redist.x64.exe"
        echo ""
        read -p "Continue anyway? [y/N] " choice
        [[ "$choice" != [yY]* ]] && exit 1
    fi
fi

echo "=== TrnsLate — CPU-only Installation ==="
echo ""

# Install torch CPU version first
echo "[1/2] Installing PyTorch (CPU only)..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
echo "[2/2] Installing TrnsLate dependencies..."
pip install -r requirements.txt

echo ""
echo "Done! Run with:  python main.py"
