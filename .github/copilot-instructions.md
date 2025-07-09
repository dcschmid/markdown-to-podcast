<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Deutsche Podcast TTS Projekt - Copilot Anweisungen

## Projektübersicht
Dieses Projekt konvertiert deutsche Podcast-Transkripte in hochqualitative MP3-Audio-Dateien mit XTTS v2 (Coqui TTS). 

## Technologie-Stack
- **Python 3.8+**
- **XTTS v2** (Coqui TTS) für Text-zu-Sprache und Voice Cloning
- **PyTorch** für Deep Learning Backend
- **Pydub** für Audio-Verarbeitung und MP3-Export
- **Soundfile/Librosa** für Audio-Manipulation

## Coding-Standards

### Deutsche Sprache
- Alle Kommentare, Docstrings und Benutzerausgaben auf Deutsch
- Variablennamen können englisch sein für bessere Code-Kompatibilität
- Fehlermeldungen und Logs auf Deutsch

### Audio-Verarbeitung
- Standardmäßig WAV für interne Verarbeitung, MP3 für Output
- Samplerate: 22kHz oder höher
- Voice Cloning: Referenz-Audio 5-20 Sekunden optimal
- Automatische Validierung von Audio-Eingaben

### TTS-Best-Practices
- Text-Preprocessing für bessere Sprachqualität
- Lange Texte in Segmente aufteilen (max 500 Zeichen)
- GPU-Beschleunigung wenn verfügbar
- Graceful Fallback zu CPU

### Error Handling
- Umfassende Try-Catch-Blöcke für Audio-Operations
- Benutzerfreundliche deutsche Fehlermeldungen
- Validierung von Eingabedateien und -formaten
- Automatische Cleanup von temporären Dateien

### Code-Organisation
- Hauptskripte: `text_to_speech.py`, `voice_clone.py`
- Hilfsfunktionen: `utils/helpers.py`
- Audio-Samples: `audio_samples/` (männlich/weiblich)
- Output: `output/` Verzeichnis

## Spezielle Anforderungen

### XTTS Integration
- Verwende immer `tts_models/multilingual/multi-dataset/xtts_v2`
- Language Parameter auf "de" setzen für Deutsch
- Device-Detection (CUDA/CPU) implementieren

### Deutsche Sprachoptimierung
- Umlaute und ß korrekt verarbeiten
- Deutsche Phonetik berücksichtigen
- Hochdeutsch als Standard

### Performance
- Batch-Verarbeitung für multiple Segmente
- Progress-Feedback für lange Verarbeitungen
- Speicher-effiziente Audio-Verarbeitung

Wenn du Code generierst, berücksichtige diese Projekt-spezifischen Anforderungen und halte den deutschen Fokus bei.
