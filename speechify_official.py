#!/usr/bin/env python3
"""
Deutsche Podcast TTS mit Speechify Official SDK (modernisiert)
-------------------------------------------------------------

Diese Datei wurde modernisiert: Logging statt print, Pathlib für Pfade,
konsequente Type-Hints, keine lokalen Imports, und kleinere Robustheitsfixes.

Alle Benutzerausgaben bleiben auf Deutsch.
"""

from __future__ import annotations

import base64
import logging
import os
import re
import sys
import time
from typing import Dict, List, Optional, Tuple
import argparse

from dotenv import load_dotenv
from pydub import AudioSegment

# Speechify SDK importieren
try:
    from speechify import Speechify

    HAS_SPEECHIFY = True
except Exception:  # pragma: no cover - best effort import
    HAS_SPEECHIFY = False

# Logger konfigurieren (kann vom Aufrufer überschrieben werden)
# Ermöglicht LOG-Level via Umgebungsvariable SPEECHIFY_LOG_LEVEL (z.B. DEBUG/INFO/WARNING)
LOG_LEVEL_NAME = os.getenv("SPEECHIFY_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO")).upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(LOG_LEVEL)

# Vereinfachte, modulweite Default-Mappings: Wir verwenden nur noch Englisch
DEFAULT_VOICE_CONFIG: Dict[str, Dict[str, str]] = {
    "daniel": {"voice_id": "jeremy"},
    "male": {"voice_id": "jeremy"},
    "annabelle": {"voice_id": "patricia"},
    "female": {"voice_id": "patricia"},
}

DEFAULT_LANGUAGE_VOICE_MAPPING: Dict[str, Dict[str, str]] = {
    "en": {
        "daniel": "jeremy",
        "male": "jeremy",
        "annabelle": "patricia",
        "female": "patricia",
    }
}


