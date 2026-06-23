#!/usr/bin/env python3
"""Merge two images with a split line through the center at a given angle."""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path
from typing import Iterable, Sequence, Tuple

from PIL import Image, ImageDraw, ImageOps


Point = Tuple[float, float]
OUTPUT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
ALPHA_FORMATS = {"PNG", "WEBP", "TIFF", "GIF"}
RESAMPLING = getattr(Image, "Resampling", Image).LANCZOS
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def parse_angle(value: str) -> float:
    """Parse degrees ('45'), '45deg', or radians ('0.785rad'). Normalized to [0, 180)."""
    text = value.strip().lower()
    if text.endswith("deg"):
        angle = float(text[:-3])
    elif text.endswith("rad"):
        angle = math.degrees(float(text[:-3]))
    else:
        angle = float(text)
    return angle % 180.0


def default_normal(angle: float) -> Point:
    """Return the default normal direction pointing toward image1's side.

    Convention: the normal (-sin θ, -cos θ) in image coords.
    - θ=0 (horizontal line): normal (0, -1) → image1 on top.
    - θ=90 (vertical line): normal (-1, 0) → image1 on left.
    - θ=45 (/ diagonal): normal points up-left → image1 on upper-left.
    - θ=135 (\\ diagonal): normal points down-left → image1 on lower-left.
    """
    radians = math.radians(angle % 180.0)
    return (-math.sin(radians), -math.cos(radians))


def half_plane_polygon(width: int, height: int, angle: float, swap: bool = False) -> Sequence[Point]:
    """Polygon covering the half-plane where image1 should be placed."""
    normal = default_normal(angle)
    if swap:
        normal = (-normal[0], -normal[1])

    radians = math.radians(angle % 180.0)
    tx = math.cos(radians)
    ty = -math.sin(radians)  # image coords: y increases downward

    cx = width / 2.0
    cy = height / 2.0
    reach = math.hypot(width, height) * 2.0 + 8.0

    p1 = (cx + tx * reach, cy + ty * reach)
    p2 = (cx - tx * reach, cy - ty * reach)
    p3 = (p2[0] + normal[0] * reach, p2[1] + normal[1] * reach)
    p4 = (p1[0] + normal[0] * reach, p1[1] + normal[1] * reach)
    return (p1, p2, p3, p4)


def create_mask(width: int, height: int, angle: float, swap: bool = False) -> Image.Image:
    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive.")
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).polygon(half_plane_polygon(width, height, angle, swap), fill=255)
    return mask


def open_rgba(path: str | os.PathLike[str]) -> Image.Image:
    image_path = Path(path).expanduser()
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")
    return ImageOps.exif_transpose(Image.open(image_path)).convert("RGBA")


def resolve_output_path(path: str | os.PathLike[str]) -> Path:
    target = Path(path).expanduser()
    if not target.suffix:
        target = target.with_suffix(".png")
    if target.suffix.lower() not in OUTPUT_EXTENSIONS:
        target = target.with_suffix(".png")
    return target


def output_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "JPEG"
    if suffix == ".webp":
        return "WEBP"
    if suffix in {".tif", ".tiff"}:
        return "TIFF"
    if suffix == ".bmp":
        return "BMP"
    if suffix == ".gif":
        return "GIF"
    return "PNG"


def flatten_on_white(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
    canvas.alpha_composite(image)
    return canvas.convert("RGB")


def find_images_in_directory(directory: Path, exclude: Path | None = None) -> list[Path]:
    """Find image files in a directory, sorted by name, optionally excluding one path."""
    images = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if exclude is not None and entry.resolve() == exclude.resolve():
            continue
        images.append(entry)
    return images


def merge_images(
    image1_path: str,
    image2_path: str,
    output_image_path: str,
    angle: float,
    swap: bool = False,
) -> str:
    img1 = open_rgba(image1_path)
    img2 = open_rgba(image2_path)

    if img2.size != img1.size:
        img2 = img2.resize(img1.size, RESAMPLING)

    mask = create_mask(img1.width, img1.height, angle, swap)
    result = Image.composite(img1, img2, mask)

    target = resolve_output_path(output_image_path)
    fmt = output_format(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    if fmt not in ALPHA_FORMATS:
        result = flatten_on_white(result)

    save_kwargs = {"quality": 95} if fmt in {"JPEG", "WEBP"} else {}
    if fmt == "PNG":
        save_kwargs["optimize"] = True
    result.save(target, format=fmt, **save_kwargs)
    return str(target.resolve())


def resolve_images_and_output(args) -> Tuple[str, str, str]:
    if len(args.images) == 0:
        cwd = Path.cwd()
        output_str = args.output if args.output else str(cwd / "merged.png")
        output_resolved = resolve_output_path(output_str)
        exclude = output_resolved if output_resolved.parent.resolve() == cwd.resolve() else None
        images = find_images_in_directory(cwd, exclude=exclude)
        if len(images) != 2:
            raise ValueError(
                f"Expected exactly 2 images in {cwd}, found {len(images)}. "
                "Specify image paths explicitly."
            )
        return str(images[0]), str(images[1]), output_str
    if len(args.images) == 2:
        output_str = args.output if args.output else str(Path.cwd() / "merged.png")
        return args.images[0], args.images[1], output_str
    raise ValueError(f"Expected 0 or 2 image paths, got {len(args.images)}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge two images with a split line through the center at a given angle.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Angle convention (0-180 degrees):
  0 or 180 = horizontal line (top/bottom split)
  45       = / diagonal
  90       = vertical line (left/right split)
  135      = \\ diagonal

Default: image1 on the upper side (left for vertical lines).
Use --swap to flip sides.

If no image paths are given, auto-detects two images in the current directory.

Examples:
  image_diagonal_merge.py img1.png img2.png -o out.png --angle 45
  image_diagonal_merge.py --angle 90 --swap
""",
    )
    parser.add_argument(
        "images",
        nargs="*",
        help="Two image paths. If omitted, auto-detects two images in the current directory.",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output image path. Defaults to ./merged.png.",
    )
    parser.add_argument(
        "--angle", "-a",
        type=parse_angle,
        default=90.0,
        help="Split line angle in degrees (0-180). 90=vertical, 0/180=horizontal, 45=/, 135=\\\\. Default: 90.",
    )
    parser.add_argument(
        "--swap",
        action="store_true",
        help="Swap which side image1 is placed on.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        image1, image2, output = resolve_images_and_output(args)
        print(
            merge_images(
                image1,
                image2,
                output,
                angle=args.angle,
                swap=args.swap,
            )
        )
    except Exception as exc:
        print(f"image-diagonal-merge failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
