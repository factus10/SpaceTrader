#!/usr/bin/env python3
"""
Verifies the art block names in the TAP match exactly what the BASIC constructs.

This guards against the nastiest failure mode in the single-TAP design. Emulators
and the TS-Pico treat a mounted TAP as an endless loop, so block order does not
matter - but a name that is not on the tape is never reported as an error. The
2068 simply searches forever. `ON ERR` cannot catch a hang.

So the game consults a presence table before naming a block, and this checks the
two sides agree:

    BASIC builds   "a" + STR$ cs zero-padded to 2   ->  a01 .. a20
                   "p" + STR$ cs zero-padded to 2   ->  p01 .. p20
    presence table stdata.bin[120 + cs - 1]         ->  0 or 1

Every system flagged present must have both blocks, spelled exactly. Anything
else is a hang waiting to happen.

Usage:
    python3 tools/check_art_names.py build/spacetrader.tap build/stdata.bin
"""

import sys
import json
import struct
import argparse
from pathlib import Path

SECTOR_BYTES = 120
ROOT = Path(__file__).resolve().parent.parent


def tap_names(path: Path):
    d = path.read_bytes()
    names, i = [], 0
    while i < len(d):
        (n,) = struct.unpack_from("<H", d, i)
        i += 2
        blk = d[i:i + n]
        i += n
        if blk and blk[0] == 0x00 and len(blk) == 19:
            # the header name field is 10 bytes, space padded
            names.append(blk[2:12].decode("ascii", "replace").rstrip())
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tap", type=Path)
    ap.add_argument("stdata", type=Path)
    args = ap.parse_args()

    names = tap_names(args.tap)
    data = args.stdata.read_bytes()
    # the presence table is exactly one byte per system; stdata carries name and
    # goods records after it, which are not part of it
    n_sys = len(json.loads((ROOT / "data" / "systems.json").read_text())["systems"])
    present = data[SECTOR_BYTES:SECTOR_BYTES + n_sys]
    if len(present) != n_sys:
        print(f"error: stdata has {len(present)} presence bytes, expected {n_sys}",
              file=sys.stderr)
        raise SystemExit(1)

    problems = []
    checked = 0

    for i, flag in enumerate(present, start=1):
        want = (f"a{i:02d}", f"p{i:02d}")
        have = [w in names for w in want]
        if flag:
            checked += 1
            for w, ok in zip(want, have):
                if not ok:
                    problems.append(
                        f"system {i} is flagged present but block {w!r} is not on the "
                        f"tape - the 2068 would search forever"
                    )
        else:
            for w, ok in zip(want, have):
                if ok:
                    problems.append(
                        f"block {w!r} is on the tape but system {i} is flagged absent "
                        f"- it will never be loaded"
                    )

    # A requested name must not be a prefix of a different block, or LOAD could
    # match the wrong one.
    art = [n for n in names if len(n) == 3 and n[0] in "ap" and n[1:].isdigit()]
    for a in art:
        for other in names:
            if other != a and other.startswith(a):
                problems.append(f"block {other!r} shares a prefix with {a!r}")

    if problems:
        print(f"   {len(problems)} problem(s):")
        for p in problems:
            print(f"     {p}")
        raise SystemExit(1)

    have = [i for i, f in enumerate(present, 1) if f]
    print(f"   OK: {checked} system(s) with art {have}, all names exact")


if __name__ == "__main__":
    main()
