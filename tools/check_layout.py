#!/usr/bin/env python3
"""
Checks that the CODE blocks do not overlap each other or the reserved regions.

The machine code grew past the sector table's base once and silently clobbered
the blinds wipe, which only showed up on roughly one arrival in four because
the wipe mode is picked at random. Nothing else catches that: both blocks load
fine, the checksums are valid, and BASIC never notices.

Fixed regions:
    $C800-$CFFF  TEMP_ATR, the attribute staging buffer
    $F7C0-$FFFF  relocated dispatcher and machine stack once ECM is on
"""

import sys
import struct
import argparse
from pathlib import Path

TEMP_ATR = (0xC800, 0xCFFF, "TEMP_ATR staging buffer")
ECM_STACK = (0xF7C0, 0xFFFF, "relocated dispatcher and stack")


def blocks(tap: Path):
    d = tap.read_bytes()
    out, i = [], 0
    while i < len(d):
        (n,) = struct.unpack_from("<H", d, i)
        i += 2
        b = d[i:i + n]
        i += n
        if b and b[0] == 0x00 and len(b) == 19 and b[1] == 3:
            name = b[2:12].decode("ascii", "replace").rstrip()
            length, start, _ = struct.unpack_from("<HHH", b, 12)
            out.append((name, start, length))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tap", type=Path)
    args = ap.parse_args()

    # image blocks all load to the same two addresses by design; only the
    # resident blocks need checking against each other
    resident = [b for b in blocks(args.tap)
                if not (len(b[0]) == 3 and b[0][0] in "ap" and b[0][1:].isdigit())
                and b[0] not in ("titatr", "titpix")]

    problems = []
    for i, (n1, s1, l1) in enumerate(resident):
        e1 = s1 + l1 - 1
        for lo, hi, what in (TEMP_ATR, ECM_STACK):
            if s1 <= hi and e1 >= lo:
                problems.append(f"{n1} (${s1:04X}-${e1:04X}) overlaps {what} "
                                f"(${lo:04X}-${hi:04X})")
        for n2, s2, l2 in resident[i + 1:]:
            e2 = s2 + l2 - 1
            if s1 <= e2 and e1 >= s2:
                problems.append(f"{n1} (${s1:04X}-${e1:04X}) overlaps "
                                f"{n2} (${s2:04X}-${e2:04X})")

    for n, s, l in sorted(resident, key=lambda b: b[1]):
        print(f"   {n:8} ${s:04X}-${s+l-1:04X}  {l:5} bytes")
    if problems:
        print("   " + "\n   ".join(problems), file=sys.stderr)
        raise SystemExit(1)
    print("   no overlaps")


if __name__ == "__main__":
    main()
