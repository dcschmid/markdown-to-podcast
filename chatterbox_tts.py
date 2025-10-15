#!/usr/bin/env python3
"""Chatterbox Multilingual Podcast TTS
-------------------------------------

Standalone script using the open‑source Chatterbox (Resemble AI) multilingual TTS
engine (or a mock fallback if the library is missing) to convert Markdown
dialogue scripts into audio (WAV/MP3) plus WebVTT subtitles.

Goals:
- Fully independent from the removed Speechify backend
- Multilingual support: de, en, es, it, fr, pt (extensible)
- Optional voice cloning / style prompt file (`audio_prompt_path`)
- Simple CLI ("Name: Text" speaker lines)
- Configurable pauses between segments
- Outputs: MP3 + .vtt (+ optional per‑segment WAV; JSON metadata & intro/outro music support removed)

Dependencies:
- chatterbox-tts (for real synthesis) -> `pip install chatterbox-tts`
- torchaudio (dependency) / pydub for MP3 export / ffmpeg in system
- dotenv (optional)

Mock mode:
If chatterbox is not available or `--mock` is set, the script produces
synthetic silence segments so the pipeline can be tested without the model.

License: Chatterbox is MIT (see upstream). This script only calls public APIs.
"""
from __future__ import annotations

import argparse
import os
import sys
import re
import math
import json
import logging
import uuid
import warnings
from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from dotenv import load_dotenv

# Audio handling
try:
    from pydub import AudioSegment  # For combining segments & MP3 export
except Exception as e:  # pragma: no cover
    raise RuntimeError("pydub must be installed (pip install pydub)") from e

# Try loading chatterbox
HAS_CHATTERBOX = False
try:  # pragma: no cover - Import Pfad kann variieren
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # type: ignore
    HAS_CHATTERBOX = True
except Exception:  # pragma: no cover - Fallback Mock
    HAS_CHATTERBOX = False

# Network download (for optional automatic language prompts)
try:
    import requests  # type: ignore
    HAS_REQUESTS = True
except Exception:  # pragma: no cover
    HAS_REQUESTS = False

