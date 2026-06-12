"""One-off: before/after sheet for the real logo on dark background."""
from PIL import Image

DARK = (22, 18, 14, 255)

def on_dark(path):
    img = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", img.size, DARK)
    bg.alpha_composite(img)
    return bg

before = on_dark("../../../ui/public/brand/aelunor-icon-512x512.png")
after = on_dark("aelunor-icon-512x512.clean.png")

# 3x zoom on the upper-left crescent horn edge.
box = (140, 60, 268, 188)
zoom_before = before.crop(box).resize((384, 384), Image.NEAREST)
zoom_after = after.crop(box).resize((384, 384), Image.NEAREST)

sheet = Image.new("RGBA", (1042, 916), (60, 50, 40, 255))
sheet.paste(before, (4, 4))
sheet.paste(after, (524, 4))
sheet.paste(zoom_before, (66, 524))
sheet.paste(zoom_after, (590, 524))
sheet.convert("RGB").save("logo-refine-compare.png")
print("logo-refine-compare.png written (left: original, right: defringed)")
