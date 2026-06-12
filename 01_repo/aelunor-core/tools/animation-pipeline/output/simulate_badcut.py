"""One-off: simulate a Paint.NET magic-wand cutout with gray fringe."""
import numpy as np
from PIL import Image
from scipy import ndimage

src = np.asarray(
    Image.open("../../../ui/public/brand/aelunor-icon-512x512.png").convert("RGBA"),
    dtype=np.float64,
) / 255.0

# Flatten onto white (the "photo" before background removal).
flat = src[..., :3] * src[..., 3:] + 1.0 * (1.0 - src[..., 3:])

# Magic wand from the corners: contiguous near-white pixels become transparent.
near_white = np.linalg.norm(flat - 1.0, axis=-1) < 0.22
labels, _ = ndimage.label(near_white)
border_labels = set(labels[0, :]) | set(labels[-1, :]) | set(labels[:, 0]) | set(labels[:, -1])
border_labels.discard(0)
removed = np.isin(labels, list(border_labels))

out = np.dstack([flat, (~removed).astype(np.float64)])
Image.fromarray((out * 255).round().astype(np.uint8), "RGBA").save("badcut.png")
print("badcut.png written")
