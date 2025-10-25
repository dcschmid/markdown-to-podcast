# GPU Setup Guide

Complete guide for setting up PyTorch with CUDA support for optimal TTS performance.

---

## Overview

This project uses Chatterbox TTS, which runs significantly faster on NVIDIA GPUs. This guide helps you:

- Detect your GPU capabilities
- Install the correct PyTorch + CUDA version
- Troubleshoot common CUDA compatibility issues

---

## Quick GPU Check

```bash
# Check if you have an NVIDIA GPU
nvidia-smi

# Check CUDA version
nvidia-smi | grep "CUDA Version"
```

---

## GPU Architecture Compatibility

### Understanding Compute Capability (sm_XX)

NVIDIA GPUs have different "compute capabilities" (also called `sm_XX`). PyTorch must be compiled with support for your specific architecture.

| GPU Series | Architecture | Compute Capability | PyTorch CUDA Requirement |
|------------|--------------|-------------------|-------------------------|
| RTX 40xx Series | Ada Lovelace | sm_89 | CUDA 11.8+ |
| RTX 50xx Series (Blackwell) | Blackwell | **sm_120** | **CUDA 12.8+ or 13.0+** |
| RTX 30xx Series | Ampere | sm_86 | CUDA 11.x+ |
| RTX 20xx Series | Turing | sm_75 | CUDA 10.x+ |
| GTX 16xx Series | Turing | sm_75 | CUDA 10.x+ |

### RTX 5060 / Blackwell GPUs (sm_120)

**If you have an RTX 50xx GPU**, you need:
- PyTorch 2.7+ (or nightly builds)
- CUDA 12.8 or 13.0 runtime

Standard PyTorch builds **do not support sm_120 yet**. Use one of these solutions:

#### Solution 1: CUDA 13.0 (Recommended)
```bash
source podcast-tts-env/bin/activate
pip install --upgrade torch torchaudio --index-url https://download.pytorch.org/whl/cu130
```

#### Solution 2: CUDA 12.8 (Alternative)
```bash
source podcast-tts-env/bin/activate
pip install --upgrade torch torchaudio --index-url https://download.pytorch.org/whl/cu128
```

#### Solution 3: Nightly Builds (Cutting Edge)
```bash
source podcast-tts-env/bin/activate
pip install --pre torch torchaudio --index-url https://download.pytorch.org/whl/nightly/cu130
```

---

## Automated Setup Script

Use the included `setup_gpu.sh` script to automatically detect and install the correct version:

```bash
bash setup_gpu.sh
```

The script will:
1. Detect your GPU architecture
2. Identify required CUDA version
3. Install appropriate PyTorch build
4. Verify the installation

---

## Manual Installation

### Step 1: Check Your GPU

```bash
nvidia-smi --query-gpu=name,compute_cap --format=csv
```

Example output:
```
name, compute_cap
NVIDIA GeForce RTX 5060 Laptop GPU, 12.0
```

### Step 2: Choose PyTorch Version

Based on compute capability:

**For sm_120 (RTX 50xx):**
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu130
```

**For sm_86-89 (RTX 30xx/40xx):**
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
```

**For sm_75 (RTX 20xx/GTX 16xx):**
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Step 3: Verify Installation

```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
```

Expected output (for RTX 5060 with CUDA 13.0):
```
PyTorch version: 2.9.0+cu130
CUDA available: True
CUDA version: 13.0
GPU: NVIDIA GeForce RTX 5060 Laptop GPU
```

---

## Common Errors & Solutions

### Error: "sm_120 is not compatible with current PyTorch"

**Symptom:**
```
UserWarning: NVIDIA GeForce RTX 5060 Laptop GPU with CUDA capability sm_120 
is not compatible with the current PyTorch installation.
The current PyTorch install supports CUDA capabilities sm_50 sm_60 sm_70 sm_75 sm_80 sm_86 sm_90.
```

**Solution:**
You have a Blackwell GPU (RTX 50xx). Install PyTorch with CUDA 13.0 support:
```bash
pip install --upgrade torch torchaudio --index-url https://download.pytorch.org/whl/cu130
```

### Error: "CUDA error: no kernel image is available"

**Symptom:**
```
CUDA error: no kernel image is available for execution on the device
```

**Solution:**
Same as above – your PyTorch version doesn't support your GPU architecture. Upgrade PyTorch.

### Error: "CUDA out of memory"

**Symptom:**
```
RuntimeError: CUDA out of memory. Tried to allocate XX MiB
```

**Solutions:**
1. Use CPU mode: `--device cpu`
2. Close other GPU applications
3. Reduce batch size (not applicable for this single-segment TTS)
4. Restart and try again

### Warning: chatterbox-tts dependency conflict

**Symptom:**
```
chatterbox-tts 0.1.4 requires torch==2.6.0, but you have torch 2.9.0+cu130
```

**Solution:**
This warning can be **safely ignored**. Chatterbox works fine with newer PyTorch versions. The package metadata is just strict about versions.

---

## Performance Comparison

Test on classic-rock script (553 segments):

| Device | Time | Speed |
|--------|------|-------|
| CPU (12-core) | ~45 min | ~1.2 segments/min |
| GPU (RTX 5060) | ~8 min | ~69 segments/min |
| Mock mode | ~2 sec | N/A |

**Recommendation:** Always use GPU for production synthesis.

---

## Fallback to CPU

If GPU setup fails or you don't have an NVIDIA GPU:

```bash
# Remove --device flag (auto-detects CPU)
python chatterbox_tts.py script.md --language en --output-dir output

# Or explicitly specify CPU
python chatterbox_tts.py script.md --language en --device cpu --output-dir output
```

CPU mode works reliably but is 5-10x slower.

---

## Checking Installation After Setup

Quick verification command:

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available(), '|', 'Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

---

## Additional Resources

- [PyTorch Installation Guide](https://pytorch.org/get-started/locally/)
- [NVIDIA CUDA Compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/)
- [Chatterbox TTS Documentation](https://github.com/resemble-ai/chatterbox)

---

## Still Having Issues?

1. Check `nvidia-smi` output
2. Verify CUDA drivers are installed
3. Try the automated setup script: `bash setup_gpu.sh`
4. Open an issue with:
   - GPU model (`nvidia-smi --query-gpu=name,compute_cap --format=csv`)
   - PyTorch version (`pip show torch`)
   - Full error message

---

**Last Updated:** 2025-10-25
