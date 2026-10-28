#!/usr/bin/env python3
"""
Rewrites numeric literals into cheaper forms, for the shipped build only.

Sinclair BASIC stores a numeric literal twice: the digits you typed, and then a
5-byte binary float behind a $0E marker. So `8` costs 7 bytes, and `2600` costs
10. Measured on SpaceTrader, 668 literals account for 5610 bytes - forty per
cent of the whole program, against a ceiling it is already sitting a few bytes
under. The build script's own comment makes this point about DATA; it is just
as true of every literal in the code.

Three substitutions, all of them tight-binding functions so no parenthesis is
needed and no precedence changes:

    1    ->  SGN PI      2 bytes, saves 5
    3    ->  INT PI      2 bytes, saves 5
    n    ->  VAL "n"     digits+3 bytes, saves 3

`NOT PI` is the usual idiom for 0, but NOT binds looser than arithmetic, so
`a-0` would become `a-NOT PI` and parse as `NOT (a-PI)`. Parenthesising it back
costs the saving, so 0 goes through VAL like everything else.

Control-flow operands are left alone by default. GO TO and GO SUB do accept an
expression, but leaving them literal keeps check_basic able to verify that every
jump target exists, which is worth more than the bytes. Pass --jumps to pack
them too, once you trust the boot check.

This runs AFTER check_basic, so the checks still see real line numbers and real
PRINT AT rows, and only the shipped file is rewritten. The source stays readable,
the same way strip_rem.py keeps the comments.

Usage:
    python3 tools/pack_numbers.py in.bas -o out.bas [--jumps]
"""

import argparse
import re
from pathlib import Path

LINE_RE = re.compile(r"^\s*(\d+)\s?(.*)$")
STRING_RE = re.compile(r'"[^"]*"')
JUMP_RE = re.compile(r"\b(GO\s*TO|GO\s*SUB|RESTORE)(\s+)(\d+)", re.I)
# a literal, but not the tail of a name like a1 and not part of a longer number
NUM_RE = re.compile(r"(?<![A-Za-z0-9$_.])(\d+)")

CHEAP = {"1": "SGN PI", "3": "INT PI"}


def cost(num):
    """What the literal costs in the program: its digits plus the float."""
    return len(num) + 6


def replacement(num):
    return CHEAP.get(num, f'VAL "{num}"')


def new_cost(num):
    r = replacement(num)
    return 2 if num in CHEAP else len(num) + 3


SPLIT_RE = re.compile(r'("[^"]*")')
# either a whole control-flow operand (passed through untouched) or a literal
KEEP_JUMPS_RE = re.compile(
    r"(\b(?:GO\s*TO|GO\s*SUB|RESTORE)\s+\d+)|((?<![A-Za-z0-9$_.])\d+)", re.I)


def pack_code(fragment, keep_jumps, tally):
    """Rewrite literals in a fragment known to contain no string literal."""
    def swap(num):
        tally[0] += cost(num) - new_cost(num)
        return replacement(num)

    if keep_jumps:
        return KEEP_JUMPS_RE.sub(
            lambda m: m.group(1) if m.group(1) else swap(m.group(2)), fragment)
    return NUM_RE.sub(lambda m: swap(m.group(1)), fragment)


def pack_statement(text, keep_jumps):
    """Rewrite literals in one line's text, leaving strings and REMs alone."""
    # a REM swallows the rest of the line verbatim - never touch it
    rem = re.search(r"\bREM\b", text, re.I)
    tail = ""
    if rem:
        text, tail = text[:rem.start()], text[rem.start():]

    tally = [0]
    # odd indices are the string literals; only rewrite the code between them
    parts = SPLIT_RE.split(text)
    for i in range(0, len(parts), 2):
        parts[i] = pack_code(parts[i], keep_jumps, tally)
    return "".join(parts) + tail, tally[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--jumps", action="store_true",
                    help="also pack GO TO / GO SUB / RESTORE operands")
    args = ap.parse_args()

    out, total, count = [], 0, 0
    for line in args.source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if not m:
            out.append(line)
            continue
        number, text = m.group(1), m.group(2)
        packed, saved = pack_statement(text, keep_jumps=not args.jumps)
        count += len(NUM_RE.findall(STRING_RE.sub("", text)))
        total += saved
        out.append(f"{number} {packed}" if packed else number)

    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    where = "including" if args.jumps else "excluding"
    print(f"   packed numeric literals ({where} jump targets): saved {total} bytes")


if __name__ == "__main__":
    main()
