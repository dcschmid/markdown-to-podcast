# Markdown to Podcast TTS (Chatterbox Edition)

Convert structured Markdown dialogue into podcast‑ready audio (MP3/WAV) plus WebVTT subtitles using the fully local, open‑source **Chatterbox Multilingual TTS** model (Resemble AI). No API keys, no external services. Fast mock mode available for CI.

> Automation guidelines & agent tasks: see `AGENTS.md`.

## Table of Contents

1. Overview & Features
2. Quick Start
3. Full Installation (venv & Conda)
4. Core Usage
5. Output Layout
6. Voices & Prompts
7. Performance & Parameters
8. Troubleshooting
9. Migration (Speechify → Local)
10. Cover Optimization Helper
11. Advanced Usage & Batch
12. Project Structure
13. Contributing / License
14. Acknowledgments
15. Ready Example

**GPU Setup:** For detailed GPU/CUDA setup and troubleshooting, see [`GPU_SETUP.md`](GPU_SETUP.md)

---

## 1. Overview & Features

Script pipeline:

Markdown dialogue (`Name: Text`) → parsing → per‑segment synthesis (Chatterbox) → concatenation + (optional) intro & outro music → timing → WebVTT export → MP3/WAV output.

Core outputs:

- Final MP3 (always)
- Final WAV (default ON; disable via `--no-export-wav`)
- WebVTT subtitles
- Per‑segment WAVs (default ON; disable via `--no-save-segments-wav`)

Optional: If an intro file `intro/epic-metal.mp3` exists it is prepended and appended automatically (same file as outro) and the VTT timestamps are shifted; intro/outro get their own caption entries.

Removed legacy features: external Speechify API, JSON timing dump, older intro/outro flag system.

## 2. Quick Start

Requirements

- Python 3.9+ (3.11 recommended for faster PyTorch / Chatterbox builds)
- FFmpeg on PATH (MP3 export)

Install dependencies and prepare the environment:

```bash
python -m venv podcast-tts-env
source podcast-tts-env/bin/activate
pip install -r requirements.txt

# (Optional) create .env with default overrides (no secrets required)
cp .env.example .env

Note on Python compatibility
----------------------------

The requirements file previously listed `audioop-lts` for Python 3.13 compatibility. This
project supports Python 3.8+ and `audioop` is part of the standard library for Python <=3.12.
To avoid install errors on older Python versions, `audioop-lts` was removed from
`requirements.txt`. If you run this project on Python >=3.13, you may need to install
`audioop-lts` separately.
```

Mock pipeline test (no model download):

```bash
python chatterbox_tts.py podscripts/classic-rock/classic-rock.md --language de --mock --output-dir output_mock
```

Real synthesis (first run downloads weights):

```bash
python chatterbox_tts.py podscripts/classic-rock/classic-rock.md --language de --device auto --output-dir output_real
```

With a style prompt (zero‑shot reference):

```bash
python chatterbox_tts.py script.md --language en --audio-prompt voices/en_male.wav --device cuda
```

---

## 3. Full Installation (Clean Setup: venv & Conda)

Converts a Markdown dialogue script into:

- Final MP3 file
- WebVTT subtitle file
- Per‑segment WAVs (default ON; disable with `--no-save-segments-wav`)

Removed legacy features: JSON timing export, intro/outro music injection.

Key capabilities (default-on features in bold, disable via `--no-*`):

- Speaker parsing (`Name: Text` lines)
- Languages: `de en es it fr pt`
- Voice/style via `--audio-prompt` or local `voices/` reference clips
- Local bundled style prompts for ALL supported languages (male & female) in `voices/` (no download needed)
- Configurable pauses (`--pause-ms`), expressiveness (`--exaggeration`), guidance weight (`--cfg-weight`)
- Mock mode (silence) for CI / structural tests
- **Structured output hierarchy** (`--no-structured-output` to flatten)
- **Segment WAV export** (`--no-save-segments-wav`)
- **Final WAV export** (`--no-export-wav`)
- **Warning suppression** (`--no-suppress-warnings`)

Follow these steps to get a fresh environment ready for real synthesis. Commands assume bash on Linux/macOS. Adjust Python version (`python3.11`) if needed.

