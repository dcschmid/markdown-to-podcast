#!/bin/bash

# GPU Setup Script for Markdown-to-Podcast TTS
# Automatically detects GPU and installs correct PyTorch version

set -e

echo "=========================================="
echo "GPU Setup for Markdown-to-Podcast TTS"
echo "=========================================="
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "❌ Error: No virtual environment detected."
    echo ""
    echo "Please activate your virtual environment first:"
    echo "  source podcast-tts-env/bin/activate"
    echo ""
    exit 1
fi

echo "✓ Virtual environment active: $VIRTUAL_ENV"
echo ""

# Check if nvidia-smi is available
if ! command -v nvidia-smi &> /dev/null; then
    echo "⚠️  Warning: nvidia-smi not found."
    echo ""
    echo "This means either:"
    echo "  1. You don't have an NVIDIA GPU"
    echo "  2. NVIDIA drivers are not installed"
    echo ""
    echo "Installing CPU-only PyTorch..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    echo ""
    echo "✓ CPU-only PyTorch installed."
    echo "  Use: python chatterbox_tts.py script.md --language en --device cpu"
    exit 0
fi

echo "✓ NVIDIA GPU detected"
echo ""

# Get GPU info
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
COMPUTE_CAP=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -n 1)
CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}')

echo "GPU Information:"
echo "  Name: $GPU_NAME"
echo "  Compute Capability: $COMPUTE_CAP"
echo "  CUDA Driver Version: $CUDA_VERSION"
echo ""

# Determine PyTorch version based on compute capability
MAJOR=$(echo "$COMPUTE_CAP" | cut -d. -f1)
MINOR=$(echo "$COMPUTE_CAP" | cut -d. -f2)

# Convert to integer for comparison
COMPUTE_INT=$((MAJOR * 10 + MINOR))

if [ "$COMPUTE_INT" -ge 120 ]; then
    # Blackwell (RTX 50xx series) - requires CUDA 13.0
    CUDA_INDEX="cu130"
    CUDA_NAME="13.0"
    ARCH="Blackwell (sm_120+)"
elif [ "$COMPUTE_INT" -ge 89 ]; then
    # Ada Lovelace (RTX 40xx series)
    CUDA_INDEX="cu124"
    CUDA_NAME="12.4"
    ARCH="Ada Lovelace (sm_89)"
elif [ "$COMPUTE_INT" -ge 86 ]; then
    # Ampere (RTX 30xx series)
    CUDA_INDEX="cu124"
    CUDA_NAME="12.4"
    ARCH="Ampere (sm_86)"
elif [ "$COMPUTE_INT" -ge 75 ]; then
    # Turing (RTX 20xx, GTX 16xx series)
    CUDA_INDEX="cu121"
    CUDA_NAME="12.1"
    ARCH="Turing (sm_75)"
else
    # Older architectures
    CUDA_INDEX="cu121"
    CUDA_NAME="12.1"
    ARCH="Legacy (sm_$COMPUTE_CAP)"
fi

echo "Detected Architecture: $ARCH"
echo "Selected PyTorch CUDA Version: $CUDA_NAME ($CUDA_INDEX)"
echo ""

# Ask for confirmation
read -p "Install PyTorch with CUDA $CUDA_NAME support? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo "Installing PyTorch with CUDA $CUDA_NAME..."
echo "Command: pip install --upgrade torch torchaudio --index-url https://download.pytorch.org/whl/$CUDA_INDEX"
echo ""

pip install --upgrade torch torchaudio --index-url "https://download.pytorch.org/whl/$CUDA_INDEX"

echo ""
echo "=========================================="
echo "Verifying Installation..."
echo "=========================================="
echo ""

# Verify installation
python3 << 'EOF'
import torch
import sys

print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA Version: {torch.version.cuda}")
    print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    # Test basic CUDA operation
    try:
        x = torch.randn(100, 100).cuda()
        y = torch.matmul(x, x)
        print("\n✓ CUDA tensor operations working correctly")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ CUDA test failed: {e}")
        sys.exit(1)
else:
    print("\n⚠️  Warning: CUDA is not available")
    print("PyTorch will run on CPU only")
    sys.exit(1)
EOF

VERIFY_STATUS=$?

echo ""
if [ $VERIFY_STATUS -eq 0 ]; then
    echo "=========================================="
    echo "✓ GPU Setup Complete!"
    echo "=========================================="
    echo ""
    echo "You can now use GPU acceleration:"
    echo "  python chatterbox_tts.py script.md --language en --device cuda --output-dir output"
    echo ""
    echo "For more details, see GPU_SETUP.md"
else
    echo "=========================================="
    echo "❌ GPU Setup Failed"
    echo "=========================================="
    echo ""
    echo "Possible issues:"
    echo "  1. CUDA drivers need updating"
    echo "  2. GPU not supported by this PyTorch version"
    echo "  3. System restart required after driver install"
    echo ""
    echo "Fallback to CPU mode:"
    echo "  python chatterbox_tts.py script.md --language en --device cpu --output-dir output"
    echo ""
    echo "For troubleshooting, see GPU_SETUP.md"
    exit 1
fi
