# Markdown to Podcast TTS (Chatterbox Edition)

This project converts scripted Markdown dialogue into high‑quality podcast audio (MP3) plus WebVTT subtitles using the open‑source **Chatterbox Multilingual TTS** model (Resemble AI). Optional: generate promotional audiogram MP4 videos.

The previous Speechify backend has been fully removed. No API keys, no external TTS calls – everything runs locally (or via a lightweight mock mode for fast tests).

> For automation / coding agents see `AGENTS.md`.

## Contents

- `chatterbox_tts.py` – main script: Markdown → TTS (Chatterbox) → MP3 + VTT (+ optional segment WAVs)
- `podscripts/` – sample scripts
- `utils/` – helper utilities (image optimization, categorization, etc.)

## Quick start

Requirements

- Python 3.9+ (3.11 recommended for faster PyTorch / Chatterbox builds)
- FFmpeg on PATH (MP3 export & audiogram rendering)

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

## chatterbox_tts.py – core features

Converts a Markdown dialogue script into:

- Final MP3 file
- WebVTT subtitle file
- Per‑segment WAVs (default ON; disable with `--no-save-segments-wav`)

Removed legacy features: JSON timing export, intro/outro music injection.

Key capabilities (default-on features in bold, disable via `--no-*`):

- Speaker parsing (`Name: Text` lines)
- Languages: `de en es it fr pt`
- Voice/style via `--audio-prompt` or local `voices/` reference clips
- Optional automatic prompt download (`--auto-prompts`) – German intentionally has no remote prompt URLs
- Configurable pauses (`--pause-ms`), expressiveness (`--exaggeration`), guidance weight (`--cfg-weight`)
- Mock mode (silence) for CI / structural tests
- **Structured output hierarchy** (`--no-structured-output` to flatten)
- **Segment WAV export** (`--no-save-segments-wav`)
- **Final WAV export** (`--no-export-wav`)
- **Warning suppression** (`--no-suppress-warnings`)

Install (real synthesis):

```bash
pip install chatterbox-tts  # installiert auch torch / torchaudio (ggf. CPU Variante)
# oder für Entwicklung:
git clone https://github.com/resemble-ai/chatterbox.git
cd chatterbox
pip install -e .
```

FFmpeg is required for MP3 export via pydub.

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

Important flags (default-on features have inverse `--no-*` counterpart):

- `--language` – target language (de,en,es,it,fr,pt)
- `--speakers` – override mapping (e.g. `anna:de_f,daniel:de_m`)
- `--audio-prompt` – global style reference (wav/mp3/flac/ogg/m4a)
- `--pause-ms` – silence between segments
- `--exaggeration` – expressiveness (0–1)
- `--cfg-weight` – guidance/style balance
- `--mock` – silence instead of real TTS
- `--auto-prompts` – auto fetch male/female prompts (not for `de`)
- `--voices-dir` – local prompt clips (highest priority)
- `--structured-output` / `--no-structured-output`
- `--save-segments-wav` / `--no-save-segments-wav`
- `--export-wav` / `--no-export-wav`
- `--suppress-warnings` / `--no-suppress-warnings`

Default output layout (if flattened with `--no-structured-output`):

```text
output_real/
  classic-rock.mp3
  classic-rock.vtt
  classic-rock.wav (optional)
```

With structured output (default) and segment WAVs:

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

Segment filename pattern:

`<base>_segment_<index>_<speaker>.wav` with index width = max(3, len(str(total_segments))). Example: `1960s_segment_001_daniel.wav`.

Local prompt voices:

Place in `voices/`:

- `de_male.(wav|mp3|flac|ogg|m4a)` / `de_female.*`
- Fallback: `male.*`, `female.*`

Non‑WAV formats convert once into cache (WAV). German intentionally has no remote prompts – supply local clips.

Limitations / notes:

- First run downloads weights
- GPU strongly recommended for longer scripts
- No SSML parser – emulate with segmentation / `--pause-ms`
- Voice mapping heuristic only; timbre from your prompt

### Detailed setup workflow

```bash
python3.11 -m venv cb-env
source cb-env/bin/activate
pip install --upgrade pip
pip install chatterbox-tts
# Optional CUDA Build installieren falls nötig:
# pip install torch --index-url https://download.pytorch.org/whl/cu121
```

Python smoke test:

```python
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
print("Sample Rate:", getattr(model, "sr", "?"))
```

### Parameter guidance

| Parameter | Effect | Typical Range | Note |
|-----------|--------|---------------|------|
| `--exaggeration` | Expressiveness | 0.4–0.7 | Higher = more dynamic |
| `--cfg-weight` | Guidance vs style | 0.3–0.6 | Lower = more prompt influence |
| `--pause-ms` | Silence between segments | 300–800 | Simulates SSML breaks |
| `--audio-prompt` | Style reference clip | 5–10s | Clean mono snippet |

### Performance tips

- GPU (`--device cuda`) verwenden für längere Skripte
- Segmente moderat halten (<25s)
- Gleiches Environment wiederverwenden (kein erneuter Cold Start)
- Bei knapper VRAM: `--device cpu`

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Slow first run | Weight download & init | Reuse venv; later runs faster |
| CUDA OOM | Not enough VRAM | `--device cpu` or free GPU memory |
| Monotone output | Low exaggeration | Increase to ~0.6–0.7 |
| Speech too fast | High exaggeration + high cfg | Reduce both slightly |
| Wrong style / accent | Mismatched prompt language | Provide matching prompt |
| Missing German prompt | No local clips | Add `voices/de_male.*` & `voices/de_female.*` |

### Migration from Speechify

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


## optimize_covers.py – optimize cover images

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

## Markdown format & speaker mapping

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

## Output (default)

Generated:

- `output/<name>.mp3`
- `output/<name>.vtt`
- `output/<name>.wav` (default ON unless disabled with `--no-export-wav`)

With `--save-segments-wav` + `--structured-output` see example tree above.

Temporary files are cleaned (segment WAVs preserved if requested).

## Advanced usage

Batch processing:

```bash
for f in podscripts/classic-rock/*.md; do
  python chatterbox_tts.py "$f" --language de --structured-output --output-dir batch_out
done
```

Custom token mapping:

```bash
python chatterbox_tts.py script.md --language en --speakers "host:en_m,guest:en_f"
```

## Project structure

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

## Contributing

PRs welcome: features, fixes, docs, tests.

## License

MIT – see `LICENSE`.

## 📄 License

## 🙏 Acknowledgments

- Chatterbox / Resemble AI OSS
- Testers & contributors

---

**Ready to create your multilingual podcast?**

```bash
python chatterbox_tts.py podscripts/classic-rock/classic-rock.md --language de --mock --output-dir output
```

*** End Patch
