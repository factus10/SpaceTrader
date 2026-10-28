#!/usr/bin/env python3
"""
Composes the title screen at art/ui/title.png.

256x192, converted to full-screen ECM by the build.

Laid out after the Classic Traveller little black books: black field, white
type, one thin red rule. That is also close to ideal for the hardware - a
full-width horizontal band is a single attribute per cell with no color clash,
and a black field costs nothing at all.

Text is drawn with PIL's default font and scaled with NEAREST so the letters
stay hard pixel shapes. Word spacing is doubled because the default font's
space is about two pixels at 1x, which reads as no gap once the image is down
at 256 wide.

The build blacks pixel rows 176-191 afterwards - rows 22-23 are BASIC's lower
screen, whose pixels the game cannot clear, so anything left there would show
through under the text attributes.

Usage:
    python3 tools/make_title.py                  # black field, LBB style
    python3 tools/make_title.py background.png   # with art in the lower half
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 256, 192
BAND_Y, BAND_H = 92, 3          # red rule: position and thickness
RED = (255, 0, 0)
WHITE = (255, 255, 255)


def blocky(text, scale, color):
    """Render text as hard pixels in exactly one color.

    PIL antialiases, and a mid-grey edge pixel quantizes to white-at-normal-
    brightness rather than bright white - which is why the scaled-up title came
    out grey. Threshold first, then scale with NEAREST.
    """
    f = ImageFont.load_default()
    tmp = Image.new("L", (400, 20), 0)
    ImageDraw.Draw(tmp).text((0, 2), text, font=f, fill=255)
    tmp = tmp.point(lambda v: 255 if v > 96 else 0)
    c = tmp.crop(tmp.getbbox() or (0, 0, 1, 1))
    c = c.resize((c.width * scale, c.height * scale), Image.NEAREST)
    out = Image.new("RGB", c.size, (0, 0, 0))
    out.paste(Image.new("RGB", c.size, color), mask=c)
    return out


def main():
    out = Image.new("RGB", (W, H), (0, 0, 0))

    if len(sys.argv) > 1:
        bg = Image.open(sys.argv[1]).convert("RGB").resize((W, 96), Image.LANCZOS)
        out.paste(bg, (0, 96))

    ImageDraw.Draw(out).rectangle([0, BAND_Y, W - 1, BAND_Y + BAND_H - 1], fill=RED)

    for text, scale, color, y in [
        ("SPACE  TRADER", 3, WHITE, 52),
        ("A  TRAVELLER  GAME  FOR  THE  TS2068", 1, WHITE, 104),
        ("PRESS  ANY  KEY", 1, WHITE, 160),
    ]:
        t = blocky(text, scale, color)
        if t.width > W:
            print(f"warning: {text!r} is {t.width}px, wider than the {W}px screen")
        out.paste(t, ((W - t.width) // 2, y))

    dest = ROOT / "art" / "ui" / "title.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