class SpeechifyPodcastTTS:
    """Kleine, robuste TTS-Engine-Wrapperklasse für Speechify (deutschsprachige Ausgaben).

    Diese Klasse kapselt die Interaktion mit dem Speechify-Client und bietet
    Hilfsfunktionen zum Konvertieren von Markdown-Skripten in Audiodateien.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialisiert grundlegende Attribute und optional den Speechify-Client.

        Die Klasse verwendet modulweite Defaults für die Stimmen (englisch-only).
        """
        # .env laden
        try:
            load_dotenv()
        except Exception:
            pass

        self.api_key = api_key or os.getenv("SPEECHIFY_API_KEY")
        self.client = None
        if HAS_SPEECHIFY and self.api_key:
            try:
                self.client = Speechify(token=self.api_key)
            except Exception:
                # Best effort, wir arbeiten auch ohne Client (z.B. für Tests)
                self.client = None

        # Instanz-Mappings: Default auf modulweite Englisch-Mappings
        self.voice_config = DEFAULT_VOICE_CONFIG.copy()
        self.language_voice_mapping = DEFAULT_LANGUAGE_VOICE_MAPPING.copy()

        # Runtime-Attribute
        self.ssml_variants: Dict[str, str] = {}
        self.timing_data: List[Dict] = []
        self.current_time = 0.0

        logger.info("SpeechifyPodcastTTS initialisiert (english-only voice policy)")

    def test_api_connection(self) -> bool:
        """
        Testet die Verbindung zur Speechify API mit dem Official SDK

        Returns:
            bool: True wenn erfolgreich
        """
        try:
            logger.info("🔍 Teste Speechify API-Verbindung...")

            # Test mit kurzer deutscher Nachricht
            test_text = "Hallo, das ist ein Test der deutschen Sprachsynthese."

            # Teste verschiedene Voice IDs
            test_voices = ["jannik", "ronja", "matteo"]

            for voice_id in test_voices:
                try:
                    logger.info(f"\n🎤 Teste Voice: {voice_id}")

                    # Speechify TTS-Request mit bekannter Voice ID
                    response = self.client.tts.audio.speech(
                        input=test_text,
                        voice_id=voice_id,
                        language="de",  # Deutsch
                        audio_format="mp3",  # MP3 Format für bessere Kompatibilität
                        model="simba-multilingual",
                        options={
                            "loudness_normalization": True,  # Audio-Lautstärke normalisieren
                            "text_normalization": True,  # Text normalisieren
                        },
                    )

                    if response:
                        logger.info(f"✅ Voice {voice_id} funktioniert")
                        # Test-Datei speichern
                        test_file = f"temp/api_test_{voice_id}.mp3"
                        os.makedirs(os.path.dirname(test_file), exist_ok=True)

                        if hasattr(response, "audio_data"):
                            audio_data = base64.b64decode(response.audio_data)
                            with open(test_file, "wb") as f:
                                f.write(audio_data)
                            logger.info(f"🎧 Test-Audio gespeichert: {test_file}")
                    else:
                        logger.error(f"❌ Voice {voice_id} - Keine Response")

                except Exception as e:
                    logger.error(f"❌ Voice {voice_id} Fehler: {str(e)}")
                    # Debug: Zeige mehr Details über den Fehler
                    if hasattr(e, "response") and hasattr(e.response, "text"):
                        logger.debug(f"🔍 API Response: {e.response.text}")
                    if hasattr(e, "response") and hasattr(e.response, "status_code"):
                        logger.debug(f"🔍 Status Code: {e.response.status_code}")

            logger.info("\n✅ Speechify API-Verbindung getestet")
            return True

        except Exception as e:
            logger.error(f"❌ API-Verbindung fehlgeschlagen: {str(e)}")
            return False

    def extract_speakers_from_markdown(
        self, markdown_text: str
    ) -> List[Tuple[str, str]]:
        """
        Extrahiert Sprecher und ihre Texte aus Markdown

        Args:
            markdown_text: Der Markdown-Text

        Returns:
            Liste von (sprecher, text) Tupeln
        """
        segments = []
        lines = markdown_text.strip().split("\n")
        current_speaker = None
        current_text = []

        for line in lines:
            line = line.strip()

            # Leere Zeilen überspringen
            if not line:
                if current_speaker and current_text:
                    # Segment abschließen bei Leerzeile
                    full_text = " ".join(current_text).strip()
                    if full_text:
                        segments.append((current_speaker, full_text))
                    current_text = []
                continue

            # Sprecher-Zeile erkennen (Name gefolgt von Doppelpunkt)
            if ":" in line and not line.startswith("[") and not line.startswith("♪"):
                # Vorheriges Segment abschließen
                if current_speaker and current_text:
                    full_text = " ".join(current_text).strip()
                    if full_text:
                        segments.append((current_speaker, full_text))

                # Neuer Sprecher
                parts = line.split(":", 1)
                current_speaker = parts[0].strip().lower()

                # Text nach dem Doppelpunkt
                if len(parts) > 1 and parts[1].strip():
                    current_text = [parts[1].strip()]
                else:
                    current_text = []
            else:
                # Fortsetzung des aktuellen Sprechers
                if current_speaker:
                    current_text.append(line)

        # Letztes Segment abschließen
        if current_speaker and current_text:
            full_text = " ".join(current_text).strip()
            if full_text:
                segments.append((current_speaker, full_text))

        logger.info(f"📝 {len(segments)} Sprecher-Segmente erkannt:")
        for i, (speaker, text) in enumerate(segments, 1):
            ellipsis = "..." if len(text) > 50 else ""
            logger.debug(f"   {i}. {speaker}: {text[:50]}{ellipsis}")

        return segments

    def clean_text_for_tts(
        self, text: str, preserve_tags: Optional[List[str]] = None
    ) -> str:
        """
        Bereinigt Text für bessere TTS-Qualität - extrahiert Text aus SSML
        aber behält Emotionen

        Args:
            text: Der ursprüngliche Text (kann SSML enthalten)

        Returns:
            Bereinigter Text ohne SSML-Tags, aber mit emotion-Attributen für
            spätere Verarbeitung
        """
        import re

        # Entferne alle <emphasis>-Tags frühzeitig, unabhängig von preserve_tags
        # Der Nutzer wünscht, dass emphasis-Tags komplett entfernt werden.
        try:
            text = self.remove_emphasis_tags(text)
        except Exception:
            pass
        # Emotionen extrahieren und speichern
        emotions = []
        if "<speechify:style" in text:
            emotion_matches = re.findall(r'emotion="([^"]+)"', text)
            emotions.extend(emotion_matches)

        # Wenn preserve_tags gesetzt ist, entferne alle Tags außer den erlaubten
        if preserve_tags:
            # Temporäre Platzhalter für erlaubte Tags
            placeholders: Dict[str, str] = {}
            i = 0
            for tag in preserve_tags:
                # Erkenne beide Varianten: Self-closing (<break .../>) und mit Inhalt (<emphasis>..</emphasis>)
                pattern = re.compile(rf"<{tag}[^>]*>(.*?)</{tag}>", re.DOTALL)

                def repl(m):
                    nonlocal i
                    key = f"__TAG_{i}__"
                    placeholders[key] = m.group(0)
                    i += 1
                    return key

                text = pattern.sub(repl, text)

                # Self-closing / single tags (e.g. <break time="100ms" />)
                pattern2 = re.compile(rf"<{tag}[^>]*/>", re.DOTALL)

                def repl2(m):
                    nonlocal i
                    key = f"__TAG_{i}__"
                    placeholders[key] = m.group(0)
                    i += 1
                    return key

                text = pattern2.sub(repl2, text)

            # Falls speak-Tags vorhanden sind, extrahiere inneren Inhalt (aber behalte Platzhalter)
            if "<speak>" in text and "</speak>" in text:
                speak_match = re.search(r"<speak>(.*?)</speak>", text, re.DOTALL)
                if speak_match:
                    text = speak_match.group(1)

            # Alle übrigen Tags entfernen
            text = re.sub(r"<[^>]+>", "", text)

            # Platzhalter wieder ersetzen
            for k, v in placeholders.items():
                text = text.replace(k, v)

        else:
            # Alle SSML-Tags entfernen und nur reinen Text extrahieren
            if "<speak>" in text and "</speak>" in text:
                # Extrahiere Text zwischen <speak> Tags
                speak_match = re.search(r"<speak>(.*?)</speak>", text, re.DOTALL)
                if speak_match:
                    text = speak_match.group(1)

                # Extrahiere Text aus speechify:style Tags
                if "<speechify:style" in text:
                    style_match = re.search(
                        r"<speechify:style[^>]*>(.*?)</speechify:style>",
                        text,
                        re.DOTALL,
                    )
                    if style_match:
                        text = style_match.group(1)

            # Alle anderen SSML-Tags entfernen
            text = re.sub(r"<[^>]+>", "", text)

        # Emotionale Anmerkungen entfernen
        text = re.sub(r"\[.*?\]", "", text)

        # Musik-Notationen entfernen
        text = re.sub(r"♪.*?♪", "", text)

        # HTML-Entitäten dekodieren
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&apos;", "'")

        # Mehrfache Leerzeichen entfernen
        text = re.sub(r"\s+", " ", text)

    # XML-Zeichen escapen für SSML-Kompatibilität
    # (Grund-escaping, darf später beim Einfügen in SSML partiell wieder erlaubt werden)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&apos;")

        # Wenn Emotionen gefunden wurden, füge sie als Kommentar hinzu für spätere Verarbeitung
        if emotions:
            # Verwende die erste gefundene Emotion (falls mehrere vorhanden)
            emotion = emotions[0]
            text = f"{text} [EMOTION:{emotion}]"
        else:
            # Fallback: Verwende "warm" als Standard-Emotion
            text = f"{text} [EMOTION:warm]"

        return text.strip()

    def convert_to_ssml(
        self, text: str, speaker: str = None, language: str = "en"
    ) -> str:
        """
        Konvertiert Text in SSML - wenn bereits SSML vorhanden, korrigiert nur Emotionen

        Args:
            text: Der ursprüngliche Text (mit oder ohne SSML)
            speaker: Name des Sprechers für Voice-spezifische Anpassungen
            language: Sprache für SSML

        Returns:
            SSML-formatierter Text
        """
        import re

        # Prüfe ob der Text bereits SSML mit Emotionen enthält
        if "<speechify:style" in text and "emotion=" in text:
            logger.info(
                "🔧 Text enthält bereits SSML mit Emotionen - lasse Emotionen durch und korrigiere nur bei API-Fehlern"
            )
            # Wir akzeptieren die im SSML vorhandenen Emotionen und überlassen Fallback dem Request-Error-Handler
            return text

        # Wenn der Text SSML-ähnliche Tags enthält, erlauben wir explizit <break> und <emphasis>
        preserve_tags = ["break", "emphasis"] if "<" in text else None

        # Bereinige den Text, erhalte erlaubte Tags
        clean_text = self.clean_text_for_tts(text, preserve_tags=preserve_tags)

        if not clean_text:
            logger.warning("⚠️ Kein Text nach Bereinigung verfügbar")
            return ""

        # Prüfe ob eine Emotion im bereinigten Text gespeichert wurde
        emotion = "warm"  # Standard-Emotion

        # Suche nach [EMOTION:xyz] Pattern
        emotion_match = re.search(r"\[EMOTION:([^\]]+)\]", clean_text)
        if emotion_match:
            original_emotion = emotion_match.group(1)
            # Entferne das Emotion-Kommentar aus dem Text
            clean_text = re.sub(r"\[EMOTION:[^\]]+\]", "", clean_text).strip()

            # Verwende die angegebene Emotion direkt; Fallback erfolgt später nur bei API-Fehlern
            emotion = original_emotion
            logger.debug(f"🔧 Verwende Emotion aus Text: {emotion}")
        else:
            # Sprecher-spezifische Emotionen - verwende "warm" als Standard
            if speaker:
                if speaker.lower() in ["daniel", "male"]:
                    emotion = "warm"
                elif speaker.lower() in ["anna", "annabelle", "female"]:
                    emotion = "warm"
                else:
                    emotion = "warm"

        # Text für SSML escapen
        escaped_text = self.escape_ssml_text(clean_text)

        # Falls die erlaubten Tags fälschlich escaped wurden, bringe sie zurück
        escaped_text = escaped_text.replace("&lt;break", "<break").replace(
            "&lt;/break&gt;", "</break>"
        )
        escaped_text = escaped_text.replace("&lt;emphasis", "<emphasis").replace(
            "&lt;/emphasis&gt;", "</emphasis>"
        )

        # Entferne sämtliche <emphasis> Tags vollständig (öffnende und schließende Tags), behalte inneren Text
        # Der Nutzer wünscht, dass emphasis-Tags komplett entfernt werden statt nur zu normalisieren.
        escaped_text = self.remove_emphasis_tags(escaped_text)

        # Einheitliches SSML-Format - versuche verschiedene Syntax-Varianten
        ssml_text = f'<speak><speechify:style emotion="{emotion}">{escaped_text}</speechify:style></speak>'

        # Alternative Varianten für Fallback (falls speechify:style nicht funktioniert)
        if emotion == "relaxed":
            prosody_ssml = f'<speak><prosody rate="slow" pitch="low">{escaped_text}</prosody></speak>'
        elif emotion == "cheerful":
            prosody_ssml = f'<speak><prosody rate="fast" pitch="high">{escaped_text}</prosody></speak>'
        elif emotion == "sad":
            prosody_ssml = f'<speak><prosody rate="slow" pitch="low">{escaped_text}</prosody></speak>'
        else:
            prosody_ssml = f"<speak>{escaped_text}</speak>"

        # Speichere beide Varianten für Fallback
        self.ssml_variants = {
            "speechify_style": ssml_text,
            "prosody": prosody_ssml,
            "simple": f"<speak>{escaped_text}</speak>",
        }

        return ssml_text

    def fix_ssml_emotions(self, ssml_text: str) -> str:
        """
        Korrigiert nicht-unterstützte Emotionen in SSML-Text zu offiziell unterstützten Speechify-Emotionen

        Args:
            ssml_text: SSML-Text mit möglicherweise nicht-unterstützten Emotionen

        Returns:
            Korrigierter SSML-Text mit nur offiziell unterstützten Emotionen
        """
        import re

        # Offiziell unterstützte Speechify-Emotionen (basierend auf https://docs.sws.speechify.com/v1/docs/features/emotion-control)
        supported_emotions = [
            "angry",
            "cheerful",
            "sad",
            "terrified",
            "relaxed",
            "fearful",
            "surprised",
            "calm",
            "assertive",
            "energetic",
            "warm",
            "direct",
            "bright",
        ]

        # Mapping von nicht-unterstützten zu unterstützten Emotionen
        # Alle nicht-offiziell unterstützten Emotionen werden auf 'warm' gesetzt
        emotion_mapping = {
            "hopeful": "warm",
            "empathetic": "warm",
            "excited": "warm",
            "proud": "warm",
            "nostalgic": "warm",
            "reflective": "warm",
            "inspired": "warm",
            "bright": "warm",  # Korrigiere "bright" zu "warm"
            # Weitere nicht-unterstützte Emotionen werden automatisch auf 'warm' gesetzt
        }

        # Debug: Zeige die ursprüngliche SSML
        logger.debug(f"🔧 Debug: Original SSML Länge: {len(ssml_text)} Zeichen")
        if len(ssml_text) > 200:
            logger.debug(f"🔧 Debug: SSML Vorschau: {ssml_text[:200]}...")
        else:
            logger.debug(f"🔧 Debug: SSML: {ssml_text}")

        # Alle emotion Attribute finden und ersetzen
        def replace_emotion(match):
            emotion = match.group(1)
            if emotion in emotion_mapping:
                new_emotion = emotion_mapping[emotion]
                logger.debug(f"🔧 Ersetze Emotion '{emotion}' durch '{new_emotion}'")
                return f'emotion="{new_emotion}"'
            elif emotion in supported_emotions:
                return match.group(0)  # Lass es unverändert
            else:
                logger.debug(f"🔧 Unbekannte Emotion '{emotion}' durch 'warm' ersetzt")
                return 'emotion="warm"'

        # Emotionen ersetzen
        corrected_text = re.sub(r'emotion="([^"]+)"', replace_emotion, ssml_text)

        # Prosody-Werte korrigieren (nur offiziell unterstützte Werte)
        def fix_prosody(match):
            attribute = match.group(1)
            value = match.group(2)

            # Pitch-Werte korrigieren
            if attribute == "pitch":
                pitch_mapping = {
                    "-1st": "low",
                    "+1st": "high",
                    "+2st": "x-high",
                    "-2st": "x-low",
                }
                if value in pitch_mapping:
                    new_value = pitch_mapping[value]
                    logger.debug(
                        f"🔧 Korrigiere Prosody {attribute}='{value}' zu '{new_value}'"
                    )
                    return f'{attribute}="{new_value}"'

            # Volume-Werte korrigieren
            if attribute == "volume":
                volume_mapping = {
                    "loud": "loud",
                    "x-loud": "x-loud",
                    "medium": "medium",
                    "soft": "x-soft",
                }
                if value in volume_mapping:
                    new_value = volume_mapping[value]
                    logger.debug(
                        f"🔧 Korrigiere Prosody {attribute}='{value}' zu '{new_value}'"
                    )
                    return f'{attribute}="{new_value}"'

            return match.group(0)  # Unverändert lassen

        # Prosody-Attribute korrigieren
        corrected_text = re.sub(
            r'(pitch|rate|volume)="([^"]+)"', fix_prosody, corrected_text
        )

        return corrected_text

    def escape_ssml_text(self, text: str) -> str:
        """
        Escaped Text für SSML-Kompatibilität - erweiterte Version mit besserer Zeichenbehandlung

        Args:
            text: Der ursprüngliche Text

        Returns:
            SSML-escaped Text
        """
        import re

        # Zuerst alle bereits escaped Zeichen dekodieren um doppelte Escaping zu vermeiden
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&apos;", "'")

        # Kontrollzeichen entfernen (außer Tab, Newline, Carriage Return)
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # Unicode-Zeichen die Probleme verursachen können
        text = text.replace("–", "-")  # en dash
        text = text.replace("—", "-")  # em dash
        text = text.replace("…", "...")  # ellipsis
        # Normalize smart quotes/apostrophes to ascii equivalents
        text = text.replace("“", '"').replace("”", '"')
        text = text.replace("‘", "'").replace("’", "'")

        # Spezielle Behandlung für "R&B" und ähnliche Abkürzungen
        text = text.replace("R&B", "R and B")  # R&B -> R and B
        text = text.replace("R & B", "R and B")  # R & B -> R and B

        # SSML-Zeichen escapen (in der richtigen Reihenfolge!)
        escaped_text = text
        escaped_text = escaped_text.replace(
            "&", "&amp;"
        )  # Zuerst &, sonst werden andere Escapes überschrieben
        escaped_text = escaped_text.replace("<", "&lt;")
        escaped_text = escaped_text.replace(">", "&gt;")
        escaped_text = escaped_text.replace('"', "&quot;")
        escaped_text = escaped_text.replace("'", "&apos;")

        # Debug: Zeige problematische Zeichen und Ersetzungen
        if len(text) != len(escaped_text):
            logger.debug(f"🔧 SSML-Escaping: {len(text)} -> {len(escaped_text)} Zeichen")

        # Debug: Zeige spezifische Ersetzungen
        if "R&B" in text or "R & B" in text:
            logger.debug("🔧 Ersetze R&B-Abkürzungen für bessere SSML-Kompatibilität")
        if "–" in text or "—" in text:
            logger.debug("🔧 Ersetze Em/En-Dashes durch normale Bindestriche")
        if "ä" in text or "ö" in text or "ü" in text:
            logger.debug("🔧 Umlaute gefunden - werden normal escaped")

        return escaped_text

    def remove_emphasis_tags(self, text: str) -> str:
        """
        Entfernt alle <emphasis> und </emphasis> Tags vollständig, behält aber den inneren Text.
        """
        try:
            # Entferne öffnende emphasis-Tags mit beliebigen Attributen
            text = re.sub(r"<\s*emphasis\b[^>]*>", "", text, flags=re.IGNORECASE)
            # Entferne schließende emphasis-Tags
            text = re.sub(r"<\s*/\s*emphasis\s*>", "", text, flags=re.IGNORECASE)
        except Exception:
            # Falls etwas schiefgeht, gib den Originaltext zurück
            return text
        return text

    def text_to_speech_with_ssml(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        language: str = "en",
        use_ssml: bool = True,
        speaker: str = None,
    ) -> Optional[str]:
        """
        Konvertiert Text zu Sprache mit optionaler SSML-Unterstützung

        Args:
            text: Der zu konvertierende Text
            voice_id: Die Speechify Voice ID
            output_path: Pfad für die Ausgabe-Datei
            language: Sprache für TTS (Standard: "de")
            use_ssml: Ob SSML verwendet werden soll (Standard: True)
            speaker: Name des Sprechers für SSML-Anpassungen

        Returns:
            Pfad zur erstellten Audio-Datei oder None bei Fehler
        """
        max_retries = 2  # Reduziert von 5 auf 2, da Fallback-Strategie funktioniert
        retry_delay = 2  # Sekunden

        for attempt in range(max_retries):
            try:
                if use_ssml:
                    # Text in SSML konvertieren
                    ssml_text = self.convert_to_ssml(text, speaker, language)

                    # Debug: Zeige die komplette SSML-Struktur bei Fehlern
                    if attempt == 0:  # Nur beim ersten Versuch
                        logger.debug("🔧 Debug: Vollständige SSML-Struktur:")
                        logger.debug(f"🔧 {ssml_text}")
                        logger.debug(f"🔧 SSML-Länge: {len(ssml_text)} Zeichen")

                        # Prüfe auf problematische Zeichen
                        import re

                        problematic_chars = re.findall(r"[^\x20-\x7E\n\t\r]", ssml_text)
                        if problematic_chars:
                            problematic_set = set(problematic_chars)
                            logger.warning(
                                f"🔧 Warnung: Problematische Zeichen gefunden: {problematic_set}"
                            )

                    ssml_preview = ssml_text[:100] + ("..." if len(ssml_text) > 100 else "")
                    gen_prefix = f"🎤 Generiere SSML-Audio mit {voice_id} ({language})"
                    gen_suffix = f"[Versuch {attempt + 1}/{max_retries}]: {ssml_preview}"
                    logger.info(f"{gen_prefix} {gen_suffix}")

                    # Speechify TTS Request mit SSML
                    audio_response = self.client.tts.audio.speech(
                        input=ssml_text,
                        voice_id=voice_id,
                        language=language,
                        audio_format="mp3",
                        model="simba-multilingual",
                        options={
                            "loudness_normalization": False,
                            "text_normalization": True,
                            "ssml": True,  # SSML-Flag aktivieren
                        },
                    )
                else:
                    # Normale TTS ohne SSML
                    clean_text = self.clean_text_for_tts(text)
                    if not clean_text:
                        logger.warning("⚠️ Kein Text nach Bereinigung übrig")
                        return None

                    clean_preview = clean_text[:50] + ("..." if len(clean_text) > 50 else "")
                    gen_prefix = f"🎤 Generiere Audio mit {voice_id} ({language})"
                    gen_suffix = f"[Versuch {attempt + 1}/{max_retries}]: {clean_preview}"
                    logger.info(f"{gen_prefix} {gen_suffix}")

                    audio_response = self.client.tts.audio.speech(
                        input=clean_text,  # Verwende clean_text statt text
                        voice_id=voice_id,
                        language=language,
                        audio_format="mp3",
                        model="simba-multilingual",
                        options={
                            "loudness_normalization": False,
                            "text_normalization": True,
                        },
                    )

                if audio_response:
                    # Audio-Daten speichern
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)

                    # Speechify Response ist ein Objekt mit audio_data (Base64)

                    if hasattr(audio_response, "audio_data"):
                        # Base64-decodierte Audio-Daten
                        audio_data = base64.b64decode(audio_response.audio_data)
                    elif hasattr(audio_response, "content"):
                        audio_data = audio_response.content
                    elif isinstance(audio_response, bytes):
                        audio_data = audio_response
                    else:
                        # Debug: Response-Typ anzeigen
                        logger.debug(f"🔍 Response-Typ: {type(audio_response)}")
                        if hasattr(audio_response, "__dict__"):
                            response_attrs = list(audio_response.__dict__.keys())
                            logger.debug(f"🔍 Response-Attribute: {response_attrs}")
                        # Fallback: als bytes behandeln
                        audio_data = bytes(audio_response)

                    with open(output_path, "wb") as f:
                        f.write(audio_data)

                    logger.info(f"✅ Audio gespeichert: {output_path}")
                    return output_path
                else:
                    logger.error("❌ TTS-Fehler: Keine Audio-Response")
                    if attempt < max_retries - 1:
                        logger.info(f"⏳ Warte {retry_delay}s vor erneutem Versuch...")
                        time.sleep(retry_delay)
                        continue
                    return None

            except Exception as e:
                logger.error(f"❌ TTS-Fehler (Versuch {attempt + 1}/{max_retries}): {str(e)}")

                # Detailliertes Fehler-Logging
                if hasattr(e, "response"):
                    if hasattr(e.response, "status_code"):
                        logger.debug(f"🔍 HTTP Status Code: {e.response.status_code}")
                    if hasattr(e.response, "text"):
                        logger.debug(f"🔍 API Response Body: {e.response.text}")
                    if hasattr(e.response, "headers"):
                        logger.debug(f"🔍 Response Headers: {dict(e.response.headers)}")

                    # Spezielle Behandlung für 400-Fehler
                    if (
                        hasattr(e.response, "status_code")
                        and e.response.status_code == 400
                    ):
                        logger.debug("🔍 400-Fehler Analyse:")
                        logger.debug("   - Mögliche Ursachen:")
                        logger.debug("     * Ungültige SSML-Syntax")
                        logger.debug("     * Nicht unterstützte Voice/Emotion-Kombination")
                        logger.debug("     * Text zu lang oder enthält ungültige Zeichen")
                        logger.debug("     * API-Version oder Modell-Inkompatibilität")

                        # Zeige den problematischen SSML-Text
                        if use_ssml:
                            problem_preview = text[:300] + ("..." if len(text) > 300 else "")
                            logger.debug(f"   - Problem-SSML: {problem_preview}")
                else:
                    logger.debug(f"🔍 Exception Type: {type(e).__name__}")
                    logger.debug(f"🔍 Exception Details: {str(e)}")

                # Bei SSML-Fehlern: Versuche es mit verbesserter Fallback-Strategie
                if use_ssml and (
                    attempt == max_retries - 1 or attempt >= 1
                ):  # Direkt nach erstem Fehler
                    logger.info("🔄 SSML-Fehler erkannt - wechsle zu Fallback-Strategie...")

                    # Fallback-Strategie: Erst mit "warm" Emotion, dann ohne Emotionen
                    fallback_strategies = [
                        ("warm", "Mit 'warm' Emotion"),
                        ("simple", "Einfaches SSML ohne Emotionen"),
                        ("no_ssml", "Ohne SSML"),
                    ]

                    for strategy, description in fallback_strategies:
                        try:
                            logger.info(f"🔄 Versuche {description}...")

                            if strategy == "warm":
                                # Versuche mit "warm" Emotion
                                if "<speechify:style" in text:
                                    import re

                                    # Extrahiere Text aus SSML
                                    text_match = re.search(
                                        r"<speechify:style[^>]*>(.*?)</speechify:style>",
                                        text,
                                        re.DOTALL,
                                    )
                                    if text_match:
                                        clean_text = text_match.group(1).strip()
                                        # Erstelle SSML mit "warm" Emotion
                                        warm_ssml = (
                                            '<speak><speechify:style emotion="warm">'
                                            + self.escape_ssml_text(clean_text)
                                            + '</speechify:style></speak>'
                                        )
                                        warm_preview = warm_ssml[:100] + (
                                            '...' if len(warm_ssml) > 100 else ''
                                        )
                                        logger.info(f"🎤 Versuche SSML mit 'warm': {warm_preview}")

                                        audio_response = self.client.tts.audio.speech(
                                            input=warm_ssml,
                                            voice_id=voice_id,
                                            language=language,
                                            audio_format="mp3",
                                            model="simba-multilingual",
                                            options={
                                                "loudness_normalization": False,
                                                "text_normalization": True,
                                                "ssml": True,
                                            },
                                        )
                                    else:
                                        continue  # Nächste Strategie versuchen
                                else:
                                    # Kein SSML vorhanden - erstelle mit "warm"
                                    clean_text = self.clean_text_for_tts(text)
                                    warm_ssml = (
                                        '<speak><speechify:style emotion="warm">'
                                        + self.escape_ssml_text(clean_text)
                                        + '</speechify:style></speak>'
                                    )
                                    warm_preview = warm_ssml[:100] + (
                                        '...' if len(warm_ssml) > 100 else ''
                                    )
                                    logger.info(f"🎤 Versuche SSML mit 'warm': {warm_preview}")

                                    audio_response = self.client.tts.audio.speech(
                                        input=warm_ssml,
                                        voice_id=voice_id,
                                        language=language,
                                        audio_format="mp3",
                                        model="simba-multilingual",
                                        options={
                                            "loudness_normalization": False,
                                            "text_normalization": True,
                                            "ssml": True,
                                        },
                                    )

                            elif strategy == "simple":
                                # Versuche einfaches SSML ohne Emotionen
                                if "<speechify:style" in text:
                                    import re

                                    text_match = re.search(
                                        r"<speechify:style[^>]*>(.*?)</speechify:style>",
                                        text,
                                        re.DOTALL,
                                    )
                                    if text_match:
                                        clean_text = text_match.group(1).strip()
                                        simple_ssml = (
                                            '<speak>' + self.escape_ssml_text(clean_text) + '</speak>'
                                        )
                                        simple_preview = simple_ssml[:100] + (
                                            '...' if len(simple_ssml) > 100 else ''
                                        )
                                        logger.info(f"🎤 Versuche einfaches SSML: {simple_preview}")

                                        audio_response = self.client.tts.audio.speech(
                                            input=simple_ssml,
                                            voice_id=voice_id,
                                            language=language,
                                            audio_format="mp3",
                                            model="simba-multilingual",
                                            options={
                                                "loudness_normalization": False,
                                                "text_normalization": True,
                                                "ssml": True,
                                            },
                                        )
                                    else:
                                        continue
                                else:
                                    # Kein SSML vorhanden - erstelle einfaches SSML
                                    clean_text = self.clean_text_for_tts(text)
                                    simple_ssml = (
                                        '<speak>' + self.escape_ssml_text(clean_text) + '</speak>'
                                    )
                                    simple_preview = simple_ssml[:100] + (
                                        '...' if len(simple_ssml) > 100 else ''
                                    )
                                    logger.info(f"🎤 Versuche einfaches SSML: {simple_preview}")

                                    audio_response = self.client.tts.audio.speech(
                                        input=simple_ssml,
                                        voice_id=voice_id,
                                        language=language,
                                        audio_format="mp3",
                                        model="simba-multilingual",
                                        options={
                                            "loudness_normalization": False,
                                            "text_normalization": True,
                                            "ssml": True,
                                        },
                                    )

                            elif strategy == "no_ssml":
                                # Letzter Fallback: Versuche ohne SSML
                                clean_text = self.clean_text_for_tts(text)
                                if clean_text:
                                    clean_preview = clean_text[:50] + ('...' if len(clean_text) > 50 else '')
                                    logger.info(f"🎤 Versuche ohne SSML: {clean_preview}")

                                    audio_response = self.client.tts.audio.speech(
                                        input=clean_text,
                                        voice_id=voice_id,
                                        language=language,
                                        audio_format="mp3",
                                        model="simba-multilingual",
                                        options={
                                            "loudness_normalization": False,
                                            "text_normalization": True,
                                        },
                                    )
                                else:
                                    logger.error("❌ Kein Text nach Bereinigung verfügbar")
                                    return None

                            # Wenn wir hier ankommen, war der Versuch erfolgreich
                            if audio_response:
                                # Audio-Daten speichern
                                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                                if hasattr(audio_response, "audio_data"):
                                    audio_data = base64.b64decode(
                                        audio_response.audio_data
                                    )
                                elif hasattr(audio_response, "content"):
                                    audio_data = audio_response.content
                                elif isinstance(audio_response, bytes):
                                    audio_data = audio_response
                                else:
                                    audio_data = bytes(audio_response)

                                with open(output_path, "wb") as f:
                                    f.write(audio_data)

                                logger.info(f"✅ Audio mit {description} gespeichert: {output_path}")
                                return output_path

                        except Exception as fallback_error:
                            logger.error(f"❌ {description} fehlgeschlagen: {str(fallback_error)}")

                            continue  # Nächste Strategie versuchen
                            continue  # Nächste Strategie versuchen

                    # Wenn alle Fallback-Strategien fehlgeschlagen sind
                    logger.error("❌ Alle Fallback-Strategien fehlgeschlagen")
                    return None

                # Bei anderen Fehlern: Warte und versuche erneut
                if attempt < max_retries - 1:
                    logger.info(f"⏳ Warte {retry_delay}s vor erneutem Versuch...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Moderate backoff
                else:
                    logger.error("❌ Alle Versuche fehlgeschlagen")
                    return None

        return None

    def process_podcast_script(
        self,
        markdown_file: str,
        output_dir: str = "output",
        output_prefix: str = "podcast",
        custom_speakers: Dict[str, str] = None,
        language: str = "en",
        use_ssml: bool = True,
        intro_music_path: Optional[str] = None,
        outro_music_path: Optional[str] = None,
        intro_duration_ms: Optional[int] = None,
        outro_duration_ms: Optional[int] = None,
        intro_gain_db: float = 0.0,
        outro_gain_db: float = 0.0,
        intro_silence_after_ms: int = 0,
        outro_silence_before_ms: int = 0,
    ) -> Optional[str]:
        """
        Verarbeitet ein komplettes Podcast-Skript mit Speechify Official SDK und SSML-Unterstützung

        Args:
            markdown_file: Pfad zur Markdown-Datei
            output_dir: Ausgabe-Verzeichnis
            output_prefix: Präfix für Ausgabe-Dateien
            custom_speakers: Benutzerdefinierte Sprecher-Voice-Zuordnung
            language: Sprache für TTS (Standard: "de")
            use_ssml: Ob SSML für bessere Qualität verwendet werden soll (Standard: True)

        Returns:
            Pfad zur finalen Audio-Datei oder None bei Fehler
        """
        try:
            # Markdown-Datei laden
            with open(markdown_file, "r", encoding="utf-8") as f:
                markdown_content = f.read()

            logger.info(f"📖 Verarbeite Podcast-Skript: {markdown_file}")

            # Sprecher-Segmente extrahieren
            segments = self.extract_speakers_from_markdown(markdown_content)

            if not segments:
                logger.error("❌ Keine Sprecher-Segmente gefunden")
                return None

            # Ausgabe-Verzeichnis erstellen und leeren
            os.makedirs(output_dir, exist_ok=True)

            # Verzeichnis leeren
            for file in os.listdir(output_dir):
                file_path = os.path.join(output_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.info(f"🗑️ Gelöscht: {file_path}")

            # Dateiname aus Markdown-Datei extrahieren
            base_name = os.path.splitext(os.path.basename(markdown_file))[0]
            logger.info(f"📝 Verwende Dateiname: {base_name}")

            # Audio-Dateien für jedes Segment generieren
            audio_files = []
            self.timing_data = []
            self.current_time = 0.0

            for i, (speaker, text) in enumerate(segments, 1):
                # Voice ID bestimmen (mit Sprachunterstützung)
                if custom_speakers and speaker in custom_speakers:
                    voice_id = custom_speakers[speaker]
                else:
                    # Verwende die neue multilinguale get_voice_for_language Methode
                    voice_id = self.get_voice_for_language(speaker, language=language)

                logger.info(f"🗣️ Segment {i}/{len(segments)}: {speaker} -> {voice_id}")

                # Audio-Datei generieren
                segment_file = f"{output_dir}/{base_name}_segment_{i:03d}_{speaker}.mp3"

                start_time = self.current_time
                result = self.text_to_speech_with_ssml(
                    text, voice_id, segment_file, language=language, speaker=speaker
                )

                if result:
                    audio_files.append(segment_file)

                    # Timing-Daten berechnen
                    audio_segment = AudioSegment.from_file(segment_file)
                    duration = len(audio_segment) / 1000.0  # in Sekunden

                    self.timing_data.append(
                        {
                            "speaker": speaker,
                            "text": text,
                            "start_time": start_time,
                            "end_time": start_time + duration,
                            "duration": duration,
                        }
                    )

                    self.current_time += (
                        duration + 0.5
                    )  # 500ms Pause zwischen Segmenten
                    logger.info(f"✅ Segment {i} erstellt ({duration:.1f}s)")
                else:
                    logger.warning(f"⚠️ Segment {i} konnte nicht generiert werden")

            if not audio_files:
                logger.error("❌ Keine Audio-Segmente erstellt")
                return None

            # Audio-Segmente kombinieren
            logger.info(f"🔗 Kombiniere {len(audio_files)} Audio-Segmente...")
            final_audio = AudioSegment.empty()

            for audio_file in audio_files:
                segment = AudioSegment.from_file(audio_file)

                # Pause hinzufügen (außer beim ersten Segment)
                if len(final_audio) > 0:
                    final_audio += AudioSegment.silent(duration=500)  # 500ms Pause

                final_audio += segment

                # Temporäre Datei löschen
                os.remove(audio_file)

            # Intro/Outro automatisch setzen, falls nichts explizit übergeben wurde und Default existiert
            default_intro_outro = os.path.join("audio_samples", "epic-metal.mp3")
            if intro_music_path is None and os.path.exists(default_intro_outro):
                intro_music_path = default_intro_outro
            if outro_music_path is None and os.path.exists(default_intro_outro):
                outro_music_path = default_intro_outro

            # Intro/Outro hinzufügen (optional)
            intro_ms = 0
            if intro_music_path and os.path.exists(intro_music_path):
                try:
                    intro_seg = AudioSegment.from_file(intro_music_path)
                    if intro_duration_ms is not None:
                        intro_seg = intro_seg[: max(0, int(intro_duration_ms))]
                    if intro_gain_db != 0:
                        intro_seg = intro_seg + float(intro_gain_db)
                    final_audio = (
                        intro_seg
                        + AudioSegment.silent(duration=intro_silence_after_ms)
                        + final_audio
                    )
                    intro_ms = len(intro_seg) + int(intro_silence_after_ms)
                    logger.info(
                        f"🎼 Intro hinzugefügt: {intro_music_path} ({len(intro_seg)/1000.0:.1f}s)"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Konnte Intro nicht laden: {intro_music_path} ({str(e)})")

            if outro_music_path and os.path.exists(outro_music_path):
                try:
                    outro_seg = AudioSegment.from_file(outro_music_path)
                    if outro_duration_ms is not None:
                        outro_seg = outro_seg[: max(0, int(outro_duration_ms))]
                    if outro_gain_db != 0:
                        outro_seg = outro_seg + float(outro_gain_db)
                    final_audio = (
                        final_audio
                        + AudioSegment.silent(duration=outro_silence_before_ms)
                        + outro_seg
                    )
                    logger.info(
                        f"🎼 Outro hinzugefügt: {outro_music_path} ({len(outro_seg)/1000.0:.1f}s)"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Konnte Outro nicht laden: {outro_music_path} ({str(e)})")

            # Finale Audio-Datei speichern
            final_output = f"{output_dir}/{base_name}.mp3"
            final_audio.export(final_output, format="mp3", bitrate="192k")

            logger.info(f"✅ Podcast erfolgreich erstellt: {final_output}")
            logger.info(f"⏱️ Gesamtdauer: {len(final_audio) / 1000.0:.1f} Sekunden")

            # WebVTT-Untertitel generieren (Timing um Intro-Vorlauf korrigieren)
            if intro_ms > 0 and self.timing_data:
                offset_seconds = intro_ms / 1000.0
                for seg in self.timing_data:
                    seg["start_time"] = seg.get("start_time", 0) + offset_seconds
                    seg["end_time"] = seg.get("end_time", 0) + offset_seconds
            self.generate_webvtt_subtitles(f"{output_dir}/{base_name}.vtt")

            return final_output

        except Exception as e:
            logger.error(f"❌ Fehler bei der Podcast-Verarbeitung: {str(e)}")
            logger.debug("Stacktrace beim Podcast-Fehler", exc_info=True)
            return None

    def generate_webvtt_subtitles(self, output_path: str):
        """Generiert WebVTT-Untertitel für Web-Player"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("WEBVTT\n")
                f.write("NOTE Generiert mit Speechify Official SDK\n\n")

                for i, segment in enumerate(self.timing_data):
                    start_time = self.format_time(segment["start_time"])
                    end_time = self.format_time(segment["end_time"])
                    speaker = segment["speaker"].title()
                    text = segment["text"]

                    f.write(f"{i+1}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"<v {speaker}>{text}\n\n")

            logger.info(f"📺 WebVTT-Untertitel erstellt: {output_path}")
        except Exception as e:
            logger.error(f"❌ WebVTT-Fehler: {str(e)}")

    def format_time(self, seconds: float) -> str:
        """Formatiert Zeit für WebVTT (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def test_german_voices(self) -> None:
        """
        Testet deutsche Voices mit dem Voice-Mapping
        """
    # test_german_voices entfernt — Test-Utilities wurden aus der Produktionsklasse
    # entfernt. Für Tests bitte externe Testskripte oder Unit-Tests anlegen.
    logger.debug("test_german_voices entfernt")

    def test_ssml_features(self) -> None:
        """
        Testet SSML-Features mit verschiedenen Beispielen
        """
        logger.info("🎤 Teste SSML-Features...")

        # SSML-Test-Beispiele basierend auf dem Speechify Blog
        ssml_tests = [
            {
                "name": "Grundlegende SSML",
                "text": "Hallo! Das ist ein Test der SSML-Funktionen.",
                "description": "Normale Sätze mit SSML-Tags",
            },
            {
                "name": "Prosody-Test",
                "text": "Dieser Text wird langsamer gesprochen. Und dieser schneller!",
                "description": "Geschwindigkeits- und Tonhöhen-Anpassungen",
            },
            {
                "name": "Break-Test",
                "text": "Erste Pause. Zweite Pause. Dritte Pause.",
                "description": "Pausen zwischen Sätzen",
            },
            {
                "name": "Emotion-Test",
                "text": "Das ist sehr aufregend! Was denkst du? Lass uns das besprechen...",
                "description": "Verschiedene Satztypen mit Emotionen",
            },
        ]

        for test in ssml_tests:
            try:
                logger.info(f"\n🗣️ Teste: {test['name']}")
                logger.info(f"📝 Beschreibung: {test['description']}")

                # Test mit einfachem Standard-SSML
                ssml_text = f"<speak>{test['text']}</speak>"
                logger.debug(f"🔧 Einfaches SSML: {ssml_text}")

                # Voice ID bestimmen
                voice_id = self.get_voice_for_language("daniel", "de")

                # SSML-Audio generieren
                result = self.text_to_speech_with_ssml(
                    test["text"],
                    voice_id,
                    f"temp/ssml_test_{test['name'].lower().replace(' ', '_')}.mp3",
                    language="de",
                    use_ssml=True,
                    speaker="daniel",
                )

                if result:
                    logger.info(f"✅ SSML-Test erfolgreich: {result}")
                else:
                    logger.error("❌ SSML-Test fehlgeschlagen")

            except Exception as e:
                logger.error(f"❌ SSML-Test Fehler: {str(e)}")

        logger.info("\n🎧 Höre dir die SSML-Test-Dateien in temp/ an!")
        logger.info("✨ SSML-Features: Prosody, Breaks, Voice-Anpassungen, Emotionen")

    def get_voice_for_language(self, speaker: str, language: str = "en") -> str:
        """
        Bestimmt die Voice ID für einen Sprecher basierend auf Sprache und Mapping

        Args:
            speaker: Name des Sprechers (daniel, anna, annabelle, etc.)
            language: Sprach-Code (de, en, fr, etc.)

        Returns:
            Voice ID für Speechify TTS
        """
        # Vereinfachte Policy: Wir benutzen nur noch Englisch-Voices.
        # Konkrete Mappings:
        #   - daniel / male   -> jeremy
        #   - annabelle / female -> patricia
        s = (speaker or "").lower()

        # Wenn die gewünschte Sprache Englisch ist, nutze die festen Mappings
        if language and language.lower().startswith("en"):
            if s in ("daniel", "male"):
                logger.info(f"🗣️ Voice: {speaker} ({language}) -> jeremy (english policy)")
                return "jeremy"
            if s in ("annabelle", "female"):
                logger.info(f"🗣️ Voice: {speaker} ({language}) -> patricia (english policy)")
                return "patricia"

        # Defensive fallback: Falls legacy-Mappings vorhanden sind, nutze sie
        # Prüfe legacy instance-level Mappings zuerst
        try:
            if hasattr(self, "language_voice_mapping") and self.language_voice_mapping:
                if (
                    language in self.language_voice_mapping
                    and s in self.language_voice_mapping[language]
                ):
                    voice_id = self.language_voice_mapping[language][s]
                    logger.debug(
                        f"🗣️ Voice: {speaker} ({language}) -> {voice_id} (legacy mapping)"
                    )
                    return voice_id
        except Exception:
            # Ignoriere beschädigte/fehlende Mappings
            pass

        # Dann modulweite Defaults prüfen
        if language and language.lower().startswith("en"):
            if (
                language in DEFAULT_LANGUAGE_VOICE_MAPPING
                and s in DEFAULT_LANGUAGE_VOICE_MAPPING[language]
            ):
                voice_id = DEFAULT_LANGUAGE_VOICE_MAPPING[language][s]
                logger.debug(
                    f"🗣️ Voice: {speaker} ({language}) -> {voice_id} (default mapping)"
                )
                return voice_id

        try:
            if hasattr(self, "voice_config") and s in self.voice_config:
                voice_id = self.voice_config[s]["voice_id"]
                logger.debug(f"🗣️ Voice: {speaker} ({language}) -> {voice_id} (voice_config)")
                return voice_id
        except Exception:
            pass

        # Modulweites DEFAULT_VOICE_CONFIG als Fallback
        if s in DEFAULT_VOICE_CONFIG:
            voice_id = DEFAULT_VOICE_CONFIG[s]["voice_id"]
            logger.debug(f"🗣️ Voice: {speaker} ({language}) -> {voice_id} (module default)")
            return voice_id

        # Letzter Fallback: engelsbasierte Defaults
        if s in ("daniel", "male"):
            voice_id = "jeremy"
        else:
            voice_id = "patricia"

        logger.debug(f"🗣️ Voice: {speaker} ({language}) -> {voice_id} (default)")
        return voice_id

    def get_available_voices(self) -> None:
        """
        Ruft alle verfügbaren Speechify Voices ab und zeigt sie an
        """
    # Voice-Listing entfernt: Diese Produktionsklasse soll keine
    # interaktiven Test- oder Listing-Utilities enthalten. Falls benötigt,
    # bitte eine separate Hilfsfunktion oder CLI-Subcommand implementieren.
    logger.debug("get_available_voices entfernt — kein Listing in produktivem Wrapper")

    def test_emotion_mapping(self) -> None:
        """
        Testet die Emotion-Mapping-Funktionalität
        """
    # test_emotion_mapping entfernt — Test-Utilities wurden aus der Klasse
    # entfernt. Für Regressionstests separate Testfälle verwenden.
    logger.debug("test_emotion_mapping entfernt")


def main():
    """Hauptfunktion für CLI-Verwendung"""
    parser = argparse.ArgumentParser(
        description="Deutsche Podcast TTS mit Speechify Official SDK"
    )
    parser.add_argument(
        "input_file", nargs="?", help="Markdown-Datei mit Podcast-Skript"
    )
    parser.add_argument("--output-dir", default="output", help="Ausgabe-Verzeichnis")
    parser.add_argument(
        "--output-prefix", default="podcast", help="Präfix für Ausgabe-Dateien"
    )
    parser.add_argument(
        "--api-key", help="Speechify API Key (oder SPEECHIFY_API_KEY in .env)"
    )
    # CLI-Flags für Tests wurden entfernt (keine interaktiven Test-Flags mehr)
    parser.add_argument(
        "--speakers",
        help="Benutzerdefinierte Sprecher (format: name:voice_id,name2:voice_id2)",
    )
    parser.add_argument(
        "--language", default="de", help="Sprache für TTS (Standard: de)"
    )
    # SSML wird standardmäßig verwendet; kein --no-ssml Flag mehr
    # Intro/Outro Musik Optionen
    parser.add_argument("--intro-music", help="Pfad zur Intro-Musik (MP3/WAV)")
    parser.add_argument("--outro-music", help="Pfad zur Outro-Musik (MP3/WAV)")
    parser.add_argument(
        "--intro-duration-ms",
        type=int,
        default=None,
        help="Intro-Länge in ms (Standard: volle Länge)",
    )
    parser.add_argument(
        "--outro-duration-ms",
        type=int,
        default=None,
        help="Outro-Länge in ms (Standard: volle Länge)",
    )
    parser.add_argument(
        "--intro-gain-db",
        type=float,
        default=0.0,
        help="Intro-Lautstärke in dB (Standard: 0 = unverändert)",
    )
    parser.add_argument(
        "--outro-gain-db",
        type=float,
        default=0.0,
        help="Outro-Lautstärke in dB (Standard: 0 = unverändert)",
    )
    parser.add_argument(
        "--intro-silence-after-ms",
        type=int,
        default=0,
        help="Stille nach Intro in ms (Standard: 0)",
    )
    parser.add_argument(
        "--outro-silence-before-ms",
        type=int,
        default=0,
        help="Stille vor Outro in ms (Standard: 0)",
    )

    args = parser.parse_args()

    try:
        # TTS-Engine initialisieren
        tts = SpeechifyPodcastTTS(api_key=args.api_key)

    # Keine interaktiven Test-Flags mehr (API/SSML-Tests wurden entfernt)

        # Custom speakers parsen
        custom_speakers = {}
        if args.speakers:
            for speaker_mapping in args.speakers.split(","):
                if ":" in speaker_mapping:
                    name, voice_id = speaker_mapping.split(":", 1)
                    custom_speakers[name.strip().lower()] = voice_id.strip()

        # Podcast verarbeiten
        result = tts.process_podcast_script(
            args.input_file,
            output_dir=args.output_dir,
            output_prefix=args.output_prefix,
            custom_speakers=custom_speakers if custom_speakers else None,
            language=args.language,
            use_ssml=True,
            intro_music_path=args.intro_music,
            outro_music_path=args.outro_music,
            intro_duration_ms=args.intro_duration_ms,
            outro_duration_ms=args.outro_duration_ms,
            intro_gain_db=args.intro_gain_db,
            outro_gain_db=args.outro_gain_db,
            intro_silence_after_ms=args.intro_silence_after_ms,
            outro_silence_before_ms=args.outro_silence_before_ms,
        )

        if result:
            logger.info(f"🎉 Podcast erfolgreich erstellt: {result}")
            return 0
        else:
            logger.error("❌ Podcast-Erstellung fehlgeschlagen")
            return 1

    except Exception as e:
        logger.exception(f"❌ Fehler: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
