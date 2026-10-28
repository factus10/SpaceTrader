#!/usr/bin/env python3
"""
Draws the game's 8x8 font and writes it as a 768-byte CHARS block.

96 glyphs, codes 32-127, in the Sinclair layout - which puts a pound sign at
code 96 where ASCII has a backtick. That layout is shared by the ZX Spectrum and
the TS2068, so the result works on either.

DESIGNED FOR THIS GAME'S CONSTRAINT: pixel row 0 of every cell is left empty, so
the hairline rule on row 8 has a clear line to sit on. Caps occupy rows 1-6,
x-height 3-6, descenders row 7. An existing font has to be shifted down to
achieve this, which costs it a row of descenders; drawing to the constraint
costs nothing.

Glyphs are defined below as six or seven rows of '#' and '.', top row first,
starting at cell row 1. Edit them here - they are meant to be legible.

Usage:
    python3 tools/make_font.py            # writes art/ui/font.bin
    python3 tools/make_font.py --sheet    # also a PNG proof sheet
"""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Each entry: rows starting at cell row 1. Six rows = cap height, a seventh
# row is the descender line (cell row 7).
G = {
" ": "",
"!": ".#..\n.#..\n.#..\n.#..\n....\n.#..",
'"': "#.#.\n#.#.\n....\n....\n....\n....",
"#": ".#.#.\n#####\n.#.#.\n#####\n.#.#.\n.....",
"$": "..#..\n.####\n#.#..\n.###.\n..#.#\n####.\n..#..",
"%": "##..#\n##.#.\n..#..\n.#.##\n#..##\n.....",
"&": ".##..\n#..#.\n.#...\n#.#.#\n#..#.\n.##.#",
"'": ".#..\n.#..\n....\n....\n....\n....",
"(": "..#.\n.#..\n.#..\n.#..\n.#..\n..#.",
")": ".#..\n..#.\n..#.\n..#.\n..#.\n.#..",
"*": ".....\n#.#.#\n.###.\n#.#.#\n.....\n.....",
"+": ".....\n..#..\n.###.\n..#..\n.....\n.....",
",": "....\n....\n....\n....\n.##.\n.##.\n.#..",
"-": ".....\n.....\n.###.\n.....\n.....\n.....",
".": "....\n....\n....\n....\n.##.\n.##.",
"/": "....#\n...#.\n..#..\n.#...\n#....\n.....",
"0": ".###.\n#..##\n#.#.#\n##..#\n#...#\n.###.",
"1": "..#..\n.##..\n..#..\n..#..\n..#..\n.###.",
"2": ".###.\n#...#\n...#.\n..#..\n.#...\n#####",
"3": "####.\n....#\n.###.\n....#\n#...#\n.###.",
"4": "...#.\n..##.\n.#.#.\n#..#.\n#####\n...#.",
"5": "#####\n#....\n####.\n....#\n#...#\n.###.",
"6": ".###.\n#....\n####.\n#...#\n#...#\n.###.",
"7": "#####\n....#\n...#.\n..#..\n..#..\n..#..",
"8": ".###.\n#...#\n.###.\n#...#\n#...#\n.###.",
"9": ".###.\n#...#\n#...#\n.####\n....#\n.###.",
":": "....\n.##.\n.##.\n....\n.##.\n.##.",
";": "....\n.##.\n.##.\n....\n.##.\n.##.\n.#..",
"<": "...#.\n..#..\n.#...\n..#..\n...#.\n.....",
"=": ".....\n.###.\n.....\n.###.\n.....\n.....",
">": ".#...\n..#..\n...#.\n..#..\n.#...\n.....",
"?": ".###.\n#...#\n...#.\n..#..\n.....\n..#..",
"@": ".###.\n#...#\n#.##.\n#.#..\n#....\n.###.",
"A": ".###.\n#...#\n#...#\n#####\n#...#\n#...#",
"B": "####.\n#...#\n####.\n#...#\n#...#\n####.",
"C": ".###.\n#...#\n#....\n#....\n#...#\n.###.",
"D": "####.\n#...#\n#...#\n#...#\n#...#\n####.",
"E": "#####\n#....\n####.\n#....\n#....\n#####",
"F": "#####\n#....\n####.\n#....\n#....\n#....",
"G": ".###.\n#...#\n#....\n#..##\n#...#\n.###.",
"H": "#...#\n#...#\n#####\n#...#\n#...#\n#...#",
"I": ".###.\n..#..\n..#..\n..#..\n..#..\n.###.",
"J": "...##\n....#\n....#\n....#\n#...#\n.###.",
"K": "#...#\n#..#.\n###..\n#..#.\n#...#\n#...#",
"L": "#....\n#....\n#....\n#....\n#....\n#####",
"M": "#...#\n##.##\n#.#.#\n#...#\n#...#\n#...#",
"N": "#...#\n##..#\n#.#.#\n#..##\n#...#\n#...#",
"O": ".###.\n#...#\n#...#\n#...#\n#...#\n.###.",
"P": "####.\n#...#\n####.\n#....\n#....\n#....",
"Q": ".###.\n#...#\n#...#\n#.#.#\n#..#.\n.##.#",
"R": "####.\n#...#\n####.\n#..#.\n#...#\n#...#",
"S": ".####\n#....\n.###.\n....#\n#...#\n.###.",
"T": "#####\n..#..\n..#..\n..#..\n..#..\n..#..",
"U": "#...#\n#...#\n#...#\n#...#\n#...#\n.###.",
"V": "#...#\n#...#\n#...#\n#...#\n.#.#.\n..#..",
"W": "#...#\n#...#\n#...#\n#.#.#\n##.##\n#...#",
"X": "#...#\n.#.#.\n..#..\n..#..\n.#.#.\n#...#",
"Y": "#...#\n.#.#.\n..#..\n..#..\n..#..\n..#..",
"Z": "#####\n....#\n...#.\n..#..\n.#...\n#####",
"[": ".###\n.#..\n.#..\n.#..\n.#..\n.###",
"\\": "#....\n.#...\n..#..\n...#.\n....#\n.....",
"]": "###.\n..#.\n..#.\n..#.\n..#.\n###.",
"^": "..#..\n.#.#.\n#...#\n.....\n.....\n.....",
"_": ".....\n.....\n.....\n.....\n.....\n.....\n#####",
"£": "..##.\n.#..#\n.#...\n####.\n.#...\n#####",
"a": ".....\n.....\n.###.\n#..#.\n#..#.\n.##.#",
"b": "#....\n#....\n####.\n#...#\n#...#\n####.",
"c": ".....\n.....\n.###.\n#....\n#....\n.###.",
"d": "....#\n....#\n.####\n#...#\n#...#\n.####",
"e": ".....\n.###.\n#..#.\n###..\n#....\n.###.",
"f": "..##.\n.#...\n####.\n.#...\n.#...\n.#...",
"g": ".....\n.....\n.####\n#...#\n.####\n....#\n.###.",
"h": "#....\n#....\n####.\n#...#\n#...#\n#...#",
"i": "..#..\n.....\n.##..\n..#..\n..#..\n.###.",
"j": "...#.\n.....\n..##.\n...#.\n...#.\n#..#.\n.##..",
"k": "#....\n#..#.\n#.#..\n##...\n#.#..\n#..#.",
"l": ".##..\n..#..\n..#..\n..#..\n..#..\n.###.",
"m": ".....\n.....\n##.#.\n#.#.#\n#.#.#\n#...#",
"n": ".....\n.....\n####.\n#...#\n#...#\n#...#",
"o": ".....\n.....\n.###.\n#...#\n#...#\n.###.",
"p": ".....\n.....\n####.\n#...#\n####.\n#....\n#....",
"q": ".....\n.....\n.####\n#...#\n.####\n....#\n....#",
"r": ".....\n.....\n#.##.\n##...\n#....\n#....",
"s": ".....\n.....\n.####\n.###.\n...##\n####.",
"t": ".#...\n.#...\n####.\n.#...\n.#...\n..##.",
"u": ".....\n.....\n#...#\n#...#\n#...#\n.####",
"v": ".....\n.....\n#...#\n#...#\n.#.#.\n..#..",
"w": ".....\n.....\n#...#\n#.#.#\n#.#.#\n.#.#.",
"x": ".....\n.....\n#...#\n.#.#.\n.#.#.\n#...#",
"y": ".....\n.....\n#...#\n#...#\n.####\n....#\n.###.",
"z": ".....\n.....\n#####\n..##.\n.#...\n#####",
"{": "..##.\n..#..\n.##..\n..#..\n..#..\n..##.",
"|": "..#..\n..#..\n..#..\n..#..\n..#..\n..#..",
"}": ".##..\n..#..\n..##.\n..#..\n..#..\n.##..",
"~": ".....\n.##.#\n#..##\n.....\n.....\n.....",
"©": ".###.\n#...#\n#.##.\n#.#..\n#...#\n.###.",
}


