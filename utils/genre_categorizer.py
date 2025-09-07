#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genre Kategorisierungs-Modul für Markdown-to-Podcast Projekt

Dieses Modul bietet Funktionen zur automatischen Kategorisierung von Musik-Genres
in übergeordnete Hauptkategorien.
"""

from typing import Dict, List, Optional
import re


class GenreCategorizer:
    """Klasse zur Kategorisierung von Musik-Genres"""

    def __init__(self):
        """Initialisiert den Genre-Kategorisierer mit vordefinierten Mappings"""
        self.genre_mappings = {
            # Rock Genres
            'rock': [
                'alternative rock', 'classic rock', 'grunge', 'hard rock',
                'indie rock', 'post-punk', 'psych-rock', 'psychedelic rock',
                'punk', 'rock', 'rock n roll', 'rock and roll', 'rockabilly',
                'surf rock', 'garage rock', 'blues rock', 'folk rock',
                'progressive rock', 'art rock', 'glam rock'
            ],

            # Metal Genres
            'metal': [
                'acoustic metal', 'alternative metal', 'ambient metal', 'avant-garde metal',
                'black metal', 'blackened death metal', 'celtic metal', 'chamber metal',
                'christian metal', 'classic heavy metal', 'cyber metal', 'dark metal',
                'death metal', 'doom metal', 'experimental metal', 'folk metal',
                'funeral doom metal', 'gothic metal', 'groove metal', 'hair metal',
                'heavy metal', 'horror metal', 'industrial metal', 'jazz metal',
                'math metal', 'melodic death metal', 'metalcore', 'neo-classical metal',
                'new wave of british heavy metal', 'nwobhm', 'noise metal', 'nu metal',
                'power metal', 'post metal', 'progressive metal', 'screamo',
                'sludge metal', 'speed metal', 'stoner metal', 'symphonic black metal',
                'symphonic metal', 'technical death metal', 'thrash metal', 'viking metal'
            ],

            # Pop Genres
            'pop': [
                'acoustic pop', 'cantopop', 'indie-pop', 'indie pop', 'j-pop',
                'k-pop', 'mandopop', 'pop', 'poprock', 'pop rock', 'power-pop',
                'power pop', 'synth-pop', 'synthpop', 'electropop', 'dance pop',
                'teen pop', 'bubblegum pop'
            ],

            # Electronic & Dance
            'electronic': [
                'ambient', 'bass music', 'breakbeat', 'chicago house', 'chiptune',
                'club', 'deep house', 'detroit techno', 'drum and bass', 'dnb',
                'dubstep', 'eurodance', 'future bass', 'garage', 'hardstyle',
                'house', 'j-dance', 'minimal techno', 'progressive house',
                'synthwave', 'techno', 'trance', 'vaporwave', 'edm',
                'electronic dance music', 'big beat', 'trip hop', 'trip-hop'
            ],

            # Hip Hop & Urban
            'hip_hop': [
                'german rap', 'deutschrap', 'hip hop', 'hip-hop', 'rap', 'trap',
                'gangsta rap', 'conscious rap', 'old school hip hop', 'boom bap',
                'mumble rap', 'cloud rap'
            ],

            # R&B & Soul
            'rnb_soul': [
                'r&b', 'rnb', 'soul', 'neo soul', 'contemporary r&b', 'motown',
                'northern soul', 'southern soul', 'funk soul'
            ],

            # Jazz
            'jazz': [
                'acid jazz', 'jazz', 'jazz fusion', 'smooth jazz', 'swing',
                'bebop', 'cool jazz', 'free jazz', 'hard bop', 'latin jazz',
                'modal jazz', 'post-bop', 'ragtime', 'big band'
            ],

            # Blues & Country
            'blues_country': [
                'blues', 'bluegrass', 'country', 'delta blues', 'chicago blues',
                'electric blues', 'country blues', 'alt-country', 'country rock',
                'honky tonk', 'western swing', 'outlaw country'
            ],

            # Folk & World
            'folk_world': [
                'african music', 'afrobeat', 'balkan music', 'caribbean music',
                'celtic music', 'celtic', 'folk', 'indie folk', 'indian music',
                'middle eastern music', 'nordic folk', 'krautrock', 'world music',
                'traditional folk', 'contemporary folk', 'americana'
            ],

            # Latin & Caribbean
            'latin_caribbean': [
                'bachata', 'bossa nova', 'cumbia', 'dancehall', 'forró',
                'mambo', 'merengue', 'reggae', 'reggaeton', 'salsa',
                'samba', 'sertanejo', 'tango', 'latin', 'calypso',
                'son cubano', 'bolero', 'rumba'
            ],

            # Classical & Orchestral
            'classical': [
                'chamber music', 'classical', 'neo-classical', 'neoclassical',
                'opera', 'orchestral', 'piano', 'baroque', 'romantic',
                'contemporary classical', 'minimalism', 'string quartet'
            ],

            # Alternative & Experimental
            'alternative_experimental': [
                'ambient', 'avant-garde', 'downtempo', 'experimental', 'industrial',
                'lo-fi', 'lofi', 'new age', 'noise', 'post hardcore', 'post-hardcore',
                'shoegaze', 'drone', 'sound art', 'musique concrète'
            ],

            # Funk & Groove
            'funk': [
                'funk', 'groove', 'p-funk', 'funk rock', 'funk metal',
                'acid funk', 'go-go'
            ],

            # Gospel & Christian
            'gospel_christian': [
                'christian metal', 'gospel', 'contemporary christian',
                'christian rock', 'praise and worship', 'southern gospel',
                'black gospel'
            ],

            # Reggae & Ska
            'reggae_ska': [
                'reggae', 'ska', 'rocksteady', 'dub', 'reggae fusion',
                'two tone', 'third wave ska'
            ],

            # Punk & Hardcore
            'punk_hardcore': [
                'punk', 'hardcore punk', 'post-punk', 'pop punk', 'pop-punk',
                'street punk', 'crust punk', 'anarcho-punk', 'oi!',
                'post hardcore', 'post-hardcore', 'screamo'
            ]
        }

        # Reverse mapping für schnelle Lookup
        self._create_reverse_mapping()

    def _create_reverse_mapping(self):
        """Erstellt ein Reverse-Mapping von Genre zu Kategorie"""
        self.reverse_mapping = {}
        for category, genres in self.genre_mappings.items():
            for genre in genres:
                self.reverse_mapping[genre.lower()] = category

    def categorize_genre(self, genre: str) -> Optional[str]:
        """
        Kategorisiert ein einzelnes Genre

        Args:
            genre: Das zu kategorisierende Genre

        Returns:
            Die Hauptkategorie oder None wenn nicht gefunden
        """
        if not genre:
            return None

        genre_clean = self._clean_genre_name(genre)

        # Direkte Suche
        if genre_clean in self.reverse_mapping:
            return self.reverse_mapping[genre_clean]

        # Fuzzy matching für ähnliche Begriffe
        return self._fuzzy_match(genre_clean)

    def _clean_genre_name(self, genre: str) -> str:
        """Bereinigt Genre-Namen für besseres Matching"""
        genre = genre.lower().strip()
        # Entferne Sonderzeichen
        genre = re.sub(r'[^\w\s-]', '', genre)
        # Normalisiere Whitespace
        genre = re.sub(r'\s+', ' ', genre)
        return genre

    def _fuzzy_match(self, genre: str) -> Optional[str]:
        """Versucht ein Fuzzy-Matching für unbekannte Genres"""
        # Suche nach Teilstrings in bekannten Genres
        for known_genre, category in self.reverse_mapping.items():
            # Check ob das gesuchte Genre ein Substring eines bekannten Genres ist
            if genre in known_genre or known_genre in genre:
                return category

        # Spezielle Regeln für häufige Fälle
        if 'metal' in genre:
            return 'metal'
        elif 'rock' in genre:
            return 'rock'
        elif 'pop' in genre:
            return 'pop'
        elif 'jazz' in genre:
            return 'jazz'
        elif 'electronic' in genre or 'dance' in genre or 'house' in genre:
            return 'electronic'
        elif 'hip' in genre or 'rap' in genre:
            return 'hip_hop'
        elif 'folk' in genre:
            return 'folk_world'
        elif 'classical' in genre or 'orchestra' in genre:
            return 'classical'
        elif 'punk' in genre:
            return 'punk_hardcore'
        elif 'blues' in genre:
            return 'blues_country'
        elif 'country' in genre:
            return 'blues_country'
        elif 'reggae' in genre:
            return 'reggae_ska'
        elif 'funk' in genre:
            return 'funk'

        return None

    def categorize_multiple_genres(self, genres: List[str]) -> Dict[str, str]:
        """
        Kategorisiert mehrere Genres auf einmal

        Args:
            genres: Liste von Genre-Namen

        Returns:
            Dictionary mit Genre -> Kategorie Mappings
        """
        result = {}
        for genre in genres:
            category = self.categorize_genre(genre)
            if category:
                result[genre] = category
        return result

    def get_genres_by_category(self, category: str) -> List[str]:
        """
        Gibt alle Genres einer bestimmten Kategorie zurück

        Args:
            category: Die Kategorie

        Returns:
            Liste der Genres in dieser Kategorie
        """
        return self.genre_mappings.get(category, [])

    def get_all_categories(self) -> List[str]:
        """Gibt alle verfügbaren Kategorien zurück"""
        return list(self.genre_mappings.keys())

    def get_category_stats(self, genres: List[str]) -> Dict[str, int]:
        """
        Erstellt Statistiken über Genre-Kategorien

        Args:
            genres: Liste von Genres

        Returns:
            Dictionary mit Kategorie -> Anzahl
        """
        stats = {}
        for genre in genres:
            category = self.categorize_genre(genre)
            if category:
                stats[category] = stats.get(category, 0) + 1
        return stats


def main():
    """Beispiel-Verwendung des Genre-Kategorisierers"""
    categorizer = GenreCategorizer()

    # Test mit verschiedenen Genres
    test_genres = [
        'Rock', 'Heavy Metal', 'Pop', 'Hip Hop', 'Jazz',
        'Death Metal', 'Alternative Rock', 'Techno', 'Blues',
        'Progressive Metal', 'Indie Pop', 'Drum and Bass'
    ]

    print("Genre-Kategorisierung Test:")
    print("=" * 50)

    for genre in test_genres:
        category = categorizer.categorize_genre(genre)
        print(f"{genre:20} -> {category}")

    print("\nKategorien-Statistiken:")
    print("=" * 50)
    stats = categorizer.get_category_stats(test_genres)
    for category, count in sorted(stats.items()):
        print(f"{category:20}: {count} Genres")


if __name__ == "__main__":
    main()