### 3.1 System prerequisites

1. Python 3.9+ (3.11 recommended)
2. FFmpeg available on PATH:
  ```bash
  ffmpeg -version
  ```
  If this prints a version, you are good. If not, install via your package manager (e.g. `sudo apt install ffmpeg`).
3. Optional: NVIDIA GPU + CUDA drivers (for `--device cuda`).

### 3.2 Create virtual environment (venv)

```bash
python3.11 -m venv podcast-tts-env
source podcast-tts-env/bin/activate
python -m pip install --upgrade pip
```

### 3.3 Install base project dependencies

```bash
pip install -r requirements.txt
```

These cover audio processing (pydub, librosa), image utilities, dotenv, Flask, and testing.

### 3.4 Install Chatterbox (TTS backend)

Choose ONE of the following approaches:

Option A – PyPI (simplest CPU setup):
```bash
pip install chatterbox-tts
```

Option B – Editable local clone (for development):
```bash
git clone https://github.com/resemble-ai/chatterbox.git
cd chatterbox
pip install -e .
cd ..
```

### 3.4a GPU Setup (Recommended for Performance)

**IMPORTANT:** For optimal TTS performance, GPU acceleration is strongly recommended (5-10x faster).

#### Quick GPU Setup (Automated)

Use the automated setup script:
```bash
bash setup_gpu.sh
```

The script will:
- Detect your GPU architecture
- Install the correct PyTorch + CUDA version
- Verify the installation works

#### Manual GPU Setup

If you prefer manual installation or the script fails:

1. Check your GPU compute capability:
   ```bash
   nvidia-smi --query-gpu=name,compute_cap --format=csv
   ```

2. Install PyTorch based on your GPU:

   **RTX 50xx (Blackwell, sm_120):**
   ```bash
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu130
   ```

   **RTX 40xx (Ada Lovelace, sm_89):**
   ```bash
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```

   **RTX 30xx (Ampere, sm_86):**
   ```bash
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
   ```

   **RTX 20xx / GTX 16xx (Turing, sm_75):**
   ```bash
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

3. Verify CUDA is working:
   ```bash
   python -c "import torch; print('CUDA:', torch.cuda.is_available())"
   ```

**For detailed GPU troubleshooting, see `GPU_SETUP.md`**

### 3.5 (Optional) Add a `.env` file

Create `.env` to override defaults (no secrets required). Example:
```bash
echo "CHT_PAUSE_MS=600" > .env
```

### 3.6 Verify installation

Run a mock synthesis (fast, no model weights):
```bash
python chatterbox_tts.py podscripts/classic-rock/classic-rock.md --language de --mock --output-dir verify_mock
```

Run a real synthesis (downloads weights on first run):
```bash
python chatterbox_tts.py podscripts/classic-rock/classic-rock.md --language de --device auto --output-dir verify_real
```

### 3.7 GPU check (optional)

Inside Python:
```python
import torch
print(torch.cuda.is_available())  # Expect True for CUDA usage
```

### 3.8 Update / maintenance

To update Chatterbox (PyPI):
```bash
pip install --upgrade chatterbox-tts
```

For a git clone:
```bash
cd chatterbox
git pull
pip install -e .
cd ..
```

### 3.9 Common installation issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `ffmpeg` not found | Not installed | Install via package manager (e.g. `sudo apt install ffmpeg`) |
| Very slow first run | Weight download | Reuse the same virtualenv for subsequent runs |
| CUDA not used | Drivers / build mismatch | Reinstall torch with correct CUDA wheel (see command above) |
| ImportError: soundfile | Missing libsndfile system library | Install via package manager (`sudo apt install libsndfile1`) |
| Permission denied writing cache | Insufficient directory rights | Run from user-writable project directory |

### 3.10 Uninstall / cleanup
### 3.11 Conda alternative

If you prefer Conda (good for complex CUDA setups):

```bash
conda create -n podcast-tts python=3.11 -y
conda activate podcast-tts
conda install -c conda-forge ffmpeg libsndfile -y
pip install -r requirements.txt
pip install chatterbox-tts
# Optional CUDA (ensure matching version):
# pip install torch --index-url https://download.pytorch.org/whl/cu121
```

To remove:
```bash
conda deactivate
conda env remove -n podcast-tts
```

---

## 4. Core Usage

Remove the virtual environment directory:
```bash
deactivate  # if still active
rm -rf podcast-tts-env
```

Delete generated outputs:
```bash
rm -rf output_chatterbox*
```

---

FFmpeg is required for MP3 export via pydub (verify with `ffmpeg -version`).

Mock test (no model download):

```bash
python chatterbox_tts.py podscripts/classic-rock/classic-rock.md --language de --mock --output-dir out_mock
```

Real synthesis (GPU preferred):

```bash
python chatterbox_tts.py podscripts/classic-rock/classic-rock.md \
  --language de \
  --device cuda \
  --output-dir out_real \
  --exaggeration 0.5 --cfg-weight 0.5