def build():
    out = bytearray(768)
    missing = []
    for code in range(32, 128):
        ch = "£" if code == 96 else ("©" if code == 127 else chr(code))
        spec = G.get(ch)
        if spec is None:
            missing.append((code, ch))
            continue
        rows = spec.split("\n") if spec else []
        for n, row in enumerate(rows):
            if n > 6:
                raise SystemExit(f"glyph {ch!r} has more than 7 rows")
            bits = 0
            for x, c in enumerate(row[:8]):
                if c == "#":
                    bits |= 0x80 >> x
            out[(code - 32) * 8 + 1 + n] = bits      # row 0 stays empty
    return bytes(out), missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", action="store_true", help="also write a proof sheet PNG")
    ap.add_argument("-o", "--out", type=Path, default=ROOT / "art" / "ui" / "font.bin")
    args = ap.parse_args()

    font, missing = build()
    if missing:
        raise SystemExit(f"error: no glyph drawn for {missing}")

    row0 = sum(1 for g in range(96) if font[g * 8])
    if row0:
        raise SystemExit(f"error: {row0} glyphs touch pixel row 0, which the rule needs")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(font)
    blank = [32 + g for g in range(96) if not any(font[g * 8:g * 8 + 8])]
    print(f"wrote {args.out} ({len(font)} bytes)")
    print(f"  pixel row 0 clear on all 96 glyphs")
    print(f"  blank glyphs: {[chr(c) for c in blank]} (space only, expected)")

    if args.sheet:
        from PIL import Image
        S, COLS = 6, 16
        im = Image.new("RGB", (COLS * 8 * S, 6 * 8 * S), (0, 0, 0))
        px = im.load()
        for g in range(96):
            gx, gy = (g % COLS) * 8, (g // COLS) * 8
            for r in range(8):
                b = font[g * 8 + r]
                for c in range(8):
                    if b & (0x80 >> c):
                        for a in range(S):
                            for d in range(S):
                                px[(gx + c) * S + a, (gy + r) * S + d] = (255, 255, 255)
        p = ROOT / "build" / "font_sheet.png"
        p.parent.mkdir(exist_ok=True)
        im.save(p)
        print(f"  proof sheet {p}")


if __name__ == "__main__":
    main()
