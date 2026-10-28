#!/usr/bin/env python3
"""
Composes the manual's screenshots from the game's own data.

These are not emulator captures. They are built from the actual font bytes in
art/ui/font.bin, the actual band planes in build/art/, and the layout constants
taken from src/spacetrader.bas, then put through the same attribute rules the
hardware applies. Market prices use the game's own formula at zero variance, so
the output is deterministic.

Run tools/build_game.sh first, so build/art/ and build/title/ exist.

Usage:
    python3 tools/render_screens.py
"""
import sys, json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "manual" / "images"
FONT = (ROOT / "art/ui/font.bin").read_bytes()

NORMAL, BRIGHT = 0xCD, 0xFF
def rgb(c, b):
    v = BRIGHT if b else NORMAL
    return (((c >> 1) & 1) * v, ((c >> 2) & 1) * v, (c & 1) * v)

def off(y, x):                       # canonical display offset
    return ((y & 0xC0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2) | (x >> 3)

class Screen:
    def __init__(s):
        s.pix = bytearray(6144); s.atr = bytearray(6144)
    def band(s, idx):                # art into rows 0-7
        a = (ROOT / f"build/art/a{idx:02d}.bin").read_bytes()
        p = (ROOT / f"build/art/p{idx:02d}.bin").read_bytes()
        for y in range(64):
            for x in range(0, 256, 8):
                src = (y & 7) * 256 + (y >> 3) * 32 + (x >> 3)
                s.pix[off(y, x)] = p[src]; s.atr[off(y, x)] = a[src]
    def fill_attr(s, r0, r1, v):
        for y in range(r0 * 8, (r1 + 1) * 8):
            for x in range(0, 256, 8): s.atr[off(y, x)] = v
    def row_attr(s, r, v):  s.fill_attr(r, r, v)
    def line_attr(s, r, line, v):
        for x in range(0, 256, 8): s.atr[off(r * 8 + line, x)] = v
    def cell_attr(s, r, c, v):
        for line in range(8): s.atr[off(r * 8 + line, c * 8)] = v
    def text(s, r, c, txt):
        for n, ch in enumerate(txt):
            if c + n > 31: break
            g = FONT[(ord(ch) - 32) * 8:(ord(ch) - 32) * 8 + 8]
            for line in range(8):
                s.pix[off(r * 8 + line, (c + n) * 8)] = g[line]
    def right(s, r, end, val):       # right-align ending at column `end`
        t = str(val); s.text(r, end - len(t) + 1, t)
    def save(s, name):
        im = Image.new("RGB", (256, 192), (0, 0, 0)); px = im.load()
        for y in range(192):
            for x0 in range(0, 256, 8):
                o = off(y, x0); a = s.atr[o]; bits = s.pix[o]
                b, paper, ink = (a >> 6) & 1, (a >> 3) & 7, a & 7
                ci, cp = rgb(ink, b), rgb(paper, b)
                for i in range(8):
                    px[x0 + i, y] = ci if bits & (0x80 >> i) else cp
        im = im.resize((512, 384), Image.NEAREST)
        im.save(OUT / f"{name}.png"); print(f"  {name}.png")

TEXT, HEAD, COL, RULE, KEY, ALERT, INV = 71, 70, 69, 80, 70, 66, 120

def chrome(s, header, hcol=HEAD):
    s.fill_attr(8, 23, TEXT)
    s.row_attr(8, hcol)
    s.line_attr(8, 0, RULE)
    s.text(8, 0, header)

def market():
    sysj = json.loads((ROOT / "data/systems.json").read_text())
    sy = sysj["systems"][0]; goods = sysj["goods"]
    s = Screen(); s.band(1); chrome(s, "CORIOLIS GATE")
    s.text(8, 22, "TL15 LAW 8")
    s.text(9, 0, "CARGO 0 OF 20 TONS")
    s.text(10, 0, "  GOOD        PRICE ST  HELD"); s.row_attr(10, COL)
    pm = 10 - int(sy["pop"] * 20 / 15); tm = 10 - int(sy["tl"] * 20 / 15)
    for i, g in enumerate(goods, 1):
        st = -30 if g["abbr"] in sy["exports"] else (40 if g["abbr"] in sy["imports"] else 0)
        price = max(1, int(g["base_price"] * (100 + st + pm + tm) / 100))
        tag = "EX" if st < 0 else ("IM" if st > 0 else "--")
        r = 10 + i
        s.text(r, 0, str(i)); s.text(r, 2, g["short"])
        s.right(r, 18, price); s.text(r, 20, tag); s.right(r, 27, 0)
        if g["law_threshold"] < sy["law"]: s.text(r, 29, "!")
    s.line_attr(19, 7, RULE)
    s.text(20, 0, "BUY SELL JUMP PORT")
    for c in (0, 4, 9, 14): s.cell_attr(20, c, KEY)
    s.text(21, 0, "CR 1000 FUEL 8 HULL 8 HEAT 0")
    s.text(22, 0, "COMMAND?")
    s.save("market")

def jump():
    s = Screen(); s.band(1); chrome(s, "JUMP FROM")
    s.text(8, 10, "CORIOLIS GATE")
    for n, (nm, f) in enumerate([("MERIDIAN", 2), ("VERITY", 2), ("ALDEBAR PRIME", 1),
                                 ("PELLUCID", 2)], 1):
        s.text(9 + n, 0, str(n)); s.text(9 + n, 2, nm); s.text(9 + n, 16, f"F{f}")
    s.line_attr(19, 7, RULE)
    s.text(20, 0, "SELECT 1-4 OR C)ANCEL")
    s.text(21, 0, "CR 1000 FUEL 8 HULL 8 HEAT 0")
    s.save("jump")

def port():
    s = Screen(); s.band(1); chrome(s, "BEOWULF")
    s.text(10, 2, "FUEL 6 OF 8    10 CR")
    s.text(11, 2, "HULL 7 OF 8    40 CR")
    s.text(12, 2, "DEBT 17600")
    s.text(13, 2, "DUE IN 5 JUMPS")
    s.text(14, 2, "FUEL  HULL  ALL FUEL")
    s.text(15, 2, "LICENSES  MORTGAGE")
    s.text(16, 2, "X BACK TO MARKET")
    for c in (2, 8, 14): s.cell_attr(14, c, KEY)
    for c in (2, 12): s.cell_attr(15, c, KEY)
    s.cell_attr(16, 2, KEY)
    s.text(21, 0, "CR 2480 FUEL 6 HULL 7 HEAT 4")
    s.save("port")

def customs():
    s = Screen(); s.band(1); chrome(s, "CUSTOMS INSPECTION", ALERT)
    s.text(11, 2, "CONTRABAND FOUND")
    s.text(12, 2, "6 TONS RESTRICTED HERE")
    s.text(14, 2, "FINE 240 CR")
    s.text(17, 2, "COMPLY     BRIBE")
    s.text(18, 2, "SURRENDER  RESIST")
    for r in (17, 18):
        for c in (2, 13): s.cell_attr(r, c, KEY)
    s.text(21, 0, "CR 2480 FUEL 5 HULL 7 HEAT 6")
    s.save("customs")

def combat():
    s = Screen(); s.band(14); chrome(s, "PIRATE CORVETTE CLOSING", ALERT)
    s.text(11, 2, "THEIR HULL 6")
    s.text(12, 2, "YOUR HULL  7")
    s.text(14, 2, "CARGO AT RISK 18 TONS")
    s.text(17, 2, "EVADE      FIGHT")
    s.text(18, 2, "BRIBE      RUN")
    for r in (17, 18):
        for c in (2, 13): s.cell_attr(r, c, KEY)
    s.text(21, 0, "CR 1980 FUEL 4 HULL 7 HEAT 9")
    s.save("combat")

def naming():
    s = Screen()
    s.fill_attr(8, 23, TEXT)
    s.text(11, 2, "NAME YOUR FREE TRADER")
    s.text(13, 2, "ENTER ALONE FOR BEOWULF")
    s.text(22, 0, "Beowulf")
    s.save("naming")

def title():
    s = Screen()
    p = (ROOT / "build/title/titlepix.bin").read_bytes()
    a = (ROOT / "build/title/titleatr.bin").read_bytes()
    s.pix = bytearray(p); s.atr = bytearray(a)
    s.save("title")

OUT.mkdir(parents=True, exist_ok=True)
title(); naming(); market(); jump(); port(); customs(); combat()