```

With reference prompt:

```bash
python chatterbox_tts.py script.md --language en --audio-prompt voices/en_male.wav --device cuda
```

### 4.1 Important flags

- `--language` – target language (de,en,es,it,fr,pt)
- `--speakers` – override mapping (e.g. `anna:de_f,daniel:de_m`)
- `--audio-prompt` – global style reference (wav/mp3/flac/ogg/m4a)
- `--pause-ms` – silence between segments
- `--exaggeration` – expressiveness (0–1)
- `--cfg-weight` – guidance/style balance
- `--mock` – silence instead of real TTS
- `--voices-dir` – local prompt clips (highest priority)
- `--structured-output` / `--no-structured-output`
- `--save-segments-wav` / `--no-save-segments-wav`
- `--export-wav` / `--no-export-wav`
- `--suppress-warnings` / `--no-suppress-warnings`

## 5. Output Layout

```text
output_real/
  classic-rock.mp3
  classic-rock.vtt
  classic-rock.wav (optional)
```

Structured output (default) and segment WAVs:

```text
output_real/
  de/
    classic-rock/
      final/
  classic-rock.mp3
  classic-rock.vtt
  classic-rock.wav
      segments/
        classic-rock_segment_001_daniel.wav
        classic-rock_segment_002_annabelle.wav
        ...
```

### 5.1 Segment filename pattern

`<base>_segment_<index>_<speaker>.wav` with index width = max(3, len(str(total_segments))). Example: `1960s_segment_001_daniel.wav`.

## 6. Voices & Prompts

Bundled examples already included for every supported language, pattern:

`<lang>_male.(wav|mp3|flac|ogg|m4a)` and `<lang>_female.*` (e.g. `de_male.mp3`, `en_female.mp3`).

Adding / overriding voices:

1. Drop new files into `voices/` following the same `<lang>_male` / `<lang>_female` pattern.
2. Non‑WAV formats are auto-converted once into cached WAV.
3. Fallback still accepts generic `male.*` / `female.*` if language‑specific files missing.

## 7. Performance & Notes

- First run downloads weights
- GPU strongly recommended for longer scripts
- No SSML parser – emulate with segmentation / `--pause-ms`
- Voice mapping heuristic only; timbre from your prompt

### 7.1 Minimal setup snippet (condensed)

```bash
python3.11 -m venv cb-env
source cb-env/bin/activate
pip install --upgrade pip
pip install chatterbox-tts
# Optional: install CUDA build (adjust version as needed)
# pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### 7.2 Python smoke test

```python
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
print("Sample Rate:", getattr(model, "sr", "?"))
```

### 7.3 Parameter guidance

| Parameter | Effect | Typical Range | Note |
|-----------|--------|---------------|------|
| `--exaggeration` | Expressiveness | 0.4–0.7 | Higher = more dynamic |
| `--cfg-weight` | Guidance vs style | 0.3–0.6 | Lower = more prompt influence |
| `--pause-ms` | Silence between segments | 300–800 | Simulates SSML breaks |
| `--audio-prompt` | Style reference clip | 5–10s | Clean mono snippet |

### 7.4 Performance tips

