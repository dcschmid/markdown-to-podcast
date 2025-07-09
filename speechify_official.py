#!/usr/bin/env python3
"""
Deutsche Podcast TTS mit Speechify Official SDK
==============================================

Hochqualitative Text-zu-Sprache Konvertierung für deutsche Podcasts
mit dem offiziellen Speechify Python SDK.

Autor: Daniel
Datum: Juli 2025
"""

import os
import sys
import time
import json
import base64
import argparse
import tempfile
from typing import List, Tuple, Dict, Optional
from pydub import AudioSegment
from dotenv import load_dotenv

# Speechify SDK importieren
try:
    from speechify import Speechify
    HAS_SPEECHIFY = True
except ImportError:
    print("⚠️ Speechify SDK nicht installiert. Installiere mit: pip install git+https://github.com/SpeechifyInc/speechify-api-sdk-python.git")
    HAS_SPEECHIFY = False


class SpeechifyPodcastTTS:
    """
    Speechify-basierte TTS-Engine für deutsche Podcasts mit Official SDK
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialisiert Speechify TTS mit Official SDK
        
        Args:
            api_key: Speechify API Key (oder über .env Datei/SPEECHIFY_API_KEY)
        """
        print("🎤 Initialisiere Speechify TTS mit Official SDK...")
        
        # .env Datei laden
        load_dotenv()
        
        if not HAS_SPEECHIFY:
            raise ImportError("Speechify SDK nicht verfügbar")
        
        # API Key laden
        self.api_key = api_key or os.getenv("SPEECHIFY_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Speechify API Key erforderlich! Setze SPEECHIFY_API_KEY in .env Datei oder übergebe api_key Parameter.")
        
        # Speechify Client initialisieren
        try:
            self.client = Speechify(token=self.api_key)
            print("✅ Speechify Client initialisiert")
        except Exception as e:
            raise RuntimeError(f"❌ Speechify Client-Initialisierung fehlgeschlagen: {str(e)}")
        
        # Multilinguale Stimmen-Konfiguration für Speechify mit allen unterstützten Sprachen
        self.voice_config = {
            # Deutsche Sprecher (Daniel/Anna/Annabelle)
            "daniel": {
                "voice_id": "jannik",  # Männliche deutsche Stimme
                "language": "de",
                "gender": "male"
            },
            "anna": {
                "voice_id": "ronja",  # Weibliche deutsche Stimme
                "language": "de", 
                "gender": "female"
            },
            "annabelle": {
                "voice_id": "ronja",  # Weibliche deutsche Stimme (gleich wie Anna)
                "language": "de", 
                "gender": "female"
            },
            
            # Legacy-Support für generische Sprecher
            "male": {
                "voice_id": "jannik",
                "language": "de",
                "gender": "male"
            },
            "female": {
                "voice_id": "ronja",
                "language": "de",
                "gender": "female"
            }
        }
        
        # Sprachabhängige Stimm-Zuordnung für Daniel/Anna/Annabelle
        self.language_voice_mapping = {
            "de": {  # Deutsch
                "daniel": "jannik",
                "anna": "ronja", 
                "annabelle": "ronja"
            },
            "en": {  # Englisch  
                "daniel": "frederick",
                "anna": "andra",
                "annabelle": "andra"
            },
            "zh": {  # Chinesisch
                "daniel": "chun-wah",  # Männlich
                "anna": "yan-ting",  # Weiblich
                "annabelle": "yan-ting"  # Weiblich
            },
            "da": {  # Dänisch
                "daniel": "frederik",  # Männlich
                "anna": "freja",  # Weiblich
                "annabelle": "freja"  # Weiblich
            },
            "nl": {  # Niederländisch
                "daniel": "daan",  # Männlich
                "anna": "lotte",  # Weiblich
                "annabelle": "lotte"  # Weiblich
            },
            "fi": {  # Finnisch
                "daniel": "eino",  # Männlich
                "anna": "helmi",  # Weiblich
                "annabelle": "helmi"  # Weiblich
            },
            "fr": {  # Französisch
                "daniel": "raphael",  # Männlich
                "anna": "elise",  # Weiblich
                "annabelle": "elise"  # Weiblich
            },
            "it": {  # Italienisch
                "daniel": "lazzaro",  # Männlich
                "anna": "alessia",  # Weiblich
                "annabelle": "alessia"  # Weiblich
            },
            "ja": {  # Japanisch
                "daniel": "tsubasa",  # Männlich
                "anna": "sakura",  # Weiblich
                "annabelle": "sakura"  # Weiblich
            },
            "pt": {  # Portugiesisch
                "daniel": "lucas",  # Männlich
                "anna": "luiza",  # Weiblich
                "annabelle": "luiza"  # Weiblich
            },
            "ru": {  # Russisch
                "daniel": "mikhail",  # Männlich
                "anna": "olga",  # Weiblich
                "annabelle": "olga"  # Weiblich
            },
            "es": {  # Spanisch
                "daniel": "alejandro",  # Männlich
                "anna": "carmen",  # Weiblich
                "annabelle": "carmen"  # Weiblich
            },
            "sv": {  # Schwedisch
                "daniel": "axel",  # Männlich
                "anna": "ebba",  # Weiblich
                "annabelle": "ebba"  # Weiblich
            },
            "uk": {  # Ukrainisch
                "daniel": "taras",  # Männlich
                "anna": "lesya",  # Weiblich
                "annabelle": "lesya"  # Weiblich
            }
        }
        
        # Timing-Daten für Transkripte
        self.timing_data = []
        self.current_time = 0.0
        
        print("✅ Speechify TTS bereit für deutsche Podcasts")
    
    def test_api_connection(self) -> bool:
        """
        Testet die Verbindung zur Speechify API mit dem Official SDK
        
        Returns:
            bool: True wenn erfolgreich
        """
        try:
            print("🔍 Teste Speechify API-Verbindung...")
            
            # Test mit kurzer deutscher Nachricht
            test_text = "Hallo, das ist ein Test der deutschen Sprachsynthese."
            
            # Speechify TTS-Request mit bekannter Voice ID
            response = self.client.tts.audio.speech(
                input=test_text,
                voice_id="jannik",  # Deutsche männliche Stimme zum Testen
                language="de",  # Deutsch
                audio_format="mp3",  # MP3 Format für bessere Kompatibilität
                model="simba-multilingual",
                options={
                    "loudness_normalization": True,  # Audio-Lautstärke normalisieren
                    "text_normalization": True,  # Text normalisieren
                }
            )
            
            if response:
                print("✅ Speechify API-Verbindung erfolgreich")
                return True
            else:
                print("❌ API-Test fehlgeschlagen: Keine Response")
                return False
                
        except Exception as e:
            print(f"❌ API-Verbindung fehlgeschlagen: {str(e)}")
            return False
    
    def extract_speakers_from_markdown(self, markdown_text: str) -> List[Tuple[str, str]]:
        """
        Extrahiert Sprecher und ihre Texte aus Markdown
        
        Args:
            markdown_text: Der Markdown-Text
            
        Returns:
            Liste von (sprecher, text) Tupeln
        """
        segments = []
        lines = markdown_text.strip().split('\n')
        current_speaker = None
        current_text = []
        
        for line in lines:
            line = line.strip()
            
            # Leere Zeilen überspringen
            if not line:
                if current_speaker and current_text:
                    # Segment abschließen bei Leerzeile
                    full_text = ' '.join(current_text).strip()
                    if full_text:
                        segments.append((current_speaker, full_text))
                    current_text = []
                continue
            
            # Sprecher-Zeile erkennen (Name gefolgt von Doppelpunkt)
            if ':' in line and not line.startswith('[') and not line.startswith('♪'):
                # Vorheriges Segment abschließen
                if current_speaker and current_text:
                    full_text = ' '.join(current_text).strip()
                    if full_text:
                        segments.append((current_speaker, full_text))
                
                # Neuer Sprecher
                parts = line.split(':', 1)
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
            full_text = ' '.join(current_text).strip()
            if full_text:
                segments.append((current_speaker, full_text))
        
        print(f"📝 {len(segments)} Sprecher-Segmente erkannt:")
        for i, (speaker, text) in enumerate(segments, 1):
            ellipsis = "..." if len(text) > 50 else ""
            print(f"   {i}. {speaker}: {text[:50]}{ellipsis}")
        
        return segments
    
    def clean_text_for_tts(self, text: str) -> str:
        """
        Bereinigt Text für bessere TTS-Qualität
        
        Args:
            text: Der ursprüngliche Text
            
        Returns:
            Bereinigter Text
        """
        # Emotionale Anmerkungen entfernen
        import re
        
        # [laughter], [sighs], etc. entfernen
        text = re.sub(r'\[.*?\]', '', text)
        
        # Musik-Notationen entfernen
        text = re.sub(r'♪.*?♪', '', text)
        
        # Mehrfache Leerzeichen entfernen
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def text_to_speech(self, text: str, voice_id: str, output_path: str, language: str = "de") -> Optional[str]:
        """
        Konvertiert Text zu Sprache mit Speechify Official SDK
        
        Args:
            text: Der zu konvertierende Text
            voice_id: Die Speechify Voice ID (wird überschrieben mit simba-multilingual)
            output_path: Pfad für die Ausgabe-Datei
            language: Sprache für TTS (Standard: "de")
            
        Returns:
            Pfad zur erstellten Audio-Datei oder None bei Fehler
        """
        try:
            # Text bereinigen
            clean_text = self.clean_text_for_tts(text)
            
            if not clean_text:
                print("⚠️ Kein Text nach Bereinigung übrig")
                return None
            
            print(f"🎤 Generiere Audio mit {voice_id} ({language}): {clean_text[:50]}{'...' if len(clean_text) > 50 else ''}")
            
            # Speechify TTS Request mit korrekter Voice ID
            audio_response = self.client.tts.audio.speech(
                input=clean_text,
                voice_id=voice_id,  # Verwende die tatsächliche Voice ID
                language=language,  # Dynamische Sprache verwenden
                audio_format="mp3",  # MP3 Format für bessere Kompatibilität
                model="simba-multilingual",  # Multilinguales Modell für bessere Sprachqualität
                options={
                    "loudness_normalization": False,  # Audio-Lautstärke normalisieren (-14 LUFS, -2 dBTP, 7 LU)
                    "text_normalization": True,  # Text normalisieren (Zahlen zu Worten, etc.)
                }
            )
            
            if audio_response:
                # Audio-Daten speichern
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Speechify Response ist ein Objekt mit audio_data (Base64)
                
                if hasattr(audio_response, 'audio_data'):
                    # Base64-decodierte Audio-Daten
                    audio_data = base64.b64decode(audio_response.audio_data)
                elif hasattr(audio_response, 'content'):
                    audio_data = audio_response.content
                elif isinstance(audio_response, bytes):
                    audio_data = audio_response
                else:
                    # Debug: Response-Typ anzeigen
                    print(f"🔍 Response-Typ: {type(audio_response)}")
                    if hasattr(audio_response, '__dict__'):
                        print(f"🔍 Response-Attribute: {list(audio_response.__dict__.keys())}")
                    # Fallback: als bytes behandeln
                    audio_data = bytes(audio_response)
                
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                
                print(f"✅ Audio gespeichert: {output_path}")
                return output_path
            else:
                print("❌ TTS-Fehler: Keine Audio-Response")
                return None
                
        except Exception as e:
            print(f"❌ TTS-Fehler: {str(e)}")
            return None
    
    def process_podcast_script(self, markdown_file: str, output_dir: str = "output", 
                             output_prefix: str = "podcast", custom_speakers: Dict[str, str] = None,
                             language: str = "de") -> Optional[str]:
        """
        Verarbeitet ein komplettes Podcast-Skript mit Speechify Official SDK
        
        Args:
            markdown_file: Pfad zur Markdown-Datei
            output_dir: Ausgabe-Verzeichnis
            output_prefix: Präfix für Ausgabe-Dateien
            custom_speakers: Benutzerdefinierte Sprecher-Voice-Zuordnung
            language: Sprache für TTS (Standard: "de")
            
        Returns:
            Pfad zur finalen Audio-Datei oder None bei Fehler
        """
        try:
            # Markdown-Datei laden
            with open(markdown_file, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            print(f"📖 Verarbeite Podcast-Skript: {markdown_file}")
            
            # Sprecher-Segmente extrahieren
            segments = self.extract_speakers_from_markdown(markdown_content)
            
            if not segments:
                print("❌ Keine Sprecher-Segmente gefunden")
                return None
            
            # Ausgabe-Verzeichnis erstellen
            os.makedirs(output_dir, exist_ok=True)
            timestamp = int(time.time())
            
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
                
                print(f"🗣️ Segment {i}/{len(segments)}: {speaker} -> {voice_id}")
                
                # Audio-Datei generieren
                segment_file = f"{output_dir}/{output_prefix}_segment_{i:03d}_{speaker}.mp3"
                
                start_time = self.current_time
                result = self.text_to_speech(text, voice_id, segment_file, language=language)
                
                if result:
                    audio_files.append(segment_file)
                    
                    # Timing-Daten berechnen
                    audio_segment = AudioSegment.from_file(segment_file)
                    duration = len(audio_segment) / 1000.0  # in Sekunden
                    
                    self.timing_data.append({
                        "speaker": speaker,
                        "text": text,
                        "start_time": start_time,
                        "end_time": start_time + duration,
                        "duration": duration
                    })
                    
                    self.current_time += duration + 0.5  # 500ms Pause zwischen Segmenten
                    print(f"✅ Segment {i} erstellt ({duration:.1f}s)")
                else:
                    print(f"⚠️ Segment {i} konnte nicht generiert werden")
            
            if not audio_files:
                print("❌ Keine Audio-Segmente erstellt")
                return None
            
            # Audio-Segmente kombinieren
            print(f"🔗 Kombiniere {len(audio_files)} Audio-Segmente...")
            final_audio = AudioSegment.empty()
            
            for audio_file in audio_files:
                segment = AudioSegment.from_file(audio_file)
                
                # Pause hinzufügen (außer beim ersten Segment)
                if len(final_audio) > 0:
                    final_audio += AudioSegment.silent(duration=500)  # 500ms Pause
                
                final_audio += segment
                
                # Temporäre Datei löschen
                os.remove(audio_file)
            
            # Finale Audio-Datei speichern
            final_output = f"{output_dir}/{output_prefix}_speechify_{timestamp}.mp3"
            final_audio.export(final_output, format="mp3", bitrate="192k")
            
            print(f"✅ Podcast erfolgreich erstellt: {final_output}")
            print(f"⏱️ Gesamtdauer: {len(final_audio) / 1000.0:.1f} Sekunden")
            
            # JSON-Transkript generieren
            self.generate_json_transcript(f"{output_dir}/{output_prefix}_transcript_{timestamp}.json")
            
            # WebVTT-Untertitel generieren
            self.generate_webvtt_subtitles(f"{output_dir}/{output_prefix}_subtitles_{timestamp}.vtt")
            
            return final_output
            
        except Exception as e:
            print(f"❌ Fehler bei der Podcast-Verarbeitung: {str(e)}")
            return None
    
    def generate_json_transcript(self, output_path: str):
        """Generiert JSON-Transkript mit Timing-Informationen"""
        try:
            transcript_data = {
                "podcast_transcript": {
                    "total_duration": self.current_time,
                    "segments": self.timing_data,
                    "generated_with": "Speechify Official SDK",
                    "timestamp": time.time()
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)
            
            print(f"📝 JSON-Transkript erstellt: {output_path}")
        except Exception as e:
            print(f"❌ JSON-Transkript Fehler: {str(e)}")
    
    def generate_webvtt_subtitles(self, output_path: str):
        """Generiert WebVTT-Untertitel für Web-Player"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
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
            
            print(f"📺 WebVTT-Untertitel erstellt: {output_path}")
        except Exception as e:
            print(f"❌ WebVTT-Fehler: {str(e)}")
    
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
        print("🎤 Teste deutsche Voices mit Voice-Mapping...")
        
        # Deutsche Sprecher testen
        test_speakers = {
            "daniel": "Hallo Daniel hier, ich teste die deutsche männliche Aussprache mit Umlauten: Ä, Ö, Ü und dem Eszett ß.",
            "anna": "Hallo Anna hier, ich teste die deutsche weibliche Aussprache mit verschiedenen Wörtern.",
            "annabelle": "Hallo Annabelle hier, ich teste ebenfalls die deutsche weibliche Sprachsynthese."
        }
        
        for speaker, test_text in test_speakers.items():
            try:
                print(f"\n🗣️ Teste {speaker}...")
                
                # Voice ID aus Mapping bestimmen
                voice_id = self.get_voice_for_language(speaker, "de")
                
                # Test-Audio generieren
                audio_response = self.client.tts.audio.speech(
                    input=test_text,
                    voice_id=voice_id,
                    language="de",
                    audio_format="mp3",
                    model="simba-multilingual",
                    options={
                        "loudness_normalization": True,
                        "text_normalization": True,
                    }
                )
                
                if audio_response:
                    # Test-Datei speichern
                    test_file = f"temp/voice_test_{speaker}_{voice_id}.mp3"
                    os.makedirs(os.path.dirname(test_file), exist_ok=True)
                    
                    if hasattr(audio_response, 'audio_data'):
                        audio_data = base64.b64decode(audio_response.audio_data)
                        with open(test_file, 'wb') as f:
                            f.write(audio_data)
                        print(f"✅ Test-Audio gespeichert: {test_file}")
                    else:
                        print(f"⚠️ Audio-Format unbekannt für {speaker}")
                else:
                    print(f"❌ Fehler bei {speaker}")
                    
            except Exception as e:
                print(f"❌ {speaker} nicht verfügbar: {str(e)}")
        
        print("\n🎧 Höre dir die Test-Dateien in temp/ an und prüfe die Qualität der verschiedenen Sprecher!")
        print("✨ Features aktiviert: Simba-Multilingual Modell + Loudness Normalization + Text Normalization")
    
    def get_voice_for_language(self, speaker: str, language: str = "de") -> str:
        """
        Bestimmt die Voice ID für einen Sprecher basierend auf Sprache und Mapping
        
        Args:
            speaker: Name des Sprechers (daniel, anna, annabelle, etc.)
            language: Sprach-Code (de, en, fr, etc.)
            
        Returns:
            Voice ID für Speechify TTS
        """
        # Erst im language_voice_mapping nachschauen
        if language in self.language_voice_mapping:
            if speaker in self.language_voice_mapping[language]:
                voice_id = self.language_voice_mapping[language][speaker]
                print(f"🗣️ Voice: {speaker} ({language}) -> {voice_id}")
                return voice_id
        
        # Fallback zu voice_config
        if speaker in self.voice_config:
            voice_id = self.voice_config[speaker]["voice_id"]
            print(f"🗣️ Voice: {speaker} ({language}) -> {voice_id} (fallback)")
            return voice_id
        
        # Letzter Fallback basierend auf Geschlecht
        if speaker.lower() in ['daniel', 'male']:
            voice_id = "jannik"  # Männliche deutsche Stimme
        else:
            voice_id = "ronja"  # Weibliche deutsche Stimme
        
        print(f"🗣️ Voice: {speaker} ({language}) -> {voice_id} (default)")
        return voice_id
    
    def get_available_voices(self) -> None:
        """
        Ruft alle verfügbaren Speechify Voices ab und zeigt sie an
        """
        try:
            print("🎤 Lade verfügbare Speechify Voices...")
            
            # Speechify Voices abrufen
            voices_response = self.client.voices.get()
            
            if voices_response and hasattr(voices_response, 'voices'):
                print(f"✅ {len(voices_response.voices)} Voices gefunden:")
                
                # Nach Sprachen gruppieren
                languages = {}
                for voice in voices_response.voices:
                    lang = getattr(voice, 'language', 'unknown')
                    if lang not in languages:
                        languages[lang] = []
                    languages[lang].append(voice)
                
                # Voices anzeigen
                for lang, voice_list in languages.items():
                    print(f"\n🌍 {lang.upper()}:")
                    for voice in voice_list:
                        voice_id = getattr(voice, 'voice_id', 'unknown')
                        name = getattr(voice, 'name', voice_id)
                        gender = getattr(voice, 'gender', 'unknown')
                        print(f"   - {voice_id}: {name} ({gender})")
            else:
                print("❌ Keine Voices gefunden oder unbekanntes Response-Format")
                
        except Exception as e:
            print(f"❌ Fehler beim Laden der Voices: {str(e)}")


def main():
    """Hauptfunktion für CLI-Verwendung"""
    parser = argparse.ArgumentParser(description="Deutsche Podcast TTS mit Speechify Official SDK")
    parser.add_argument("input_file", nargs='?', help="Markdown-Datei mit Podcast-Skript")
    parser.add_argument("--output-dir", default="output", help="Ausgabe-Verzeichnis")
    parser.add_argument("--output-prefix", default="podcast", help="Präfix für Ausgabe-Dateien")
    parser.add_argument("--api-key", help="Speechify API Key (oder SPEECHIFY_API_KEY in .env)")
    parser.add_argument("--test-api", action="store_true", help="Nur API-Verbindung testen")
    parser.add_argument("--test-voices", action="store_true", help="Deutsche Stimmen testen")
    parser.add_argument("--list-voices", action="store_true", help="Alle verfügbaren Voices anzeigen")
    parser.add_argument("--speakers", help="Benutzerdefinierte Sprecher (format: name:voice_id,name2:voice_id2)")
    parser.add_argument("--language", default="de", help="Sprache für TTS (Standard: de)")
    
    args = parser.parse_args()
    
    try:
        # TTS-Engine initialisieren
        tts = SpeechifyPodcastTTS(api_key=args.api_key)
        
        # API-Test falls gewünscht
        if args.test_api:
            if tts.test_api_connection():
                print("✅ API-Test erfolgreich!")
                return 0
            else:
                print("❌ API-Test fehlgeschlagen!")
                return 1
        
        # Voice-Test falls gewünscht
        if args.test_voices:
            tts.test_german_voices()
            return 0
        
        # Voices auflisten falls gewünscht
        if args.list_voices:
            tts.get_available_voices()
            return 0
        
        # Custom speakers parsen
        custom_speakers = {}
        if args.speakers:
            for speaker_mapping in args.speakers.split(','):
                if ':' in speaker_mapping:
                    name, voice_id = speaker_mapping.split(':', 1)
                    custom_speakers[name.strip().lower()] = voice_id.strip()
        
        # Podcast verarbeiten
        result = tts.process_podcast_script(
            args.input_file,
            output_dir=args.output_dir,
            output_prefix=args.output_prefix,
            custom_speakers=custom_speakers if custom_speakers else None,
            language=args.language
        )
        
        if result:
            print(f"🎉 Podcast erfolgreich erstellt: {result}")
            return 0
        else:
            print("❌ Podcast-Erstellung fehlgeschlagen")
            return 1
            
    except Exception as e:
        print(f"❌ Fehler: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
