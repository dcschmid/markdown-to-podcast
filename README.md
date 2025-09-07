# Markdown to Podcast TTS

# Markdown to Podcast TTS

This repository converts scripted Markdown dialogues into high-quality podcast audio and optional audiogram videos.

It uses the Speechify Official SDK for TTS, Pydub for audio processing, and FFmpeg for encoding. The CLI and library are designed for production usage: SSML is enabled by default and automatic mappings favor English voices for consistent output quality.

## Contents

- `speechify_official.py` — main CLI and library wrapper to convert Markdown scripts into audio and subtitles
- `audiogram.py` — helper script to generate short promotional audiogram videos
- `examples/` — example markdown scripts

## Quick start

Requirements

- Python 3.8+
- FFmpeg installed and available on PATH

Install dependencies and prepare the environment:

```bash
python -m venv podcast-tts-env
source podcast-tts-env/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and set SPEECHIFY_API_KEY
```

Run a demo (if `examples/demo.md` exists):

```bash
python speechify_official.py examples/demo.md --language de --output-dir output
```

## speechify_official.py — CLI and programmatic usage

`speechify_official.py` converts a Markdown script into a final MP3 file and a WebVTT subtitle file. It splits the script into speaker segments, performs TTS calls, and merges the segments.

Important production behavior

- Automatic voice mapping defaults to English voices for automatic assignments:
  - `daniel` / `male` -> `jeremy`
  - `annabelle` / `female` -> `patricia`
- SSML is enabled by default; there is no `--no-ssml` flag.
- Interactive test and listing flags were removed from the production CLI (e.g. `--test-voices`, `--test-emotions`, `--list-voices`, `--test-api`, `--test-ssml`). Use separate test scripts or unit tests for validation.

CLI example

```bash
python speechify_official.py <input_markdown.md> \
  --language de \
  --output-dir output \
  --speakers "daniel:jeremy,annabelle:patricia" \
  --intro-music audio_samples/epic-metal.mp3
```

Programmatic example

```python
from speechify_official import SpeechifyPodcastTTS

tts = SpeechifyPodcastTTS(api_key="sk-...")
output = tts.process_podcast_script(
    "scripts/episode1.md",
    output_dir="output",
    language="de",
    custom_speakers={"daniel": "jeremy"},
)
print("Generated:", output)
```

Environment variables

- `SPEECHIFY_API_KEY` — Speechify API key (or pass `--api-key`)
- `SPEECHIFY_LOG_LEVEL` — optional, set to `DEBUG`, `INFO`, or `WARNING` (default: `INFO`)

## audiogram.py — create a visual audiogram

`audiogram.py` generates a short MP4 video with a waveform visualization and an optional cover image for social sharing.

BASIC example

```bash
python audiogram.py --audio output/podcast.mp3 --cover covers/the-melody-mind-podcast.png --title "Episode 1" --subtitle "The Golden 50s"
```

Extended example (with subtitles and export target)

```bash
python audiogram.py \
  --audio output/en/decades/1980s/1980s.mp3 \
  --cover covers/1980s.png \
  --title "The Melody Mind Podcast" \
  --subtitle "Episode 4 · The 80s - Synth-Pop & Hair Metal" \
  --size 1920x1080 \
  --bg_blur 18 \
  --theme midnight \
  --out movies/1980s.mp4 \
  --subtitles output/en/decades/1980s/1980s.vtt \
  --subs_mode soft
```

Common options

- `--audio` (required) — input audio (MP3/WAV)
- `--cover` — optional cover image (PNG/JPG)
- `--title` — title text
- `--subtitle` — subtitle text
- `--size` — video resolution, e.g. `1920x1080` or `1080x1080`
- `--out` — output filename (default: `audiogram.mp4`)

Ensure FFmpeg is installed for audio processing and video encoding.

## Markdown format and speaker mapping

The CLI expects speaker lines in the Markdown file. Example:

```markdown
Daniel: Welcome to our podcast.
Annabelle: Thank you, Daniel. Today we'll talk about...
Daniel: Let's dive in.
```

Speaker lines are detected by a name followed by `:`. Subsequent lines belong to that speaker until the next speaker label or a blank line.

Override automatic voice mapping with the `--speakers` flag:

```bash
--speakers "daniel:jeremy,annabelle:patricia"
```

## Output

The script writes:

- `output/<scriptname>.mp3` — final podcast audio
- `output/<scriptname>.vtt` — WebVTT subtitles

Temporary per-segment files are created during generation and removed after the final mix.

## Troubleshooting

Install dependencies:

```bash
pip install -r requirements.txt
```

FFmpeg missing: install via your package manager (Ubuntu: `sudo apt install ffmpeg`, macOS: `brew install ffmpeg`)

Invalid API key: verify `SPEECHIFY_API_KEY` and network access

For more verbose logs (debugging):

```bash
export SPEECHIFY_LOG_LEVEL=DEBUG
python speechify_official.py examples/demo.md
```

## Advanced usage

Batch processing example

```bash
for file in scripts/*.md; do
  python speechify_official.py "$file" --language auto
done
```

Custom voice assignment

```bash
python speechify_official.py script.md --speakers daniel:custom_male,anna:custom_female
```

## Project structure

```
markdown-to-podcast/
├── speechify_official.py    # Main TTS script
├── audiogram.py             # Audiogram generator
├── requirements.txt         # Dependencies
├── README.md                # This documentation
├── LICENSE                  # MIT License
├── .env.example             # Environment template
├── examples/                # Example scripts
└── output/                  # Generated audio files
```

## Contributing

Contributions are welcome. Open issues or PRs for feature requests, bug fixes, or documentation improvements.

## License

MIT License — see the included `LICENSE` file for details.

4. Push branch: `git push origin feature/new-feature`
5. Create Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- **Speechify**: For the excellent TTS API and multilingual voices
- **Contributors**: All testers and feedback providers

---

**Ready to create your multilingual podcast?**

```bash
python speechify_official.py examples/demo.md --language auto
```