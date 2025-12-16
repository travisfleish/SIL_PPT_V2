#!/usr/bin/env python3
"""
Crop an image to a centered circle with a transparent background.

Unlike `assets/crop_circle.py`, this script is designed for one-off use and
will NOT overwrite the input by default.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw


def _center_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def _circle_mask(size: Tuple[int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0], size[1]), fill=255)
    return mask


def crop_to_circle(
    input_path: Path,
    output_path: Path,
    size: Optional[int] = None,
) -> Path:
    img = Image.open(input_path).convert("RGBA")
    img = _center_square(img)

    if size:
        img = img.resize((size, size), Image.Resampling.LANCZOS)

    mask = _circle_mask(img.size)
    img.putalpha(mask)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop an image into a circle (transparent PNG)")
    parser.add_argument("input", type=Path, help="Input image path")
    parser.add_argument("output", type=Path, help="Output PNG path")
    parser.add_argument("--size", type=int, default=1024, help="Output width/height in px (square)")
    args = parser.parse_args()

    out = crop_to_circle(args.input, args.output, size=args.size)
    print(f"✅ Wrote circular PNG: {out}")


if __name__ == "__main__":
    main()


