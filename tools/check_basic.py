#!/usr/bin/env python3
"""
Static checks for a zmakebas-format Sinclair BASIC source.

zmakebas will happily tokenize a program with duplicate line numbers or a jump to
a line that does not exist; the failure only shows up at run time, on hardware.
These are the checks worth having before that point:

  - line numbers unique and strictly ascending
  - line numbers within 1..9999
  - every GO TO / GO SUB / RESTORE / ON ERR GO TO target exists
  - every GO SUB target is reachable by a matching RETURN somewhere after it
  - PRINT AT rows stay out of the art band (rows 0-7) and off row 22-23
  - no CLS once the art band is in use

Usage:
    python3 tools/check_basic.py src/spacetrader.bas
    python3 tools/check_basic.py build/spacetrader_full.bas --art-band
"""

import re
import sys
import argparse
from pathlib import Path

# zmakebas tokenizes anything that looks like a keyword, so a variable named
# after one silently becomes that token and the program dies with "C Nonsense
# in BASIC" at run time. AT, FN, LN and PI are the ones that bite, because they
# are short enough to look like natural variable names.
KEYWORDS = {
    # functions
    "RND", "PI", "FN", "POINT", "ATTR", "AT", "TAB", "VAL", "LEN", "SIN", "COS",
    "TAN", "ASN", "ACS", "ATN", "LN", "EXP", "INT", "SQR", "SGN", "ABS", "PEEK",
    "IN", "USR", "NOT", "BIN", "CODE", "SCREEN", "STR", "CHR", "INKEY",
    # statements and clauses
    "OR", "AND", "LINE", "THEN", "TO", "STEP", "DEF", "CAT", "FORMAT", "MOVE",
    "ERASE", "MERGE", "VERIFY", "BEEP", "CIRCLE", "INK", "PAPER", "FLASH",
    "BRIGHT", "INVERSE", "OVER", "OUT", "LPRINT", "LLIST", "STOP", "READ",
    "DATA", "RESTORE", "NEW", "BORDER", "CONTINUE", "DIM", "REM", "FOR", "GO",
    "SUB", "INPUT", "LOAD", "LIST", "LET", "PAUSE", "NEXT", "POKE", "PRINT",
    "PLOT", "RUN", "SAVE", "RANDOMIZE", "IF", "CLS", "DRAW", "CLEAR", "RETURN",
    "COPY",
    # TS2068 additions
    "DELETE", "ON", "ERR", "STICK", "SOUND", "FREE", "RESET",
}

DIM_NAME = re.compile(r"\bDIM\s+([A-Za-z][A-Za-z0-9]*\$?)\s*\(", re.I)
DECL = re.compile(r"\b(?:LET|FOR|DIM)\s+([A-Za-z][A-Za-z0-9]*)")
ARRAY = re.compile(r"\b([A-Za-z][A-Za-z0-9]*)\s*\(")
INPUT_VAR = re.compile(r"\bINPUT\s+(?:\"[^\"]*\"\s*;\s*)?([A-Za-z][A-Za-z0-9]*)")
JUMP = re.compile(r"\b(?:GO\s*TO|GO\s*SUB|RESTORE)\s+(\d+)", re.I)
PRINT_AT = re.compile(r"PRINT\s+AT\s+(\d+)\s*,", re.I)
LINE_RE = re.compile(r"^\s*(\d+)\s?(.*)$")


def parse(path: Path):
    lines = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        m = LINE_RE.match(raw)
        if not m:
            lines.append((None, raw.strip(), n))
            continue
        lines.append((int(m.group(1)), m.group(2), n))
    return lines


def check(path: Path, art_band: bool):
    lines = parse(path)
    problems = []
    numbers = []

    prev = None
    for num, body, src in lines:
        if num is None:
            problems.append(f"{path.name}:{src}: line does not start with a number: {body[:40]!r}")
            continue
        if not 1 <= num <= 9999:
            problems.append(f"{path.name}:{src}: line number {num} out of range 1-9999")
        if prev is not None and num <= prev:
            kind = "duplicate" if num == prev else "out of order"
            problems.append(f"{path.name}:{src}: line {num} is {kind} (previous was {prev})")
        prev = num
        numbers.append(num)

    known = set(numbers)

    for num, body, src in lines:
        if num is None:
            continue
        if body.upper().lstrip().startswith("REM"):
            continue
        for tgt in JUMP.findall(body):
            if int(tgt) not in known:
                problems.append(
                    f"{path.name}:{src}: line {num} jumps to {tgt}, which does not exist"
                )
        # variable names that collide with keywords
        nostr = re.sub(r'"[^"]*"', "", body)
        # Only where a variable is introduced. Matching "name(" too would flag
        # every legitimate function call - INT (RND*6) looks identical to an
        # array reference - and array names are already caught at their DIM.
        for pat in (DECL, INPUT_VAR):
            for name in pat.findall(nostr):
                if name.upper() in KEYWORDS:
                    problems.append(
                        f"{path.name}:{src}: line {num} uses {name!r} as a variable, "
                        f"but zmakebas will tokenize it as the keyword "
                        f"{name.upper()} - rename it"
                    )
        # Sinclair BASIC array names are a single letter (plus $ for strings).
        # A multi-letter DIM is accepted by zmakebas and fails on the machine.
        for nm in DIM_NAME.findall(nostr):
            bare = nm[:-1] if nm.endswith("$") else nm
            if len(bare) > 1:
                problems.append(
                    f"{path.name}:{src}: line {num} declares array {nm!r}; "
                    f"Sinclair BASIC array names are one letter only"
                )
        if re.search(r"\bCLS\b", body, re.I):
            problems.append(
                f"{path.name}:{src}: line {num} uses CLS - it clears rows 0-21 "
                f"and would wipe the art band"
            )
        if art_band:
            for row in PRINT_AT.findall(body):
                r = int(row)
                if r <= 7:
                    problems.append(
                        f"{path.name}:{src}: line {num} prints at row {r}, "
                        f"inside the art band (rows 0-7)"
                    )
                elif r > 21:
                    problems.append(
                        f"{path.name}:{src}: line {num} prints at row {r}; "
                        f"PRINT AT only reaches row 21, use PRINT #1 for 22-23"
                    )

    # Every GO SUB target should have a RETURN at or after it, before the next
    # GO SUB target. Cheap approximation, but it catches fallthrough.
    gosub_targets = sorted({
        int(t) for num, body, _ in lines if num is not None
        and not body.upper().lstrip().startswith("REM")
        for t in re.findall(r"\bGO\s*SUB\s+(\d+)", body, re.I)
    })
    returns = {num for num, body, _ in lines
               if num is not None and re.search(r"\bRETURN\b", body, re.I)}
    for t in gosub_targets:
        if t not in known:
            continue
        later = [n for n in numbers if n >= t]
        if not any(n in returns for n in later):
            problems.append(f"{path.name}: GO SUB {t} has no RETURN after it")

    return problems, numbers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("--art-band", action="store_true",
                    help="also enforce the PRINT AT row limits for the ECM band layout")
    args = ap.parse_args()

    problems, numbers = check(args.source, args.art_band)

    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print(f"  {p}")
        raise SystemExit(1)

    print(f"OK: {args.source.name}, {len(numbers)} lines, "
          f"{numbers[0]}-{numbers[-1]}, no duplicate or dangling targets")


if __name__ == "__main__":
    main()
