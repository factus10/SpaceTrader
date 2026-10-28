#!/usr/bin/env python3
"""
Converts an image to TS2068 Extended Color Mode band planes.

Replaces tools/ecm_preview.py, which duplicated this encoding and got one rule
wrong. This is a reference/testing converter; the production path is Retro Pixel
Converter at https://factus10.github.io/retro-pixel-converter/

Output is two 2048-byte planes for one screen band:

    pixels      -> $4000 + band*2048     1 bit per pixel, set = ink
    attributes  -> $6000 + band*2048     one byte per 8x1 strip

Byte offset within a band, for pixel row Y (0-63) and column X (0-255):

    offset = (Y & 7)*256 + (Y >> 3)*32 + (X >> 3)
    bit    = $80 >> (X & 7)

which is the canonical Spectrum display formula with the band bits removed.

THE CONSTRAINT THAT SHAPES THE OUTPUT: an attribute byte is

    FLASH(7) BRIGHT(6) PAPER(5:3) INK(2:0)

One BRIGHT bit, shared by ink and paper. So a cell cannot mix a normal-brightness
color with a bright one - it gets eight colors plus a brightness flag, not
fifteen. Black is the exception: it is (0,0,0) at either brightness, so it pairs
with anything.

Usage:
    python3 tools/png_to_ecm.py art/ossuary.png --out-dir build/ecm
    python3 tools/png_to_ecm.py art/*.png --out-dir build/ecm --preview --report
    python3 tools/png_to_ecm.py art/ossuary.png --dither bayer2 --preview
"""

import argparse
from itertools import combinations_with_replacement
from pathlib import Path

import numpy as np
from PIL import Image

WIDTH, BAND_HEIGHT, CELL = 256, 64, 8
BAND_SIZE = 2048
NORMAL, BRIGHT = 0xCD, 0xFF


def color_rgb(c: int, bright: int):
    """Spectrum color c (0-7) at the given brightness. bit0=blue bit1=red bit2=green."""
    v = BRIGHT if bright else NORMAL
    return (((c >> 1) & 1) * v, ((c >> 2) & 1) * v, (c & 1) * v)


# RGB for all 8 colors at each brightness, as two 8x3 tables
PAL = np.array([[color_rgb(c, b) for c in range(8)] for b in (0, 1)], dtype=np.int32)


