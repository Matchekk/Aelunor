"""One-off: before/after sheet for refine_edges on dark background."""
from PIL import Image

DARK = (22, 18, 14, 255)

def on_dark(path):
    img = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", img.size, DARK)
    bg.alpha_composite(img)
    return bg

before = on_dark("badcut.png")
after = on_dark("badcut.clean.png")

# 3x zoom crops of the upper-left crescent horn edge.
box = (140, 60, 268, 188)
zoom_before = before.crop(box).resize((384, 384), Image.NEAREST)
zoom_after = after.crop(box).resize((384, 384), Image.NEAREST)

sheet = Image.new("RGBA", (1042, 916), (60, 50, 40, 255))
sheet.paste(before, (4, 4))
sheet.paste(after, (524, 4))
sheet.paste(zoom_before, (66, 524))
sheet.paste(zoom_after, (590, 524))
sheet.convert("RGB").save("refine-compare.png")
print("refine-compare.png written (left: badcut, right: cleaned)")
