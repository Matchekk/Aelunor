"""Edge refinement for hand-cut PNGs (Paint.NET magic-wand cutouts etc.).

Removes the rough gray halo that manual background removal leaves behind:

1. Reconstructs a plausible pre-cutout image by compositing the PNG back
   onto the removed background color (``--bg``, default white; ``auto``
   estimates it from the image itself).
2. Builds a trimap automatically from the existing alpha channel: pixels
   well inside the shape are sure-foreground, pixels well outside are
   sure-background, and a band around the edge is left "unknown".
3. Runs closed-form alpha matting (PyMatting, MIT) over the unknown band,
   which recovers smooth anti-aliased alpha from the image colors. The
   matting only runs on the bounding box of the unknown band, so large
   images with small subjects stay fast.
4. Runs multilevel foreground estimation, which removes the background
   color that contaminates the edge pixels (the gray fringe).
5. Measures the remaining background admixture at the edge (fringe score)
   and automatically retries with a wider band if the halo survived.

Usage:
    python scripts/refine_edges.py <file...> [--bg white|auto|"#rrggbb"]
        [--band N] [--out DIR] [--replace] [--compare] [--no-retry]

Output: <name>.clean.png next to the input (or --out DIR / --replace);
--compare additionally writes <name>.compare.png (before/after on a dark
backdrop with a zoom on the previously worst edge region).

No ML models, no downloads — PyMatting is purely numerical
(pip install -r requirements.txt).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from pymatting import estimate_alpha_cf, estimate_foreground_ml
from scipy import ndimage

MAX_BAND = 9
DARK = (22, 18, 14, 255)


def parse_color(value: str) -> np.ndarray:
    if value == "white":
        return np.array([1.0, 1.0, 1.0])
    if value.startswith("#") and len(value) == 7:
        return np.array([int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)])
    raise argparse.ArgumentTypeError(f"invalid color: {value!r} (use white, auto or #rrggbb)")


def nearest_interior_colors(rgb: np.ndarray, interior: np.ndarray) -> np.ndarray:
    """For every pixel, the color of the nearest sure-interior pixel."""
    indices = ndimage.distance_transform_edt(
        ~interior, return_distances=False, return_indices=True
    )
    return rgb[tuple(indices)]


def estimate_background(rgb: np.ndarray, alpha: np.ndarray, solid: np.ndarray) -> tuple[np.ndarray, str]:
    """Estimate the removed background color.

    Strategy 1: many editors (Paint.NET among them) keep the original RGB
    under fully transparent pixels — if those colors near the edge carry
    information, their median IS the removed background.

    Strategy 2: alternating least squares over the contaminated edge ring
    using the mixing model c = a*f + (1-a)*bg with f taken from the nearest
    sure-interior pixel.
    """
    near_edge = (~solid) & ndimage.binary_dilation(solid, iterations=4)
    probe = rgb[near_edge & (alpha < 0.01)]
    if len(probe) > 100:
        # Editors that zero out hidden colors leave exactly-black pixels —
        # those carry no information about the removed background.
        zeroed = (probe == 0).all(axis=1).mean()
        if zeroed < 0.3:
            return np.median(probe, axis=0), "transparent-pixel probe"

    ring = solid & ~ndimage.binary_erosion(solid, iterations=2)
    interior = ndimage.binary_erosion(solid, iterations=4)
    if ring.any() and interior.any():
        f = nearest_interior_colors(rgb, interior)[ring]
        c = rgb[ring]
        bg = np.ones(3)
        for _ in range(8):
            direction = bg - f
            denom = np.maximum((direction * direction).sum(axis=1), 1e-9)
            mix = np.clip(((c - f) * direction).sum(axis=1) / denom, 0.0, 1.0)
            usable = mix > 0.25
            if not usable.any():
                break
            bg_estimates = f[usable] + (c[usable] - f[usable]) / mix[usable, None]
            bg = np.clip(np.median(bg_estimates, axis=0), 0.0, 1.0)
        return bg, "least-squares"

    return np.ones(3), "fallback white"


def fringe_score(rgb: np.ndarray, alpha: np.ndarray, background: np.ndarray) -> float:
    """Average background admixture (0..1) of the outermost opaque edge ring."""
    solid = alpha > 0.5
    if not solid.any() or solid.all():
        return 0.0
    ring = solid & ~ndimage.binary_erosion(solid, iterations=2)
    interior = ndimage.binary_erosion(solid, iterations=4)
    if not ring.any() or not interior.any():
        return 0.0
    f = nearest_interior_colors(rgb, interior)[ring]
    c = rgb[ring]
    direction = background - f
    denom = np.maximum((direction * direction).sum(axis=1), 1e-9)
    mix = np.clip(((c - f) * direction).sum(axis=1) / denom, 0.0, 1.0)
    return float(mix.mean())


def worst_fringe_location(rgb: np.ndarray, alpha: np.ndarray, background: np.ndarray) -> tuple[int, int]:
    """Center of the edge region with the strongest background admixture."""
    solid = alpha > 0.5
    ring = solid & ~ndimage.binary_erosion(solid, iterations=2)
    interior = ndimage.binary_erosion(solid, iterations=4)
    if not ring.any() or not interior.any():
        return rgb.shape[0] // 2, rgb.shape[1] // 2
    f = nearest_interior_colors(rgb, interior)
    direction = background - f
    denom = np.maximum((direction * direction).sum(axis=-1), 1e-9)
    mix = np.clip(((rgb - f) * direction).sum(axis=-1) / denom, 0.0, 1.0)
    mix[~ring] = 0.0
    # Smooth so we find a cluster of fringe, not a lone noisy pixel.
    smoothed = ndimage.uniform_filter(mix, size=15)
    y, x = np.unravel_index(np.argmax(smoothed), smoothed.shape)
    return int(y), int(x)


def matting_pass(
    composite: np.ndarray, alpha: np.ndarray, solid: np.ndarray, band: int
) -> tuple[np.ndarray, np.ndarray]:
    """One matting + decontamination pass, restricted to the edge bounding box."""
    sure_fg = ndimage.binary_erosion(solid, iterations=band)
    sure_bg = ~ndimage.binary_dilation(solid, iterations=band)
    trimap = np.full(alpha.shape, 0.5)
    trimap[sure_fg] = 1.0
    trimap[sure_bg] = 0.0

    unknown = (trimap > 0.0) & (trimap < 1.0)
    ys, xs = np.where(unknown)
    pad = 24
    y0, y1 = max(0, ys.min() - pad), min(alpha.shape[0], ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(alpha.shape[1], xs.max() + pad + 1)

    crop_alpha = estimate_alpha_cf(composite[y0:y1, x0:x1], trimap[y0:y1, x0:x1])
    crop_fg = estimate_foreground_ml(composite[y0:y1, x0:x1], crop_alpha)

    new_alpha = trimap.copy()
    new_alpha[y0:y1, x0:x1] = crop_alpha
    foreground = composite.copy()
    foreground[y0:y1, x0:x1] = crop_fg
    return foreground, new_alpha


def write_compare_sheet(original: Image.Image, cleaned: Image.Image, focus: tuple[int, int], target: Path) -> None:
    def on_dark(img: Image.Image) -> Image.Image:
        base = Image.new("RGBA", img.size, DARK)
        base.alpha_composite(img.convert("RGBA"))
        return base

    before, after = on_dark(original), on_dark(cleaned)
    width, height = before.size
    crop_size = max(96, min(width, height) // 4)
    y, x = focus
    x0 = min(max(0, x - crop_size // 2), width - crop_size)
    y0 = min(max(0, y - crop_size // 2), height - crop_size)
    box = (x0, y0, x0 + crop_size, y0 + crop_size)
    zoom = (384, 384)
    zoom_before = before.crop(box).resize(zoom, Image.NEAREST)
    zoom_after = after.crop(box).resize(zoom, Image.NEAREST)

    gap = 8
    sheet_w = max(width * 2 + gap * 3, zoom[0] * 2 + gap * 3)
    sheet = Image.new("RGBA", (sheet_w, height + zoom[1] + gap * 3), (60, 50, 40, 255))
    sheet.paste(before, (gap, gap))
    sheet.paste(after, (width + gap * 2, gap))
    zoom_x = (sheet_w - zoom[0] * 2 - gap) // 2
    sheet.paste(zoom_before, (zoom_x, height + gap * 2))
    sheet.paste(zoom_after, (zoom_x + zoom[0] + gap, height + gap * 2))
    sheet.convert("RGB").save(target)


def refine(path: Path, args: argparse.Namespace) -> Path:
    original = Image.open(path).convert("RGBA")
    data = np.asarray(original, dtype=np.float64) / 255.0
    rgb, alpha = data[..., :3], data[..., 3]

    solid = alpha > 0.5
    if not solid.any() or solid.all():
        raise SystemExit(f"{path}: image has no transparency boundary to refine")

    if args.bg == "auto":
        background, source = estimate_background(rgb, alpha, solid)
    else:
        background, source = parse_color(args.bg), "user"

    composite = rgb * alpha[..., None] + background * (1.0 - alpha[..., None])
    score_before = fringe_score(rgb, alpha, background)
    focus = worst_fringe_location(rgb, alpha, background)

    band = args.band
    while True:
        foreground, new_alpha = matting_pass(composite, alpha, solid, band)
        score_after = fringe_score(foreground, new_alpha, background)
        good_enough = score_after <= max(0.06, 0.4 * score_before)
        if good_enough or args.no_retry or band + 2 > MAX_BAND:
            break
        band += 2
        print(f"[refine]   halo persists (score {score_after:.3f}), retrying with --band {band}")

    result = np.dstack([foreground, new_alpha])
    result_img = Image.fromarray(
        (np.clip(result, 0.0, 1.0) * 255).round().astype(np.uint8), "RGBA"
    )

    if args.replace:
        target = path
    else:
        directory = Path(args.out) if args.out else path.parent
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{path.stem}.clean.png"
    result_img.save(target)

    bg_hex = "#" + "".join(f"{int(c * 255):02x}" for c in background)
    print(
        f"[refine] {path} -> {target}\n"
        f"[refine]   bg {bg_hex} ({source}), band {band}, "
        f"fringe {score_before:.3f} -> {score_after:.3f}"
    )

    if args.compare:
        compare_target = target.with_name(f"{path.stem}.compare.png")
        write_compare_sheet(original, result_img, focus, compare_target)
        print(f"[refine]   compare sheet -> {compare_target}")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument(
        "--bg",
        default="white",
        help="removed background color: white (default), auto, or #rrggbb",
    )
    parser.add_argument(
        "--band",
        type=int,
        default=3,
        help="unknown-band radius in px around the edge (default 3; raise for rougher cuts)",
    )
    parser.add_argument("--out", help="output directory")
    parser.add_argument("--replace", action="store_true", help="overwrite input files")
    parser.add_argument(
        "--compare", action="store_true", help="write a before/after comparison sheet"
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="disable automatic retry with a wider band when the halo persists",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    for path in args.files:
        if not path.exists():
            print(f"skip (not found): {path}", file=sys.stderr)
            continue
        refine(path, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