def bayer_matrix(n: int):
    """Recursive Bayer ordered-dither matrix, values 0..n*n-1."""
    if n == 1:
        return np.zeros((1, 1), dtype=np.int32)
    h = bayer_matrix(n // 2)
    return np.block([[4 * h, 4 * h + 2],
                     [4 * h + 3, 4 * h + 1]])


DITHERS = {"none": None, "bayer2": 2, "bayer4": 4, "bayer8": 8}


def plane_offset(y: int, x0: int, full: bool) -> int:
    """Byte offset for pixel row y, column x0.

    A band plane drops the band bits, so the same 2048 bytes render at any band
    base. A full-screen plane keeps them and is 6144 bytes.
    """
    if full:
        return (y >> 6) * 2048 + (y & 7) * 256 + ((y >> 3) & 7) * 32 + (x0 >> 3)
    return (y & 7) * 256 + (y >> 3) * 32 + (x0 >> 3)


def encode_band(img: Image.Image, height: int = BAND_HEIGHT, dither: str = "none"):
    """Return (pixel_plane, attr_plane, clash_cells, total_cells).

    Dithering happens *after* the ink/paper pair is chosen, so it only ever
    alternates between the two colors the cell can actually hold. At 256x64 the
    dither pattern is the same size as the picture detail, so it stops reading as
    tone and starts reading as noise - 'none' or 'bayer2' is usually the right
    choice for a band image. Larger matrices give smoother tone at the cost of
    more high-frequency speckle.
    """
    if dither not in DITHERS:
        raise SystemExit(f"error: unknown dither {dither!r}, want one of "
                         f"{', '.join(DITHERS)}")
    n = DITHERS[dither]
    thresh = None
    if n:
        thresh = (bayer_matrix(n).astype(np.float64) + 0.5) / (n * n)
    src = np.array(img.convert("RGB").resize((WIDTH, height), Image.LANCZOS),
                   dtype=np.int32)

    full = height > BAND_HEIGHT
    size = 6144 if full else BAND_SIZE
    pix = bytearray(size)
    atr = bytearray(size)
    clash = 0
    pairs = list(combinations_with_replacement(range(8), 2))

    for y in range(height):
        for x0 in range(0, WIDTH, CELL):
            cell = src[y, x0:x0 + CELL]                     # 8 x 3

            best = None
            for b in (0, 1):
                # squared distance from each pixel to each of the 8 colors
                d = ((cell[:, None, :] - PAL[b][None, :, :]) ** 2).sum(-1)   # 8 x 8
                for ink, paper in pairs:
                    err = np.minimum(d[:, ink], d[:, paper]).sum()
                    if best is None or err < best[0]:
                        best = (err, b, ink, paper, d)

            _, b, ink, paper, d = best
            # a cell wanting more than two colors has lost detail
            if len(set(d.argmin(1).tolist())) > 2:
                clash += 1

            bits = 0
            if thresh is None or ink == paper:
                for i in range(CELL):
                    if d[i, ink] <= d[i, paper]:
                        bits |= 0x80 >> i
            else:
                # position of each pixel along the paper->ink axis, so the
                # dither only ever chooses between the two colors in this cell
                ca, cb = PAL[b][ink], PAL[b][paper]
                axis = ca - cb
                denom = float((axis * axis).sum()) or 1.0
                for i in range(CELL):
                    t = float(((cell[i] - cb) * axis).sum()) / denom
                    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
                    if t > thresh[y % n, (x0 + i) % n]:
                        bits |= 0x80 >> i
            off = plane_offset(y, x0, full)
            pix[off] = bits
            atr[off] = (b << 6) | (paper << 3) | ink

    return bytes(pix), bytes(atr), clash, height * (WIDTH // CELL)


def speckle(pix: bytes, atr: bytes) -> float:
    """Fraction of cells that read as dither noise rather than picture.

    A two-color cell whose eight pixels flip four or more times is a dither
    pattern, not an edge. At 256x64 that pattern is the same size as the detail
    it is meant to shade, so this is the number to watch when choosing a mode -
    'cells exact' cannot see it, being about color demand rather than pixels.
    """
    n = 0
    for i in range(len(pix)):
        a = atr[i]
        if a & 7 == (a >> 3) & 7:
            continue
        b = pix[i]
        if sum(((b >> k) & 1) != ((b >> (k - 1)) & 1) for k in range(1, 8)) >= 4:
            n += 1
    return n / len(pix)


def decode_preview(pix: bytes, atr: bytes, height: int, scale: int):
    """Render the planes back to RGB, so what you see is what the machine shows."""
    full = height > BAND_HEIGHT
    out = np.zeros((height, WIDTH, 3), dtype=np.uint8)
    for y in range(height):
        for x0 in range(0, WIDTH, CELL):
            off = plane_offset(y, x0, full)
            a, bits = atr[off], pix[off]
            b, paper, ink = (a >> 6) & 1, (a >> 3) & 7, a & 7
            ci, cp = color_rgb(ink, b), color_rgb(paper, b)
            for i in range(CELL):
                out[y, x0 + i] = ci if bits & (0x80 >> i) else cp
    im = Image.fromarray(out)
    return im.resize((WIDTH * scale, height * scale), Image.NEAREST) if scale > 1 else im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("build/ecm"))
    ap.add_argument("--band", type=int, default=0, choices=(0, 1, 2))
    ap.add_argument("--height", type=int, default=BAND_HEIGHT)
    ap.add_argument("--preview", action="store_true", help="also write a PNG preview")
    ap.add_argument("--scale", type=int, default=4, help="preview upscale, default 4")
    ap.add_argument("--dither", default="none", choices=list(DITHERS),
                    help="ordered dither applied within each cell; default none")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    for src in args.images:
        img = Image.open(src)
        w, h = img.size
        if abs(w / h - WIDTH / args.height) > 0.02:
            print(f"warning: {src.name} is {w}x{h} ({w/h:.2f}:1), "
                  f"wanted {WIDTH/args.height:.0f}:1 - it will be squashed")

        pix, atr, clash, total = encode_band(img, args.height, args.dither)

        stem = src.stem.replace("-", "")[:6]
        (args.out_dir / f"{stem}pix.bin").write_bytes(pix)
        (args.out_dir / f"{stem}atr.bin").write_bytes(atr)

        msg = (f"{src.name} -> {args.out_dir}/{stem}pix.bin + {stem}atr.bin "
               f"({len(pix)}+{len(atr)} bytes)")
        if args.report:
            msg += (f"   {100*(total-clash)/total:.1f}% cells exact"
                    f"   {100*speckle(pix, atr):.0f}% speckle")
        print(msg)

        if args.preview:
            p = args.out_dir / f"{src.stem}_ecm.png"
            decode_preview(pix, atr, args.height, args.scale).save(p)
            print(f"  preview {p}")


if __name__ == "__main__":
    main()
