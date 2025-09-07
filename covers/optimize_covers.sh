#!/bin/bash

# Web-Optimierung Script für Cover-Bilder
# Dieses Script optimiert PNG-Bilder für die Web-Nutzung

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Konfiguration
ORIGINAL_DIR="."
OPTIMIZED_DIR="optimized"
MAX_WIDTH=800
MAX_HEIGHT=800
QUALITY=85
WEBP_QUALITY=80

# Prüfe ob notwendige Tools installiert sind
check_dependencies() {
    echo -e "${BLUE}Prüfe verfügbare Tools...${NC}"
    
    TOOLS_AVAILABLE=()
    TOOLS_MISSING=()
    
    # ImageMagick
    if command -v magick &> /dev/null || command -v convert &> /dev/null; then
        TOOLS_AVAILABLE+=("ImageMagick")
        HAS_IMAGEMAGICK=true
    else
        TOOLS_MISSING+=("ImageMagick")
        HAS_IMAGEMAGICK=false
    fi
    
    # optipng
    if command -v optipng &> /dev/null; then
        TOOLS_AVAILABLE+=("optipng")
        HAS_OPTIPNG=true
    else
        TOOLS_MISSING+=("optipng")
        HAS_OPTIPNG=false
    fi
    
    # pngquant
    if command -v pngquant &> /dev/null; then
        TOOLS_AVAILABLE+=("pngquant")
        HAS_PNGQUANT=true
    else
        TOOLS_MISSING+=("pngquant")
        HAS_PNGQUANT=false
    fi
    
    # cwebp (für WebP)
    if command -v cwebp &> /dev/null; then
        TOOLS_AVAILABLE+=("cwebp")
        HAS_CWEBP=true
    else
        TOOLS_MISSING+=("cwebp")
        HAS_CWEBP=false
    fi
    
    if [ ${#TOOLS_AVAILABLE[@]} -gt 0 ]; then
        echo -e "${GREEN}Verfügbare Tools: ${TOOLS_AVAILABLE[*]}${NC}"
    fi
    
    if [ ${#TOOLS_MISSING[@]} -gt 0 ]; then
        echo -e "${YELLOW}Fehlende Tools: ${TOOLS_MISSING[*]}${NC}"
        echo -e "${YELLOW}Installation mit: sudo pacman -S imagemagick optipng pngquant libwebp${NC}"
    fi
    
    if [ "$HAS_IMAGEMAGICK" = false ]; then
        echo -e "${RED}Fehler: ImageMagick ist erforderlich!${NC}"
        exit 1
    fi
}

# Erstelle Ausgabe-Verzeichnis
create_output_dir() {
    if [ ! -d "$OPTIMIZED_DIR" ]; then
        mkdir -p "$OPTIMIZED_DIR"
        echo -e "${GREEN}Verzeichnis '$OPTIMIZED_DIR' erstellt${NC}"
    fi
}

# Dateigröße in lesbarem Format
human_filesize() {
    local bytes=$1
    if [ $bytes -lt 1024 ]; then
        echo "${bytes}B"
    elif [ $bytes -lt 1048576 ]; then
        echo "$((bytes/1024))KB"
    else
        echo "$((bytes/1048576))MB"
    fi
}

# Optimiere ein einzelnes Bild
optimize_image() {
    local input_file="$1"
    local filename=$(basename "$input_file" .png)
    local output_file="$OPTIMIZED_DIR/${filename}.png"
    local webp_file="$OPTIMIZED_DIR/${filename}.webp"
    
    local original_size=$(stat -f%z "$input_file" 2>/dev/null || stat -c%s "$input_file")
    
    echo -e "${BLUE}Bearbeite: $input_file${NC}"
    echo "  Original: $(human_filesize $original_size)"
    
    # Schritt 1: Größe anpassen und als PNG optimieren
    if command -v magick &> /dev/null; then
        magick "$input_file" -resize "${MAX_WIDTH}x${MAX_HEIGHT}>" -strip "$output_file"
    else
        convert "$input_file" -resize "${MAX_WIDTH}x${MAX_HEIGHT}>" -strip "$output_file"
    fi
    
    # Schritt 2: PNG mit pngquant optimieren (wenn verfügbar)
    if [ "$HAS_PNGQUANT" = true ]; then
        pngquant --quality=65-80 --ext .png --force "$output_file"
    fi
    
    # Schritt 3: PNG mit optipng optimieren (wenn verfügbar)
    if [ "$HAS_OPTIPNG" = true ]; then
        optipng -o2 -quiet "$output_file"
    fi
    
    # Schritt 4: WebP Version erstellen (wenn verfügbar)
    if [ "$HAS_CWEBP" = true ]; then
        cwebp -q $WEBP_QUALITY "$output_file" -o "$webp_file" >/dev/null 2>&1
        local webp_size=$(stat -f%z "$webp_file" 2>/dev/null || stat -c%s "$webp_file")
        echo "  WebP: $(human_filesize $webp_size)"
    fi
    
    local optimized_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file")
    local savings=$((100 - (optimized_size * 100 / original_size)))
    
    echo "  PNG: $(human_filesize $optimized_size) (${savings}% kleiner)"
    echo
}

# Hauptfunktion
main() {
    echo -e "${GREEN}=== Cover-Bilder Web-Optimierung ===${NC}"
    echo
    
    check_dependencies
    create_output_dir
    
    echo -e "${BLUE}Starte Optimierung...${NC}"
    echo "Maximale Größe: ${MAX_WIDTH}x${MAX_HEIGHT}"
    echo "PNG Qualität: Automatisch optimiert"
    echo "WebP Qualität: ${WEBP_QUALITY}%"
    echo
    
    # Zähle PNG-Dateien
    png_count=$(find "$ORIGINAL_DIR" -maxdepth 1 -name "*.png" -type f | wc -l)
    
    if [ $png_count -eq 0 ]; then
        echo -e "${YELLOW}Keine PNG-Dateien gefunden!${NC}"
        exit 1
    fi
    
    echo "Gefunden: $png_count PNG-Dateien"
    echo
    
    # Verarbeite alle PNG-Dateien
    for png_file in *.png; do
        if [ -f "$png_file" ]; then
            optimize_image "$png_file"
        fi
    done
    
    echo -e "${GREEN}=== Optimierung abgeschlossen! ===${NC}"
    echo
    echo -e "${BLUE}Ergebnisse im Verzeichnis: $OPTIMIZED_DIR${NC}"
    echo "- PNG-Dateien: Optimiert für beste Kompatibilität"
    echo "- WebP-Dateien: Moderne Browser, kleinste Dateigröße"
    echo
    echo -e "${YELLOW}Tipp: Verwende WebP für moderne Browser und PNG als Fallback${NC}"
}

# Script ausführen
main "$@"
