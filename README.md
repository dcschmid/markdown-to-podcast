# Markdown to Podcast TTS

🎙️ **Modernste Text-zu-Sprache für deutsche Podcasts mit Speechify**

Konvertiert Markdown-Dialoge in hochqualitative MP3-Podcasts mit natürlich klingenden deutschen Stimmen.

## 🚀 Quick Start

```bash
# 1. Python-Umgebung erstellen
python -m venv podcast-tts-env
source podcast-tts-env/bin/activate  # Linux/Mac
# podcast-tts-env\Scripts\activate   # Windows

# 2. Abhängigkeiten installieren
pip install -r requirements.txt

# 3. API-Key konfigurieren
cp .env.example .env
# Editiere .env: SPEECHIFY_API_KEY=dein_key_hier

# 4. Demo ausführen
python speechify_official.py examples/demo.md --language de
```

## 🔧 Python-Umgebung Setup

### Automatisches Setup (empfohlen)

```bash
# Setup-Check ausführen
python setup_check.py
```

### Manuelles Setup

```bash
# Python 3.8+ erforderlich
python --version

# Virtuelle Umgebung
python -m venv podcast-tts-env

# Aktivieren
source podcast-tts-env/bin/activate  # Linux/Mac
podcast-tts-env\Scripts\activate     # Windows

# Dependencies
pip install -r requirements.txt

# FFmpeg (für MP3-Export)
sudo apt install ffmpeg              # Ubuntu/Debian
brew install ffmpeg                  # macOS
# Windows: https://ffmpeg.org/download.html
```

## 🔑 API-Key Konfiguration

