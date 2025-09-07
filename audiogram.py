#!/usr/bin/env python3
"""Audiogram-Generator: Erzeugt ein kurzes Video mit Cover, Text und Fortschrittsbalken.

Dieses Modul erzeugt ein statisches Background-Template (mit weichgezeichnetem
Hintergrund), zeichnet Titel/Untertitel und rendert anschließend pro Frame das
Cover (nun als "contain"), sowie einen Fortschrittsbalken. Die API bleibt CLI-
basierend über `main()`.
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import subprocess
from typing import Optional, Tuple, Dict, TypedDict

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import librosa
from moviepy import VideoFileClip, AudioFileClip, VideoClip

from utils.image_utils import compute_contain_size

logger = logging.getLogger(__name__)


class ThemeDict(TypedDict):
    bg: Tuple[int, int, int]
    accent: Tuple[int, int, int]
    accent2: Tuple[int, int, int]
    text: Tuple[int, int, int]
    subtext: Tuple[int, int, int]
    progress_bg: Tuple[int, int, int]


def parse_size(s: str) -> Tuple[int, int]:
    w, h = s.lower().split("x")
    return int(w), int(h)


THEMES: Dict[str, ThemeDict] = {
    "midnight": {
        "bg": (15, 18, 30),  # Etwas dunkler für besseren Kontrast
        "accent": (64, 180, 255),
        "accent2": (255, 128, 64),
        "text": (245, 250, 255),  # Hellerer Text für bessere Lesbarkeit
        "subtext": (200, 210, 230),
        "progress_bg": (50, 55, 75),  # Dunklerer Fortschrittsbalken
    },
    "sunset": {
        "bg": (20, 15, 25),  # Etwas dunkler
        "accent": (255, 120, 80),
        "accent2": (255, 215, 120),
        "text": (255, 245, 240),
        "subtext": (230, 210, 200),
        "progress_bg": (60, 35, 45),
    },
    "ocean": {
        "bg": (8, 20, 25),  # Etwas dunkler
        "accent": (0, 200, 180),
        "accent2": (0, 140, 255),
        "text": (230, 250, 250),  # Hellerer Text
        "subtext": (200, 220, 220),
        "progress_bg": (35, 55, 65),  # Dunklerer Fortschrittsbalken
    },
}


def load_cover(cover_path: Optional[str], size: Tuple[int, int], blur: int = 0) -> Tuple[Image.Image, Optional[Image.Image], Tuple[int, int], int]:
    """Load cover image and produce a soft blurred background.

    Returns: (bg_base, cover_image_or_None, (x,y), d)
    - bg_base: background image (without the foreground cover)
    - cover_image_or_None: original cover as PIL.Image (not resized) or None
    - (x,y): default position where the cover should be placed
    - d: default side length of the display area
    """
    base = Image.new("RGB", size, (0, 0, 0))
    if cover_path and os.path.exists(cover_path):
        img = Image.open(cover_path).convert("RGB")
        # weiche Hintergrundfüllung mit Blur (nur Hintergrund)
        bg = img.copy().resize(size, Image.LANCZOS)
        if blur > 0:
            bg = bg.filter(ImageFilter.GaussianBlur(blur))
        base.paste(bg, (0, 0))

    # Keep the original image; we will scale it later using a 'contain'
    # strategy so the whole image is visible inside the 16:9 display area.
        src_w, src_h = img.size
        cover_rect = img.convert("RGB")

    # Target width as a fraction of the canvas (slightly smaller than min)
        d = int(min(size) * 0.72)
        x = (size[0] - d) // 2
        area_h = int(d * 9 / 16)
        # etwas höher positionieren für bessere Sichtbarkeit
        y = int(size[1] * 0.14)
    # Create a mask behind the cover area to hide background details
    # (e.g. embedded small covers)
        try:
            mask_layer = Image.new('RGBA', size, (0, 0, 0, 0))
            md = ImageDraw.Draw(mask_layer)
            pad = max(8, int(d * 0.06))
            radius = max(6, int(d // 24))
            md.rounded_rectangle([x - pad, y - pad, x + d + pad, y + area_h + pad],
                                 radius=radius, fill=(0, 0, 0, 200))
            # Blur the mask so the transition looks natural
            mask_layer = mask_layer.filter(ImageFilter.GaussianBlur(radius=6))
            base = Image.alpha_composite(base.convert('RGBA'), mask_layer).convert('RGB')
        except Exception:
            # If PIL operations fail, ignore the mask gracefully
            pass

    return base, cover_rect, (x, y), d

    return base, None, (0, 0), 0




def text_draw(img: Image.Image, title: str, subtitle: str, theme: dict, size: Tuple[int, int]) -> Image.Image:
    W, H = size
    draw = ImageDraw.Draw(img)
    # Fonts (widely available DejaVu fonts)
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", int(H * 0.07))  # Etwas größer
        font_sub = ImageFont.truetype("DejaVuSans.ttf", int(H * 0.04))  # Etwas größer
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    # Title
    t_bbox = draw.textbbox((0, 0), title, font=font_title)
    tw, th = t_bbox[2] - t_bbox[0], t_bbox[3] - t_bbox[1]
    draw.text(((W - tw) / 2, int(H * 0.75)), title, fill=theme["text"], font=font_title)  # Etwas höher
    # Subtitle
    if subtitle:
        s_bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
        sw, sh = s_bbox[2] - s_bbox[0], s_bbox[3] - s_bbox[1]
        draw.text(((W - sw) / 2, int(H * 0.75) + th + int(H * 0.025)),  # Etwas mehr Abstand
                  subtitle, fill=theme["subtext"], font=font_sub)
    return img


# Note: previous `build_wave_scroll` function was removed.
# Audio loading and a simple analysis happens inline in `make_video`.


def make_video(args):
    theme = THEMES.get(args.theme, THEMES["midnight"])

    # Audioanalyse (inline: suche Datei, lade Audio, berechne Mel-Spectrogram und Dauer)
    audio_path = args.audio
    if not os.path.exists(audio_path):
        base = os.path.splitext(os.path.basename(audio_path))[0]
        logger.warning("Audio file not found: %s", audio_path)
        logger.info("Searching project for files that contain '%s' or start with it...", base)
        candidates = []
        for root, dirs, files in os.walk(os.getcwd()):
            for f in files:
                if f.lower().endswith((".mp3", ".wav")) and (f.startswith(base) or base in root):
                    candidates.append(os.path.join(root, f))
        if candidates:
            candidates = sorted(candidates)
            audio_path = candidates[0]
            logger.info("Using found audio file: %s", audio_path)
        else:
            # Exit with an explanatory message suitable for CLI use
            raise SystemExit(f"Audio file not found and no candidates in project: {audio_path}")

    # Lade Audio (librosa) und berechne vereinfachtes Mel-Spectrogram
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048,
                                       hop_length=256, n_mels=96)
    S_dB = librosa.power_to_db(S, ref=np.max)
    S_norm = (S_dB - S_dB.min()) / (S_dB.max() - S_dB.min() + 1e-9)
    duration = len(y) / sr
    audio_fps = sr / 256
    resolved_audio = audio_path
    # Vereinfachte Energiespur: mittlerer Mel-Band Pegel pro Spalte
    energy = S_norm.mean(axis=0) if S_norm is not None else None

    # Canvas
    W, H = parse_size(args.size)
    fps = int(args.fps)

    # Hintergrund + Texte (bg_template ohne das quadratische Cover)
    bg_template, cover_square, cover_pos, cover_d = load_cover(args.cover, (W, H), blur=args.bg_blur)
    if cover_square is None:
        bg = Image.new("RGB", (W, H), theme["bg"])
        bg_template = bg
    # leichte Abdunklung für bessere Lesbarkeit (etwas dezenter)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 70))
    temp = bg_template.convert("RGBA")
    temp.alpha_composite(overlay)
    temp = temp.convert("RGB")
    # Texte auf das Template malen
    temp = text_draw(temp, args.title, args.subtitle, theme, (W, H))
    bg_np = np.array(temp)

    # Layout
    p_margin = int(W * 0.12)
    p_y = int(H * 0.93)
    p_h = max(8, H // 100)  # Slightly thicker for better visibility

    total_cols = S_norm.shape[1]

    def make_frame(t: float) -> np.ndarray:
        # Fortschritt 0..1
        progress = min(max(t / duration, 0), 1.0)
        
        # Erstelle Frame ohne Wellenform - nur Hintergrund, Texte und Fortschrittsbalken
        frame = Image.fromarray(bg_np).convert("RGBA").copy()
        draw = ImageDraw.Draw(frame)

        # If cover is available: animated zoom (display area 16:9)
        if cover_square is not None:
            cx, cy = cover_pos
            zoom = 1.0 + 0.035 * math.sin(2 * math.pi * (t / 6.0))
            area_w = int(cover_d)
            area_h = max(2, int(area_w * 9 / 16))
            # Compute contain scaling so the whole source is visible with a slight zoom animation
            src_w, src_h = cover_square.size
            w, h = compute_contain_size(src_w, src_h, area_w, area_h, zoom)
            cover_resized = cover_square.resize((w, h), Image.LANCZOS)
            # abgerundete Ecken für 16:9
            radius = max(6, int(min(w, h) // 24))
            mask = Image.new('L', (w, h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
            # Schatten: leichtes, halbtransparentes Rechteck hinter dem Cover
            # Schatten: sehr dezent, nahe am Cover
            shadow = Image.new('RGBA', (w + 8, h + 8), (0, 0, 0, 0))
            sh_draw = ImageDraw.Draw(shadow)
            sh_draw.rounded_rectangle([4, 4, w + 4, h + 4], radius=radius + 1, fill=(0, 0, 0, 120))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=4))

            # Center the contained image inside the 16:9 display area
            paste_x = cx + (area_w - w) // 2
            paste_y = cy + (area_h - h) // 2
            # Clamp to canvas
            paste_x = max(0, min(paste_x, W - w))
            paste_y = max(0, min(paste_y, H - h))
            # paste shadow slightly down-right but close
            frame.paste(shadow, (paste_x + 2, paste_y + 2), shadow)
            # dezente helle Kontur (weiß, sehr transparent) hinter dem Cover
            border = Image.new('RGBA', (w + 6, h + 6), (255, 255, 255, 0))
            b_draw = ImageDraw.Draw(border)
            b_draw.rounded_rectangle([0, 0, w + 5, h + 5], radius=radius + 2, fill=(255, 255, 255, 12))
            frame.paste(border, (paste_x - 3, paste_y - 3), border)
            # paste cover mit mask (immer last, damit es sichtbar bleibt)
            frame.paste(cover_resized, (paste_x, paste_y), mask)

        # Fortschrittsbalken
        draw.rounded_rectangle([p_margin, p_y, W - p_margin, p_y + p_h],
                               radius=p_h // 2, fill=theme["progress_bg"])
        fill_w = p_margin + int(progress * (W - 2 * p_margin))
        draw.rounded_rectangle([p_margin, p_y, fill_w, p_y + p_h],
                               radius=p_h // 2, fill=theme["accent"])

    # Keine Wellenform zeichnen (schlichte Darstellung)

        return np.array(frame.convert("RGB"))

    # Build video and attach audio
    clip = VideoClip(make_frame, duration=duration).with_audio(AudioFileClip(args.audio))
    clip = clip.with_fps(fps)

    # Erstes MP4 rendern
    temp_out = args.out
    clip.write_videofile(temp_out, codec="libx264", audio_codec="aac",
                         fps=fps, preset="medium", bitrate=args.bitrate)

    # Untertitel (optional) anhängen/einbrennen via ffmpeg
    if args.subtitles:
        vtt = args.subtitles
        base, ext = os.path.splitext(args.out)
        if args.subs_mode == "soft":
            soft_out = f"{base}_softsubs.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-i", temp_out,
                "-i", vtt,
                "-c:v", "copy", "-c:a", "copy",
                "-c:s", "mov_text",
                soft_out
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info("Soft subtitles muxed -> %s", soft_out)
            except Exception as e:
                logger.warning("Could not mux soft subtitles. Check ffmpeg. %s", e)
        elif args.subs_mode == "burn":
            burn_out = f"{base}_burned.mp4"
            # Für Pfade mit Sonderzeichen einfache Quotes verwenden
            vf_expr = f"subtitles='{vtt}'"
            cmd = [
                "ffmpeg", "-y",
                "-i", temp_out,
                "-vf", vf_expr,
                "-c:a", "copy",
                burn_out
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.info("Burned-in subtitles -> %s", burn_out)
            except Exception as e:
                logger.warning("Could not burn subtitles. Check ffmpeg/libass. %s", e)


def main():
    # Logging-Grundkonfiguration, damit CLI-Infos sichtbar werden
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    ap = argparse.ArgumentParser(description="Melody Mind Audiogram Generator")
    ap.add_argument("--audio", required=True, help="Pfad zur Audio-Datei (mp3/wav)")
    ap.add_argument("--verbose", action="store_true", help="Enable verbose logging output")
    ap.add_argument("--cover", default=None, help="Pfad zum Cover-Bild (optional)")
    ap.add_argument("--title", default="The Melody Mind Podcast", help="Titelzeile")
    ap.add_argument("--subtitle", default="", help="Untertitel/ Episodentitel")
    ap.add_argument("--size", default="1920x1080", help="Video-Größe, z.B. 1920x1080 oder 1080x1080")
    ap.add_argument("--fps", type=int, default=30, help="Framerate")
    ap.add_argument("--bg_blur", type=int, default=16, help="Weichzeichner für Cover-Hintergrund")
    ap.add_argument("--theme", default="midnight", choices=list(THEMES.keys()))
    ap.add_argument("--out", default="audiogram.mp4", help="Ausgabe-Video")
    ap.add_argument("--bitrate", default="12M", help="Video-Bitrate (z.B. 8M, 12M, 20M)")
    ap.add_argument("--subtitles", default=None, help="Pfad zu .vtt oder .srt Datei (optional)")
    ap.add_argument("--subs_mode", default="soft", choices=["soft", "burn"],
                    help="Untertitel als Soft-Subs (MP4 mov_text) oder eingebrannt")
    args = ap.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    make_video(args)


if __name__ == "__main__":
    main()