#!/bin/bash
# Install TrnsLate with CUDA cu128 support (RTX 5060 / Blackwell)

set -e

echo "=== TrnsLate — CUDA cu128 Installation ==="
echo ""

# Install torch with cu128 nightly first
echo "[1/2] Installing PyTorch with CUDA cu128 (nightly)..."
pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu128

# Install remaining dependencies
echo "[2/2] Installing TrnsLate dependencies..."
pip install -r requirements.txt

echo ""
echo "Done! Run with:  python main.py --gpu"
echo "Or set GPU=true in .env"
