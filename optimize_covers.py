#!/usr/bin/env python3
"""CLI tool to optimize cover images for web delivery.

Features:
- Reads PNG/JPEG/WebP images from an input directory
- Converts everything to JPEG (unless already JPEG) for consistent compression
- Scales the longest side down to a maximum dimension while keeping aspect ratio
- Applies efficient export settings (optimize, optional progressive, 4:2:0 subsampling)
- Skips already processed files if desired
- Parallel processing using ThreadPool for I/O bound speedup

Example:
    python optimize_covers.py --input-dir covers --output-dir covers_optimized --max-size 1200 --quality 82 --progressive

Recommended quality range: 80–85 (good balance between size and fidelity). Default adds NO suffix; use --suffix _web if you want to mark optimized copies.

Dependencies: Pillow, tqdm
"""
from __future__ import annotations
import argparse
import concurrent.futures
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from PIL import Image, ImageFile
from tqdm import tqdm

ImageFile.LOAD_TRUNCATED_IMAGES = True  # Be tolerant with slightly truncated files

SUPPORTED_EXT = {'.png', '.jpg', '.jpeg', '.webp'}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimize cover images for the web (JPEG export).")
    parser.add_argument('--input-dir', '-i', type=Path, required=True, help='Input directory containing original covers')
    parser.add_argument('--output-dir', '-o', type=Path, required=True, help='Destination directory for optimized images')
    parser.add_argument('--max-size', type=int, default=1600, help='Max edge length (pixels) of the longest side (default: 1600)')
    parser.add_argument('--quality', type=int, default=82, help='JPEG quality (recommended 80-85)')
    parser.add_argument('--suffix', type=str, default='', help='Suffix added before extension (default: empty)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite already optimized files')
    parser.add_argument('--progressive', action='store_true', help='Enable progressive JPEG (recommended)')
    parser.add_argument('--keep-filename', action='store_true', help='Keep original filename (risk of overwriting)')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel threads')
    parser.add_argument('--skip-existing', action='store_true', help='Skip processing if target file exists')
    # Removed advanced flags (reporting, aspect enforcement, ratio listing) per request
    return parser.parse_args()


def collect_images(input_dir: Path) -> List[Path]:
    files: List[Path] = []
    for p in input_dir.iterdir():
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXT:
            files.append(p)
    return sorted(files)


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def resize_image(img: Image.Image, max_size: int) -> Image.Image:
    if max(img.size) <= max_size:
        return img
    # Maintain aspect ratio with high-quality downscaling
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    return img


def build_target_name(src: Path, out_dir: Path, suffix: str, keep_filename: bool) -> Path:
    if keep_filename:
        stem = src.stem
    else:
        stem = f"{src.stem}{suffix}" if suffix else src.stem
    return out_dir / f"{stem}.jpg"


def convert_one(src: Path, out_dir: Path, max_size: int, quality: int, suffix: str, overwrite: bool,
                progressive: bool, skip_existing: bool, keep_filename: bool) -> Tuple[Path, str, Optional[dict]]:
    try:
        target = build_target_name(src, out_dir, suffix, keep_filename)
        if skip_existing and target.exists() and not overwrite:
            # Gather minimal info even if skipped
            with Image.open(target) as ti:
                w2, h2 = ti.size
            with Image.open(src) as si:
                w1, h1 = si.size
            orig_size = src.stat().st_size
            new_size = target.stat().st_size
            return target, 'skipped', {
                'source': src,
                'target': target,
                'orig_w': w1,
                'orig_h': h1,
                'new_w': w2,
                'new_h': h2,
                'orig_bytes': orig_size,
                'new_bytes': new_size,
            }

        with Image.open(src) as im:
            # Composite transparency over white background if needed
            if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
                background = Image.new('RGB', im.size, (255, 255, 255))
                background.paste(im, mask=im.split()[-1])
                im = background
            elif im.mode != 'RGB':
                im = im.convert('RGB')

            orig_w, orig_h = im.size

            # No aspect enforcement (removed)
            im = resize_image(im, max_size)
            new_w, new_h = im.size

            save_kwargs = dict(
                format='JPEG',
                quality=quality,
                optimize=True,
                progressive=progressive,
                subsampling='4:2:0'
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            im.save(target, **save_kwargs)
        info = {
            'source': src,
            'target': target,
            'orig_w': orig_w,
            'orig_h': orig_h,
            'new_w': new_w,
            'new_h': new_h,
            'orig_bytes': src.stat().st_size,
            'new_bytes': target.stat().st_size,
        }
        return target, 'ok', info
    except Exception as e:  # noqa: BLE001
        return src, f'error: {type(e).__name__}: {e}', None


def process_all(images: Iterable[Path], args: argparse.Namespace) -> None:
    ensure_output_dir(args.output_dir)
    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for img in images:
            tasks.append(ex.submit(
                convert_one,
                img,
                args.output_dir,
                args.max_size,
                args.quality,
                args.suffix,
                args.overwrite,
                args.progressive,
                args.skip_existing,
                args.keep_filename,
            ))
        results = []  # list of (path, status, info)
        for f in tqdm(concurrent.futures.as_completed(tasks), total=len(tasks), desc='Optimizing'):
            results.append(f.result())

    # Summary report
    ok = sum(1 for _, status, _ in results if status == 'ok')
    skipped = sum(1 for _, status, _ in results if status == 'skipped')
    failed = [(path, status) for path, status, _ in results if status.startswith('error')]
    print(f"Done: {ok} ok, {skipped} skipped, {len(failed)} errors")
    if failed:
        for p, status in failed[:10]:  # only first 10
            print(f"  {status} -> {p}")

    # Reporting
    # Reporting removed per request


def main():
    args = parse_args()
    if not args.input_dir.exists():
        raise SystemExit(f"Input directory not found: {args.input_dir}")
    images = collect_images(args.input_dir)
    if not images:
        raise SystemExit('No supported image files found.')
    process_all(images, args)


if __name__ == '__main__':
    main()
