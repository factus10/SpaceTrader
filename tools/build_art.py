#!/usr/bin/env python3
"""
Builds per-system band blocks for the game TAP from whatever art is available.

Two sources, and a converted TAP always wins:

  art/<system>.tap   Retro Pixel Converter output - a full-screen ECM image, two
                     6144-byte blocks. A 4:1 source letterboxed into the 4:3
                     screen lands in the MIDDLE third, so the picture is in band
                     1. That is free to lift: a band plane is position
                     independent, because the intra-band offset
                     (Y & 7)*256 + (Y >> 3)*32 + (X >> 3) is the same for all
                     three bands. Band 1's bytes render identically at band 0.

  art/<system>.png   4:1 source, converted here by png_to_ecm. This is the
                     reference path, not the production one - use it to preview
                     and to build test TAPs before converting for real.

Filenames map to systems by slug, so art/hollow-sky.png is system 7. A trailing
-N version suffix is stripped and the newest file wins, so coriolis-gate-2.png
supersedes coriolis-gate.png without renaming anything.

Outputs aNN.bin / pNN.bin, a 20-byte presence table, and the --code arguments
for append_code.py. The presence table is not optional: a mounted TAP loops, so
asking for a block that is not on the tape searches forever rather than failing,
and ON ERR cannot catch a hang.

Usage:
    python3 tools/build_art.py
    python3 tools/build_art.py --dither bayer2      # png path only
    python3 tools/build_art.py --list
    python3 tools/build_art.py --force              # ignore the mtime cache
"""

import re
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from slice_ecm_tap import load_pairs, TapError            # noqa: E402
from png_to_ecm import encode_band, speckle, DITHERS      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BAND_SIZE = 2048
BANDS = 3


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def visible_pixels(pix: bytes, atr: bytes, band: int) -> int:
    """Pixels that render as something other than black.

    Counting set bits is not enough: in a letterbox bar both ink and paper are
    black, so the bit pattern is arbitrary and a black band can outscore the
    picture.
    """
    lo, total = band * BAND_SIZE, 0
    for i in range(BAND_SIZE):
        a, bits = atr[lo + i], pix[lo + i]
        set_bits = bin(bits).count("1")
        if a & 7:
            total += set_bits
        if (a >> 3) & 7:
            total += 8 - set_bits
    return total


def from_tap(path: Path, band):
    pairs = {k: p for h, p, k in load_pairs(path) if k}
    if "pix" not in pairs or "atr" not in pairs:
        raise TapError("missing pixel or attribute block")
    if band is None:
        band = max(range(BANDS),
                   key=lambda b: visible_pixels(pairs["pix"], pairs["atr"], b))
    lo, hi = band * BAND_SIZE, (band + 1) * BAND_SIZE
    a, p = pairs["atr"][lo:hi], pairs["pix"][lo:hi]
    if len(a) != BAND_SIZE or len(p) != BAND_SIZE:
        raise TapError(f"band {band} is short")
    return a, p, f"tap band {band}"


def from_png(path: Path, dither: str):
    from PIL import Image
    im = Image.open(path)
    w, h = im.size
    warn = "" if abs(w / h - 4.0) < 0.02 else f" (WARNING {w}x{h} is not 4:1)"
    pix, atr, clash, total = encode_band(im, 64, dither)
    return atr, pix, (f"png {100*(total-clash)/total:.1f}% exact "
                      f"{100*speckle(pix, atr):.0f}% speckle{warn}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art-dir", type=Path, default=ROOT / "art")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "build" / "art")
    ap.add_argument("--band", type=int, choices=range(BANDS),
                    help="force the source band for TAP input")
    ap.add_argument("--dither", default="none", choices=list(DITHERS),
                    help="dither for PNG input; default none")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="reconvert even if the output is newer than the source")
    args = ap.parse_args()

    data = json.loads((ROOT / "data" / "systems.json").read_text())
    index = {slug(s["name"]): s["index"] for s in data["systems"]}
    names = {s["index"]: s["name"] for s in data["systems"]}
    n_sys = len(data["systems"])

    # a converted TAP beats a PNG; otherwise newest file wins
    src = {}
    for path in sorted(args.art_dir.glob("*")):
        if path.suffix not in (".tap", ".png"):
            continue
        base = re.sub(r"-\d+$", "", re.sub(r"[-_]?ecm$", "", path.stem))
        i = index.get(slug(base))
        if i is None:
            print(f"  {path.name:26} no system of that name", file=sys.stderr)
            continue
        cur = src.get(i)
        better = (cur is None
                  or (path.suffix == ".tap" and cur.suffix == ".png")
                  or (path.suffix == cur.suffix
                      and path.stat().st_mtime > cur.stat().st_mtime))
        if better:
            src[i] = path

    args.out_dir.mkdir(parents=True, exist_ok=True)
    code_args = []

    for i in sorted(src):
        path = src[i]
        ab, pb = args.out_dir / f"a{i:02d}.bin", args.out_dir / f"p{i:02d}.bin"
        cached = (not args.force and ab.exists() and pb.exists()
                  and ab.stat().st_mtime > path.stat().st_mtime)
        if args.list:
            print(f"  {i:2} {names[i]:14} {path.name}")
            continue
        if cached:
            note = "cached"
        else:
            try:
                a, p, note = (from_tap(path, args.band) if path.suffix == ".tap"
                              else from_png(path, args.dither))
            except TapError as e:
                print(f"  {i:2} {names[i]:14} skip {path.name}: {e}", file=sys.stderr)
                continue
            ab.write_bytes(a)
            pb.write_bytes(p)
        print(f"  {i:2} {names[i]:14} {path.name:24} {note}")
        code_args.append(f"{ab}:a{i:02d}:24576")
        code_args.append(f"{pb}:p{i:02d}:16384")

    if args.list:
        return

    have = {int(c.split(":a")[1][:2]) for c in code_args if ":a" in c}
    present = bytes(1 if i in have else 0 for i in range(1, n_sys + 1))
    (args.out_dir / "present.bin").write_bytes(present)
    (args.out_dir / "blocks.txt").write_text("\n".join(code_args) + "\n")
    print(f"\n  {len(have)}/{n_sys} systems have art -> "
          f"{len(code_args)} blocks, {len(code_args)*BAND_SIZE//1024} KB")


if __name__ == "__main__":
    main()
