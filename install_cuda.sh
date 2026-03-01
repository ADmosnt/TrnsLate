#!/bin/bash
# Install TrnsLate with CUDA GPU support
#
# Usage:
#   ./install_cuda.sh          # stable cu126 (recommended)
#   ./install_cuda.sh cu128    # nightly cu128 (requires CUDA Toolkit 12.8)

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

CUDA_VERSION="${1:-cu126}"

if [ "$CUDA_VERSION" = "cu128" ]; then
    echo "=== TrnsLate — CUDA cu128 Installation (nightly) ==="
    echo ""
    echo "[1/2] Installing PyTorch with CUDA cu128 (nightly)..."
    pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu128
else
    echo "=== TrnsLate — CUDA cu126 Installation (stable) ==="
    echo ""
    echo "[1/2] Installing PyTorch with CUDA cu126 (stable)..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
fi

# Install remaining dependencies
echo "[2/2] Installing TrnsLate dependencies..."
pip install -r requirements.txt

echo ""
echo "Done! Run with:  python main.py --gpu"
echo "Or set GPU=true in .env"
