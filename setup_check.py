#!/usr/bin/env python3
"""
Projekt-Status und Setup-Verifizierung
======================================

Überprüft die Integrität des bereinigten TTS-Projekts.
"""

import os
import sys

def check_project_structure():
    """Überprüft die Projektstruktur"""
    
    print("🔍 PROJEKT-STRUKTUR ÜBERPRÜFUNG")
    print("=" * 50)
    
    required_files = [
        "speechify_official.py",
        "requirements.txt", 
        "README.md",
        "LICENSE",
        ".env.example",
        "examples/demo.md"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing_files.append(file_path)
    
    print("\n📁 VERZEICHNISSE:")
    directories = ["examples", "output"]
    
    for directory in directories:
        if os.path.exists(directory):
            files = os.listdir(directory)
            print(f"✅ {directory}/ ({len(files)} Dateien)")
        else:
            print(f"❌ {directory}/")
            missing_files.append(f"{directory}/")
    
    print("\n" + "=" * 50)
    
    if missing_files:
        print(f"⚠️ {len(missing_files)} Dateien/Verzeichnisse fehlen:")
        for item in missing_files:
            print(f"   - {item}")
        return False
    else:
        print("🎉 Projekt-Struktur vollständig!")
        return True

def check_dependencies():
    """Überprüft installierte Dependencies"""
    
    print("\n🔧 DEPENDENCY-CHECK")
    print("=" * 50)
    
    dependencies = [
        ("speechify", "Speechify SDK"),
        ("pydub", "Audio Processing"),
        ("dotenv", "Environment Variables"),
        ("numpy", "Scientific Computing")
    ]
    
    missing_deps = []
    
    for module, description in dependencies:
        try:
            __import__(module)
            print(f"✅ {module} - {description}")
        except ImportError:
            print(f"❌ {module} - {description}")
            missing_deps.append(module)
    
    if missing_deps:
        print(f"\n⚠️ Fehlende Dependencies: {', '.join(missing_deps)}")
        print("💡 Installiere mit: pip install -r requirements.txt")
        return False
    else:
        print("\n🎉 Alle Dependencies installiert!")
        return True

def show_quick_start():
    """Zeigt Quick-Start-Anleitung"""
    
    print("\n🚀 QUICK START")
    print("=" * 50)
    print("1. Python-Umgebung erstellen:")
    print("   python -m venv tts-env")
    print("   source tts-env/bin/activate  # Linux/Mac")
    print("   # oder: tts-env\\Scripts\\activate  # Windows")
    print()
    print("2. Dependencies installieren:")
    print("   pip install -r requirements.txt")
    print()
    print("3. API-Key konfigurieren:")
    print("   cp .env.example .env")
    print("   # .env bearbeiten und SPEECHIFY_API_KEY setzen")
    print()
    print("4. Demo-Podcast generieren:")
    print("   python speechify_official.py examples/demo.md")
    print()
    print("5. Weitere Sprachen testen:")
    print("   python speechify_official.py examples/demo.md --language en")
    print("   python speechify_official.py examples/demo.md --language fr")

def main():
    """Hauptfunktion"""
    
    print("🎙️ MULTILINGUAL PODCAST TTS - PROJEKT-STATUS")
    print("=" * 60)
    
    structure_ok = check_project_structure()
    deps_ok = check_dependencies()
    
    show_quick_start()
    
    print("\n" + "=" * 60)
    
    if structure_ok and deps_ok:
        print("🎉 PROJEKT BEREIT FÜR DEN EINSATZ!")
        print("🎯 Nächster Schritt: API-Key in .env setzen")
    else:
        print("⚠️ PROJEKT SETUP UNVOLLSTÄNDIG")
        print("🔧 Folge den obigen Anweisungen zur Behebung")

if __name__ == "__main__":
    main()
