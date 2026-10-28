#!/usr/bin/env python3
"""
Strips REM comments from a zmakebas source, preserving jump targets.

Sinclair BASIC stores REM text verbatim, so comments cost real memory in the
running program. SpaceTrader has to fit under a hard ceiling - CHNG_VID refuses
to enter ECM unless the program ends $1B00 bytes below RAMTOP - so the shipped
build strips them while the source keeps them.

A REM line that something jumps to cannot simply be deleted, or the jump breaks.
Those are reduced to a bare `REM` instead, which costs a handful of bytes and
keeps the line number valid.

Line numbers are otherwise untouched, so a listing on hardware still matches the
source line for line.

Usage:
    python3 tools/strip_rem.py in.bas -o out.bas
"""

import re
import argparse
from pathlib import Path

LINE_RE = re.compile(r"^\s*(\d+)\s?(.*)$")
JUMP = re.compile(r"\b(?:GO\s*TO|GO\s*SUB|RESTORE)\s+(\d+)", re.I)
IS_REM = re.compile(r"^\s*REM\b", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    args = ap.parse_args()

    raw = [l for l in args.source.read_text(encoding="utf-8").splitlines() if l.strip()]

    parsed = []
    for l in raw:
        m = LINE_RE.match(l)
        parsed.append((int(m.group(1)), m.group(2)) if m else (None, l))

    # Anything jumped to must keep its line number, REM or not.
    targets = set()
    for num, body in parsed:
        if num is None or IS_REM.match(body):
            continue
        targets.update(int(t) for t in JUMP.findall(body))

    out, dropped, kept = [], 0, 0
    for num, body in parsed:
        if num is None:
            out.append(body)
            continue
        if IS_REM.match(body):
            if num in targets:
                out.append(f"{num} REM")
                kept += 1
            else:
                dropped += 1
            continue
        out.append(f"{num} {body}")

    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")

    before = sum(len(l) + 4 for l in raw)
    after = sum(len(l) + 4 for l in out)
    print(f"stripped {dropped} REM lines, kept {kept} as jump targets "
          f"(~{before - after} bytes saved)")


if __name__ == "__main__":
    main()