- GPU (`--device cuda`) verwenden für längere Skripte
- Segmente moderat halten (<25s)
- Gleiches Environment wiederverwenden (kein erneuter Cold Start)
- Bei knapper VRAM: `--device cpu`

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Slow first run | Weight download & init | Reuse venv; later runs faster |
| **"sm_120 not compatible"** | **RTX 50xx GPU needs newer PyTorch** | **See GPU_SETUP.md or run `bash setup_gpu.sh`** |
| **"no kernel image available"** | **PyTorch doesn't support your GPU** | **Install correct CUDA version (see GPU_SETUP.md)** |
| CUDA OOM | Not enough VRAM | `--device cpu` or free GPU memory |
| Monotone output | Low exaggeration | Increase to ~0.6–0.7 |
| Speech too fast | High exaggeration + high cfg | Reduce both slightly |
| Wrong style / accent | Mismatched prompt language | Provide matching prompt |
| Missing German prompt | No local clips | Add `voices/de_male.*` & `voices/de_female.*` |

**For GPU-specific issues, see the detailed guide: `GPU_SETUP.md`**

## 9. Migration from Speechify

Removed to eliminate vendor costs/limits and enable fully offline reproducible TTS with flexible zero‑shot style prompts.

Removed artifacts: `speechify_official.py`, `SPEECHIFY_API_KEY`, JSON metadata export, intro/outro music flags.

Old:

```bash
python speechify_official.py script.md ...
```

New:

```bash
python chatterbox_tts.py script.md --language de ...
```

---


## 10. Cover Optimization Helper (`optimize_covers.py`)

Converts cover artwork (PNG/JPG/WebP) into optimized JPEG (optionally progressive) for efficient delivery.

Why:

- Large PNGs waste bandwidth
- Progressive JPEGs improve perceived load speed
- Downscaling trims unnecessary pixels

Process:

1. Collect images
2. Flatten transparency onto white
3. Scale to max edge
4. Export JPEG (`--quality`, optional `--progressive`)
5. Optional report (table / CSV)

Example:

```bash
python optimize_covers.py --input-dir covers --output-dir covers_web --max-size 1200 --quality 82 --progressive
```

Key flags:

| Flag | Meaning |
|------|---------|
| `--input-dir` | Source directory |
| `--output-dir` | Destination directory |
| `--max-size` | Max edge length |
| `--quality` | JPEG quality (80–85 rec.) |
| `--progressive` | Progressive JPEG |
| `--report` | Print summary table |
| `--report-csv` | CSV report |

Incremental run:

```bash
python optimize_covers.py -i covers -o covers_web --skip-existing --progressive
```

---

## 11. Markdown Format & Speaker Mapping

Example:

```markdown
Daniel: Willkommen zu unserer Episode.
Annabelle: Danke Daniel, heute sprechen wir über...
Daniel: Legen wir los.
```

Override mapping:

```bash
--speakers "daniel:de_m,annabelle:de_f"
```

## 12. Advanced Usage

Generated:

- `output/<name>.mp3`
- `output/<name>.vtt`
- `output/<name>.wav` (default ON unless disabled with `--no-export-wav`)

With `--save-segments-wav` + `--structured-output` see example tree above.

Temporary files are cleaned (segment WAVs preserved if requested).

### 12.1 Batch processing

Batch processing:

```bash
for f in podscripts/classic-rock/*.md; do
  python chatterbox_tts.py "$f" --language de --structured-output --output-dir batch_out
done
```

### 12.2 Custom token mapping

```bash
python chatterbox_tts.py script.md --language en --speakers "host:en_m,guest:en_f"
```

## 13. Project Structure

```text
markdown-to-podcast/
├── chatterbox_tts.py        # Main TTS script
├── optimize_covers.py       # Cover optimization
├── utils/                   # Helper modules
├── requirements.txt
├── README.md
├── LICENSE
├── .env.example
└── output/                  # Generierte Dateien
```

## 14. Contributing

PRs welcome: features, fixes, docs, tests.

## 15. License

MIT – see `LICENSE`.

## 16. Acknowledgments

- Chatterbox / Resemble AI OSS
- Testers & contributors

---

## 17. Ready Example

**Create your multilingual podcast now:**

```bash
python chatterbox_tts.py podscripts/classic-rock/classic-rock.md --language de --mock --output-dir output
```

*** End Patch