1. **Speechify Account**: [speechify.com](https://speechify.com) → API Key
2. **Environment Setup**:

   ```bash
   cp .env.example .env
   nano .env  # Oder anderer Editor
   ```

3. **Key eintragen**:

   ```env
   SPEECHIFY_API_KEY=sk-your-actual-key-here
   ```

## 💬 CLI-Nutzung

### Basis-Kommando

```bash
python speechify_official.py script.md
```

### Alle Optionen

```bash
python speechify_official.py script.md \
  --language de \                    # Sprache (de/en/es/fr/zh/...)
  --output-format mp3 \              # Format (mp3/wav)
  --audio-speed 1.0 \                # Geschwindigkeit (0.5-2.0)
  --voice-daniel stefan \            # Custom Speaker-Voice
  --voice-anna ronja \               # Custom Speaker-Voice
  --output-dir output/               # Output-Verzeichnis
```

### CLI-Parameter

| Parameter | Kurz | Beschreibung | Beispiel |
|-----------|------|--------------|----------|
| `--language` | `-l` | Zielsprache | `de`, `en`, `es` |
| `--output-format` | `-f` | Audio-Format | `mp3`, `wav` |
| `--audio-speed` | `-s` | Wiedergabe-Geschwindigkeit | `0.8`, `1.2`, `1.5` |
| `--voice-{speaker}` | - | Speaker-Voice zuweisen | `--voice-daniel stefan` |
| `--output-dir` | `-o` | Output-Verzeichnis | `output/`, `./results/` |
| `--help` | `-h` | Hilfe anzeigen | - |

## 🌍 Sprachen & Stimmen

### Deutsche Stimmen (Standard)

- **Männlich**: `stefan` (Daniel)
- **Weiblich**: `ronja` (Anna/Annabelle)

### Multilingual Support

| Sprache | Code | Männlich | Weiblich |
|---------|------|----------|----------|
| 🇩🇪 Deutsch | `de` | stefan | ronja |
| 🇺🇸 English | `en` | frederick | andra |
| 🇪🇸 Español | `es` | alejandro | sofia |
| 🇫🇷 Français | `fr` | raphael | elise |
| 🇨🇳 中文 | `zh` | chun-wah | yan-ting |
| 🇮🇹 Italiano | `it` | lazzaro | alessia |
| 🇵🇹 Português | `pt` | lucas | luiza |
| 🇷🇺 Русский | `ru` | mikhail | anastasia |
| 🇯🇵 日本語 | `ja` | tsubasa | sakura |
| 🇳🇱 Nederlands | `nl` | daan | lotte |
| 🇩🇰 Dansk | `da` | frederik | freja |
| 🇫🇮 Suomi | `fi` | eino | helmi |
| 🇸🇪 Svenska | `sv` | gustav | astrid |
| 🇹🇷 Türkçe | `tr` | emir | elif |

## � Markdown-Format

```markdown
# Podcast-Titel

Daniel: Willkommen zu unserem Podcast! Heute sprechen wir über...

Anna: Das ist richtig, Daniel. Dieses Thema ist sehr spannend...

Daniel: Lass uns tiefer in die Materie eintauchen...

Anna: Absolut! Die neuen Entwicklungen sind beeindruckend.
```

### Speaker-Mapping

- **daniel** → Männliche Stimme (stefan/frederick/alejandro...)
- **anna/annabelle** → Weibliche Stimme (ronja/andra/sofia...)
- Automatische Spracherkennung und Voice-Zuordnung

## 📁 Output & Struktur

### Generated Files

```
output/
├── demo_20250103_142830.mp3          # Audio-Datei
├── demo_20250103_142830_info.json    # Metadata
└── demo_20250103_142830_segments.json # Segment-Info
```

### Projektstruktur

```
markdown-to-podcast/
├── speechify_official.py    # 🎤 Haupt-TTS-Engine
├── requirements.txt         # 📦 Dependencies  
├── .env.example            # 🔑 API-Key Template
├── setup_check.py          # ✅ Setup-Validation
├── examples/               # 📝 Demo-Skripte
│   └── demo.md
├── output/                 # 🎵 Generierte Audio-Dateien
└── README.md              # 📖 Diese Dokumentation
```

## 🛠️ Troubleshooting

### Häufige Probleme

**❌ ModuleNotFoundError: speechify**

```bash
pip install speechify-api
```

**❌ FFmpeg not found**

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: https://ffmpeg.org/download.html
```

**❌ API Key ungültig**

```bash
# .env prüfen
cat .env
# Key ohne Leerzeichen?
# Speechify-Account aktiv?
```

**❌ Python Version**

```bash
python --version  # 3.8+ erforderlich
# Für Python 3.13: audioop-lts wird automatisch installiert
```

**❌ Audio-Export-Fehler**

```bash
# Pydub + FFmpeg prüfen
python -c "from pydub import AudioSegment; print('✅ Audio OK')"
```

### Setup-Validation

```bash
python setup_check.py  # Automatische Diagnose
```

## 🔥 Advanced Features

### Batch-Processing

```bash
# Mehrere Dateien
python speechify_official.py podscripts/de/*.md --language de

# Ganze Verzeichnisse
find podscripts/ -name "*.md" -exec python speechify_official.py {} \;
```

### Custom Voice-Mapping

```bash
# Deutsche Podcast mit englischen Stimmen
python speechify_official.py script.md \
  --language de \
  --voice-daniel frederick \
  --voice-anna andra
```

### Performance-Tuning

```bash
# Schnellere Wiedergabe
python speechify_official.py script.md --audio-speed 1.3

# Langsamere, deutlichere Sprache
python speechify_official.py script.md --audio-speed 0.8
```

## 💡 Features im Detail

### ✨ Kerntechnologie

- **Speechify Official SDK**: Premium TTS-Qualität
- **Multilinguale KI**: 14 Sprachen, natürliche Phonetik
- **Speaker Intelligence**: Automatische Stimm-Zuordnung
- **Hochqualitäts-Audio**: 22kHz+ MP3/WAV Export

### 🎯 Deutsche Optimierung

- **Umlaute & ß**: Perfekte Verarbeitung (ä, ö, ü, ß)
- **Hochdeutsch**: Standard-Phonetik für Podcasts
- **Dialekt-Support**: Speechify's natürliche Variationen
- **Text-Preprocessing**: Optimiert für deutsche Sprache

### 🚀 Performance

- **Batch-Verarbeitung**: Große Skripte, kleine Segmente
- **Progress-Feedback**: Live-Status bei langen Konvertierungen
- **Memory-Efficient**: Intelligente Audio-Pufferung
- **Error-Recovery**: Graceful Handling von API-Limits

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) für Details.

---

**🇩🇪 Erstellt für die deutsche Podcast-Community**  
*Hochqualitative TTS-Technologie für moderne Content-Creator*

### 4. Verify Installation

```bash
# Test API connection
python speechify_official.py --test-api

# Test voice options
python speechify_official.py --test-voices
```

## 📋 Requirements

- **Python**: 3.8+ (recommended: 3.11+)
- **API Key**: Speechify API access
- **RAM**: 2+ GB available
- **Disk**: 100+ MB for dependencies
- **OS**: Windows, macOS, Linux

## 🖥️ Usage Examples

### Basic Usage

```bash
# Generate German podcast (default)
python speechify_official.py script.md

# Generate English podcast
python speechify_official.py script.md --language en

# Generate French podcast
python speechify_official.py script.md --language fr
```

### Advanced Options

```bash
# Custom output directory
python speechify_official.py script.md --output-dir my_podcasts

# Custom speakers
python speechify_official.py script.md --speakers daniel:custom_voice,anna:another_voice

# Custom output prefix
python speechify_official.py script.md --output-prefix my_show
```

### Testing & Debugging

```bash
# Test API connection
python speechify_official.py --test-api

# Test available voices
python speechify_official.py --test-voices

# Help and options
python speechify_official.py --help
```

## � Output Files

For each podcast generation, three files are created:

- **`podcast_speechify_[timestamp].mp3`** - High-quality audio
- **`podcast_transcript_[timestamp].json`** - Synchronized transcript
- **`podcast_subtitles_[timestamp].vtt`** - WebVTT subtitles

### JSON Transcript Structure

```json
{
  "podcast_transcript": {
    "total_duration": 15.7,
    "segments": [
      {
        "speaker": "daniel",
        "text": "Welcome to our podcast!",
        "start_time": 0.0,
        "end_time": 3.2,
        "duration": 3.2
      }
    ],
    "generated_with": "Speechify Official SDK",
    "timestamp": 1720464123
  }
}
```

## 🔧 Voice Mapping Logic

The system automatically selects appropriate voices using this priority:

1. **Language-specific mapping** (primary)
2. **Speaker configuration fallback**
3. **Gender-based fallback**
4. **Default voice fallback**

Example for Spanish (`--language es`):
- `Daniel:` text → `alejandro` voice
- `Anna:` text → `carmen` voice
- `Unknown speaker:` → Gender detection → Appropriate fallback

## 🐛 Troubleshooting

### API Issues

```bash
# Check API key
echo $SPEECHIFY_API_KEY  # Linux/Mac
echo %SPEECHIFY_API_KEY%  # Windows

# Test connection
python speechify_official.py --test-api
```

### Environment Issues

```bash
# Check Python version
python --version  # Should be 3.8+

# Recreate environment
rm -rf tts-env
python -m venv tts-env
source tts-env/bin/activate
pip install -r requirements.txt
```

### Audio Issues

```bash
# Install system audio libraries (if needed)
# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# macOS:
brew install ffmpeg

# Windows: Download FFmpeg and add to PATH
```

### Common Problems

| Problem | Solution |
|---------|----------|
| API key error | Check `.env` file and API key validity |
| Import errors | Ensure virtual environment is activated |
| Audio export fails | Install FFmpeg system-wide |
| No segments found | Check markdown format with `speaker:` labels |

## 📂 Project Structure

```
markdown-to-podcast/
├── speechify_official.py    # Main TTS script
├── requirements.txt         # Dependencies
├── README.md               # This documentation
├── LICENSE                 # MIT License
├── .env.example            # Environment template
├── .env                    # Your API configuration
├── examples/               # Example scripts
│   └── demo.md             # Sample podcast script
└── output/                 # Generated audio files
```

## 🌟 Advanced Features

### Custom Voice Assignment

```bash
# Override default voices for specific speakers
python speechify_official.py script.md --speakers daniel:custom_male,anna:custom_female
```

### Batch Processing

```bash
# Process multiple files
for file in scripts/*.md; do
  python speechify_official.py "$file" --language auto
done
```

### Integration Example

```python
from speechify_official import SpeechifyPodcastTTS

# Initialize TTS
tts = SpeechifyPodcastTTS()

# Generate podcast
result = tts.process_podcast_script(
    markdown_file="script.md",
    language="en",
    output_dir="output"
)

print(f"Generated: {result}")
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
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