# Logging Setup
LOG_LEVEL = os.getenv("CHATTERBOX_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("chatterbox_tts")

SUPPORTED_LANGS = {"de", "en", "es", "it", "fr", "pt"}
DEFAULT_LANGUAGE = "de"

# Default symbolic voice mapping per language (logical tokens; actual timbre via prompt)
DEFAULT_VOICE_MAPPING: Dict[str, Dict[str, str]] = {
    "de": {"male": "de_m", "female": "de_f", "daniel": "de_m", "annabelle": "de_f"},
    "en": {"male": "en_m", "female": "en_f", "daniel": "en_m", "annabelle": "en_f"},
    "es": {"male": "es_m", "female": "es_f", "daniel": "es_m", "annabelle": "es_f"},
    "it": {"male": "it_m", "female": "it_f", "daniel": "it_m", "annabelle": "it_f"},
    "fr": {"male": "fr_m", "female": "fr_f", "daniel": "fr_m", "annabelle": "fr_f"},
    "pt": {"male": "pt_m", "female": "pt_f", "daniel": "pt_m", "annabelle": "pt_f"},
}

# Remote prompt URL support removed (local bundled prompts now cover all supported languages).

# Regex: speaker line "Name: Text"
SPEAKER_LINE = re.compile(r"^([A-Za-z0-9_ÄÖÜäöüß\- ]{1,40}):\s*(.*)$")


@dataclass
class Segment:
    index: int
    speaker: str
    text: str
    start: float = 0.0
    end: float = 0.0


class MarkdownDialogueParser:
    """Extract speaker segments from a simple Markdown dialogue format."""

    def parse(self, content: str) -> List[Segment]:
        lines = content.splitlines()
        segments: List[Segment] = []
        current_speaker: Optional[str] = None
        buffer: List[str] = []

        def flush():
            nonlocal segments, current_speaker, buffer
            if current_speaker and buffer:
                text = " ".join([b.strip() for b in buffer if b.strip()]).strip()
                if text:
                    segments.append(
                        Segment(index=len(segments) + 1, speaker=current_speaker.lower(), text=text)
                    )
            buffer = []

        for line in lines:
            line = line.rstrip()
            if not line.strip():
                # Blank line => flush current segment
                flush()
                current_speaker = current_speaker  # bleibt
                continue
            m = SPEAKER_LINE.match(line)
            if m:
                flush()
                current_speaker = m.group(1).strip()
                rest = m.group(2).strip()
                if rest:
                    buffer.append(rest)
            else:
                if current_speaker:
                    buffer.append(line.strip())
        flush()
        return segments


class ChatterboxSynthesizer:
    """Wrapper around Chatterbox or a mock fallback with automatic device selection.

    Device strategy:
    - device="auto": try cuda then cpu
    - device="cuda": if failing, fall back to cpu (warn)
    - device="cpu": only cpu
    If loading fails on all candidates -> switch to mock.
    """

    def __init__(
        self,
        language: str,
        device: str = "auto",
        mock: bool = False,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        audio_prompt_path: Optional[str] = None,
    ):
        self.language = language if language in SUPPORTED_LANGS else DEFAULT_LANGUAGE
        self.requested_device = device
        self.device = device
        self.mock = mock or not HAS_CHATTERBOX
        self.exaggeration = exaggeration
        self.cfg_weight = cfg_weight
        self.audio_prompt_path = audio_prompt_path
        self.sample_rate = 44100  # Fallback SR
        self.model = None

        if self.mock:
            if not HAS_CHATTERBOX:
                logger.warning("Chatterbox package not installed – entering mock mode")
            return

    # Device selection loop
        candidate_devices: List[str] = []
        if device == "auto":
            candidate_devices = ["cuda", "cpu"]
        elif device == "cuda":
            candidate_devices = ["cuda", "cpu"]  # Fallback versuchen
        else:
            candidate_devices = ["cpu"]

        for dev in candidate_devices:
            try:
                logger.info("Loading Chatterbox multilingual model (device=%s)...", dev)
                self.model = ChatterboxMultilingualTTS.from_pretrained(device=dev)
                self.device = dev
                self.sample_rate = getattr(self.model, "sr", self.sample_rate)
                logger.info("Model loaded on %s (sample rate %s)", dev, self.sample_rate)
                break
            except Exception as e:  # pragma: no cover
                logger.warning("Loading on %s failed (%s)", dev, e)
                # Special CPU fallback: checkpoint serialized with CUDA tensors -> enforce map_location=cpu
                if (
                    dev == "cpu"
                    and "deserialize object on a CUDA device" in str(e)
                    and HAS_CHATTERBOX
                ):
                    try:
                        import torch  # type: ignore

                        original_load = torch.load

                        def _cpu_load(*args, **kwargs):  # noqa: D401
                            if "map_location" not in kwargs:
                                kwargs["map_location"] = torch.device("cpu")
                            return original_load(*args, **kwargs)

                        torch.load = _cpu_load  # type: ignore
                        logger.info("Retrying load with forced map_location=cpu ...")
                        try:
                            self.model = ChatterboxMultilingualTTS.from_pretrained(
                                device="cpu"
                            )
                            self.device = "cpu"
                            self.sample_rate = getattr(
                                self.model, "sr", self.sample_rate
                            )
                            logger.info("Model loaded with map_location=cpu (sample rate %s)", self.sample_rate)
                            break
                        except Exception as e2:  # pragma: no cover
                            logger.warning("Retry with map_location=cpu failed (%s)", e2)
                        finally:
                            torch.load = original_load  # type: ignore
                    except Exception as patch_err:  # pragma: no cover
                        logger.debug("Could not apply map_location patch (%s)", patch_err)
                self.model = None
                continue

        if self.model is None:
            logger.error("Could not load model on any device – switching to mock mode")
            self.mock = True

    def synthesize(self, text: str, speaker_key: str, prompt_path: Optional[str] = None) -> AudioSegment:
        if self.mock:
            # Duration heuristic based on word count
            words = max(1, len(text.split()))
            seconds = min(10.0, 0.4 * words)  # 400ms pro Wort grob
            silence_ms = int(seconds * 1000)
            return AudioSegment.silent(duration=silence_ms)
    # Real generation
        kwargs = {
            "exaggeration": self.exaggeration,
            "cfg_weight": self.cfg_weight,
        }
    # Precedence: segment-specific prompt > global prompt > none
        active_prompt = None
        if prompt_path and os.path.exists(prompt_path):
            active_prompt = prompt_path
        elif self.audio_prompt_path and os.path.exists(self.audio_prompt_path):
            active_prompt = self.audio_prompt_path
        if active_prompt:
            kwargs["audio_prompt_path"] = active_prompt
        try:
            wav_tensor = self.model.generate(text, language_id=self.language, **kwargs)  # type: ignore
            # Convert tensor -> pydub AudioSegment (wav_tensor shape: (1, samples))
            import numpy as np
            import torch  # type: ignore
            if hasattr(wav_tensor, "detach"):
                wav_np = wav_tensor.detach().cpu().numpy()
            else:
                wav_np = wav_tensor
            if wav_np.ndim == 2:
                wav_np = wav_np[0]
            # Normiere auf 16-bit PCM
            wav_int16 = (wav_np * 32767.0).clip(-32768, 32767).astype("int16")
            audio = AudioSegment(
                wav_int16.tobytes(),
                frame_rate=self.sample_rate,
                sample_width=2,
                channels=1,
            )
            return audio
        except Exception as e:  # pragma: no cover
            logger.error("Synthesis error (%s) -> inserting silence", e)
            return AudioSegment.silent(duration=1000)


class PodcastAssembler:
    def __init__(self, pause_ms: int = 500):
        self.pause_ms = pause_ms

    def assemble(self, segments_audio: List[AudioSegment]) -> AudioSegment:
        total = AudioSegment.silent(duration=0)
        first = True
        for seg in segments_audio:
            if not first:
                total += AudioSegment.silent(duration=self.pause_ms)
            total += seg
            first = False
        return total


def export_webvtt(segments: List[Segment], path: Path):
    def fmt(ts: float) -> str:
        hours = int(ts // 3600)
        minutes = int((ts % 3600) // 60)
        secs = ts % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")
    with path.open("w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{fmt(seg.start)} --> {fmt(seg.end)}\n")
            speaker = re.sub(r"\s+", "_", seg.speaker.title())
            f.write(f"<v {speaker}>{seg.text}\n\n")


def build_speaker_mapping(language: str, custom: Optional[Dict[str, str]]) -> Dict[str, str]:
    mapping = {}
    lang_map = DEFAULT_VOICE_MAPPING.get(language, {})
    for role, token in lang_map.items():
        mapping[role] = token
    if custom:
        for k, v in custom.items():
            mapping[k.lower()] = v
    return mapping


def derive_speaker_key(name: str, mapping: Dict[str, str]) -> str:
    n = name.lower()
    # Direct matches incl. daniel / annabelle
    if n in mapping:
        return mapping[n]
    # Heuristic: female names / markers
    if any(x in n for x in ["annabelle", "anna", "anne", "lisa", "sarah", "eva", "marie", "frau", "female", "f"]):
        return mapping.get("annabelle", mapping.get("female", "neutral_f"))
    # Heuristic: male names / markers (fallback only)
    if any(x in n for x in ["daniel", "peter", "max", "tom", "male", "mann", "m"]):
        return mapping.get("daniel", mapping.get("male", "neutral_m"))
    # Default fallback: male token
    return mapping.get("daniel", mapping.get("male", "neutral_m"))


def find_local_prompts(language: str, voices_dir: Path, cache_dir: Path) -> Dict[str, str]:
    """Find local prompt files inside the `voices` directory.

    Supported extensions: wav, mp3, flac, ogg, m4a
    Priority name patterns (per gender):
        <lang>_male.*  | <lang>_female.*
        male.*         | female.*

    Non‑WAV files are converted once into WAV and cached.
    Returns a dict for present keys ("male", "female").
    """
    result: Dict[str, str] = {}
    if not voices_dir.exists() or not voices_dir.is_dir():
        return result
    candidates = list(voices_dir.iterdir())
    exts = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
    patterns = [
        (f"{language}_male", "male"),
        (f"{language}_female", "female"),
        ("male", "male"),
        ("female", "female"),
    ]

    def convert_to_wav(src: Path) -> Path:
        if src.suffix.lower() == ".wav":
            return src
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            target = cache_dir / (src.stem + ".wav")
            if not target.exists() or target.stat().st_mtime < src.stat().st_mtime:
                audio = AudioSegment.from_file(str(src))
                audio.export(str(target), format="wav")
            return target
        except Exception as e:  # pragma: no cover
            logger.warning("Conversion to WAV failed (%s) for %s", e, src)
            return src

    for file in candidates:
        if not file.is_file() or file.suffix.lower() not in exts:
            continue
        lower = file.name.lower()
        for pat, gender in patterns:
            if lower.startswith(pat.lower() + ".") or lower == pat.lower():
                if gender not in result:  # first matching pattern wins (priority order)
                    wav_path = convert_to_wav(file)
                    result[gender] = str(wav_path)
                break
    if result:
        logger.info("Local prompts detected: %s", {k: Path(v).name for k, v in result.items()})
    return result


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Podcast Markdown -> Audio via Chatterbox (multilingual)")
    parser.add_argument("input_file", help="Markdown file with dialogue")
    parser.add_argument("--language", "-l", default=DEFAULT_LANGUAGE, help="Language code (de,en,es,it,fr,pt)")
    parser.add_argument("--output-dir", default="output_chatterbox", help="Output directory root")
    parser.add_argument("--output-prefix", default=None, help="Optional base name (default: input stem)")
    parser.add_argument("--speakers", help="Custom mapping name:token,name2:token2")
    parser.add_argument("--pause-ms", type=int, default=500, help="Pause (ms) between segments")
    parser.add_argument("--exaggeration", type=float, default=0.5, help="Expressiveness exaggeration (0-1)")
    parser.add_argument("--cfg-weight", type=float, default=0.5, help="Guidance weight (0-1)")
    parser.add_argument("--device", default="auto", help="Device (cuda|cpu|auto)")
    parser.add_argument("--audio-prompt", help="Path to global reference voice (WAV/any supported)")
    parser.add_argument("--mock", action="store_true", help="Force mock (no real synthesis)")
    # Default-on flags (can be disabled with --no-*)
    parser.add_argument("--export-wav", action="store_true", default=True, help="Export final WAV (disable with --no-export-wav)")
    parser.add_argument("--no-export-wav", action="store_false", dest="export_wav")
    parser.add_argument("--save-segments-wav", action="store_true", default=True, help="Save each segment as WAV (disable with --no-save-segments-wav)")
    parser.add_argument("--no-save-segments-wav", action="store_false", dest="save_segments_wav")
    parser.add_argument("--prompts-cache-dir", default=".cache/chatterbox_prompts", help="Cache dir for downloaded prompts")
    parser.add_argument("--suppress-warnings", action="store_true", default=True, help="Suppress common future/deprecation warnings (disable with --no-suppress-warnings)")
    parser.add_argument("--no-suppress-warnings", action="store_false", dest="suppress_warnings")
    parser.add_argument("--attn-eager", action="store_true", help="Set HF attention implementation to 'eager'")
    parser.add_argument("--structured-output", action="store_true", default=True, help="Hierarchical layout: <out>/<language>/<topic>/(final|segments) (disable with --no-structured-output)")
    parser.add_argument("--no-structured-output", action="store_false", dest="structured_output")
    parser.add_argument("--voices-dir", default="voices", help="Directory with local prompt samples (e.g. de_male.mp3)")

    args = parser.parse_args()

    language = args.language.lower()
    if language not in SUPPORTED_LANGS:
        logger.warning("Language %s untested – falling back to %s", language, DEFAULT_LANGUAGE)
        language = DEFAULT_LANGUAGE

    input_path = Path(args.input_file)
    if not input_path.exists():
        logger.error("Input file missing: %s", input_path)
        return 1
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    base_name = args.output_prefix or input_path.stem

    # Prepare structured output layout if requested
    if args.structured_output:
        topic = base_name
        structured_base = output_root / language / topic
        final_dir = structured_base / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        segments_parent_dir = structured_base / "segments" if args.save_segments_wav else None
        if segments_parent_dir:
            segments_parent_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Structured output enabled: %s", structured_base)
    else:
        final_dir = output_root
        segments_parent_dir = output_root / "segments_wav" if args.save_segments_wav else None
        if segments_parent_dir and not segments_parent_dir.exists():
            segments_parent_dir.mkdir(parents=True, exist_ok=True)
        # Inform user about flat storage if they expected hierarchy
        if args.save_segments_wav and not args.structured_output:
            logger.info(
                "Note: segment WAVs stored flat in %s/segments_wav. Use --structured-output for <out>/<lang>/<topic>/(final|segments)",
                output_root,
            )

    content = input_path.read_text(encoding="utf-8")
    parser_md = MarkdownDialogueParser()
    segments = parser_md.parse(content)
    if not segments:
        logger.error("No segments detected – aborting")
        return 1
    logger.info("%d segments detected", len(segments))

    # Speaker Mapping
    custom_map = {}
    if args.speakers:
        for pair in args.speakers.split(","):
            if ":" in pair:
                k, v = pair.split(":", 1)
                custom_map[k.strip().lower()] = v.strip()
    speaker_mapping = build_speaker_mapping(language, custom_map)

    synthesizer = ChatterboxSynthesizer(
        language=language,
        device=args.device,
        mock=args.mock,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        audio_prompt_path=args.audio_prompt,
    )

    # Warnings suppression (after model import so filters apply)
    if args.suppress_warnings:
        # Broad categories
        warnings.filterwarnings("ignore", category=FutureWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        # Specific patterns
        for pattern in [
            "pkg_resources is deprecated",
            "LoRACompatibleLinear is deprecated",
            "torch.backends.cuda.sdp_kernel",
            "past_key_values",
        ]:
            warnings.filterwarnings("ignore", message=pattern)
        logger.info("Suppressing future/deprecation warnings (--suppress-warnings)")

    # Attention implementation tweak (only if HF transformers present)
    if args.attn_eager and not synthesizer.mock:
        try:
            import transformers  # type: ignore
            from transformers.utils import logging as hf_logging  # type: ignore

            hf_logging.set_verbosity_error()
            # Versuch: globaler Default – einige Modelle respektieren env var
            os.environ["HF_ATTENTION_IMPLEMENTATION"] = "eager"
            logger.info("Setting HF_ATTENTION_IMPLEMENTATION=eager")
        except Exception as e:  # pragma: no cover
            logger.debug("Could not set attention implementation (%s)", e)
    if synthesizer.mock and not args.mock:
        logger.warning(
            "Falling back to mock (no functional model). Check install, CUDA availability or pass --mock explicitly."
        )

    assembler = PodcastAssembler(pause_ms=args.pause_ms)

    # Synthesis loop
    audio_segments: List[AudioSegment] = []
    current_time = 0.0
    segments_wav_dir: Optional[Path] = segments_parent_dir

    # Prompt preparation (local overrides > auto)
    auto_prompt_paths: Dict[str, str] = {}
    local_prompt_paths: Dict[str, str] = {}

    # First: search local prompts (highest priority)
    voices_dir = Path(args.voices_dir)
    local_cache = Path(args.prompts_cache_dir) / "_local_convert"
    local_prompt_paths = find_local_prompts(language, voices_dir, local_cache)

    if local_prompt_paths:
        logger.info("Using local prompts instead of automatic downloads")

    pad_width = max(3, len(str(len(segments))))
    for seg in segments:
        speaker_key = derive_speaker_key(seg.speaker, speaker_mapping)
        logger.info("Synthesize segment %d (%s -> %s) ...", seg.index, seg.speaker, speaker_key)
        # Select per-speaker prompt (local first, then auto)
        prompt_path = None
        if local_prompt_paths:
            s_lower = seg.speaker.lower()
            if any(x in s_lower for x in ["annabelle", "anna", "female", "frau"]):
                prompt_path = local_prompt_paths.get("female") or local_prompt_paths.get("male")
            elif any(x in s_lower for x in ["daniel", "male", "mann"]):
                prompt_path = local_prompt_paths.get("male") or local_prompt_paths.get("female")
            else:
                prompt_path = local_prompt_paths.get("female") or local_prompt_paths.get("male")
        elif auto_prompt_paths:
            s_lower = seg.speaker.lower()
            if any(x in s_lower for x in ["annabelle", "anna", "female", "frau"]):
                prompt_path = auto_prompt_paths.get("female") or auto_prompt_paths.get("male")
            elif any(x in s_lower for x in ["daniel", "male", "mann"]):
                prompt_path = auto_prompt_paths.get("male") or auto_prompt_paths.get("female")
            else:
                prompt_path = auto_prompt_paths.get("female") or auto_prompt_paths.get("male")
        audio = synthesizer.synthesize(seg.text, speaker_key, prompt_path=prompt_path)
        duration_sec = len(audio) / 1000.0
        seg.start = current_time
        seg.end = current_time + duration_sec
        current_time = seg.end + (args.pause_ms / 1000.0)
        audio_segments.append(audio)

    # Optional per-segment WAV export
        if segments_wav_dir is not None:
            safe_speaker = re.sub(r"[^a-zA-Z0-9_-]", "_", seg.speaker.lower())
            seg_filename = f"{base_name}_segment_{seg.index:0{pad_width}d}_{safe_speaker}.wav"
            seg_path = segments_wav_dir / seg_filename
            try:
                audio.export(str(seg_path), format="wav")
            except Exception as e:  # pragma: no cover
                logger.warning("Could not save segment %s (%s)", seg.index, e)

    combined = assembler.assemble(audio_segments)

    # Intro/outro music feature removed: directly use synthesized concatenation
    final_audio = combined

    # Export final assets
    mp3_path = final_dir / f"{base_name}.mp3"
    final_audio.export(str(mp3_path), format="mp3", bitrate="192k")
    logger.info("MP3 exported: %s (%.1fs)", mp3_path, len(final_audio)/1000.0)

    if args.export_wav:
        wav_path = final_dir / f"{base_name}.wav"
        final_audio.export(str(wav_path), format="wav")
        logger.info("WAV exported: %s", wav_path)

    vtt_path = final_dir / f"{base_name}.vtt"
    export_webvtt(segments, vtt_path)
    logger.info("VTT exported: %s", vtt_path)

    # JSON metadata export removed per updated requirements

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
