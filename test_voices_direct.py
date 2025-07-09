#!/usr/bin/env python3
"""
Direkter Test für Speechify Voices ohne dotenv
"""

import os
import base64

# Speechify SDK importieren
try:
    from speechify import Speechify
    HAS_SPEECHIFY = True
except ImportError:
    print("⚠️ Speechify SDK nicht installiert.")
    HAS_SPEECHIFY = False

def test_voices():
    """Testet verschiedene deutsche Stimmen"""
    
    if not HAS_SPEECHIFY:
        print("❌ Speechify SDK nicht verfügbar")
        return
    
    # API Key direkt aus Umgebungsvariable
    api_key = os.getenv("SPEECHIFY_API_KEY")
    if not api_key:
        print("❌ Speechify API Key erforderlich! Setze SPEECHIFY_API_KEY in .env Datei.")
        return
    
    # Speechify Client initialisieren
    try:
        client = Speechify(token=api_key)
        print("✅ Speechify Client initialisiert")
    except Exception as e:
        print(f"❌ Speechify Client-Initialisierung fehlgeschlagen: {str(e)}")
        return
    
    # Test-Text
    test_text = "Hallo, ich bin eine deutsche Stimme. Ich spreche Hochdeutsch mit Umlauten: Ä, Ö, Ü und dem Eszett ß."
    
    # Verschiedene deutsche Voice IDs testen
    german_voices = [
        "stefan",
        "ronja", 
        "jannik",
        "anna",
        "daniel",
        "maria",
        "hans",
        "lisa",
        "klaus",
        "petra"
    ]
    
    print(f"🎤 Teste {len(german_voices)} deutsche Stimmen...")
    print(f"📝 Test-Text: {test_text}")
    print()
    
    for voice_id in german_voices:
        try:
            print(f"🗣️ Teste Voice: {voice_id}")
            
            # Test 1: Mit de-DE
            print("  📍 Test 1: Mit language='de-DE'")
            response1 = client.tts.audio.speech(
                input=test_text,
                voice_id=voice_id,
                language="de-DE",
                audio_format="mp3",
                options={
                    "loudness_normalization": True,
                    "text_normalization": True,
                    "model": "simba-multilingual"
                }
            )
            
            if response1:
                os.makedirs("temp", exist_ok=True)
                test_file1 = f"temp/voice_test_{voice_id}_de-DE.mp3"
                
                if hasattr(response1, 'audio_data'):
                    audio_data = base64.b64decode(response1.audio_data)
                    with open(test_file1, 'wb') as f:
                        f.write(audio_data)
                    print(f"  ✅ Audio gespeichert: {test_file1}")
                else:
                    print(f"  ⚠️ Audio-Format unbekannt")
            else:
                print(f"  ❌ Keine Response")
            
            # Test 2: Ohne language-Parameter (automatische Erkennung)
            print("  📍 Test 2: Ohne language-Parameter (automatische Erkennung)")
            response2 = client.tts.audio.speech(
                input=test_text,
                voice_id=voice_id,
                audio_format="mp3",
                options={
                    "loudness_normalization": True,
                    "text_normalization": True,
                    "model": "simba-multilingual"
                }
            )
            
            if response2:
                test_file2 = f"temp/voice_test_{voice_id}_auto.mp3"
                
                if hasattr(response2, 'audio_data'):
                    audio_data = base64.b64decode(response2.audio_data)
                    with open(test_file2, 'wb') as f:
                        f.write(audio_data)
                    print(f"  ✅ Audio gespeichert: {test_file2}")
                else:
                    print(f"  ⚠️ Audio-Format unbekannt")
            else:
                print(f"  ❌ Keine Response")
                
        except Exception as e:
            print(f"❌ {voice_id} nicht verfügbar: {str(e)}")
        
        print()
    
    print("🎧 Höre dir die Test-Dateien in temp/ an!")
    print("💡 Vergleiche die Dateien mit '_de-DE' und '_auto' Endungen.")
    print("🔍 Welche Version klingt besser?")

if __name__ == "__main__":
    test_voices() 