#!/bin/bash
# Install TrnsLate CPU-only (no GPU required)

set -e

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
