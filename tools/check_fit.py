#!/usr/bin/env python3
"""
Fails the build if the tokenized BASIC will not leave room for ECM.

CHNG_VID (EXROM $0E8E) checks `STKEND + $1B00 <= RAMTOP` before it will enter
extended color mode, and jumps to an error exit if not. The failure is silent
from BASIC's point of view - the mode simply never engages - so it is worth
catching at build time rather than on hardware.

With CLEAR 49151 the ceiling is:

    RAMTOP  49151  ($BFFF)
    less    $1B00  (6912, dispatcher + stack headroom)
    ------
    STKEND  42239  ($A4FF) maximum

The program starts at PROG ($6856 in standard mode), and variables, workspace
and the calculator stack all sit above it, so the tokenized program must be
comfortably under 15529 bytes.

Usage:
    python3 tools/check_fit.py build/basic_only.tap
"""

import struct
import argparse
from pathlib import Path

PROG = 0x6856          # TS2068 BASIC program start, standard mode
RAMTOP = 49151         # what CLEAR 49151 sets
HEADROOM = 0x1B00      # what CHNG_VID demands above STKEND
# Measured, not guessed. Sinclair storage is 6 bytes per simple numeric and
# 3 + 2*dims + 5*elements per array:
#     9 numeric arrays of 8      414
#     64 simple numerics         384
#     5 strings at 32 chars      175
#     calculator stack + workspace ~400
VAR_BUDGET = 1400


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tap", type=Path)
    ap.add_argument("--var-budget", type=int, default=VAR_BUDGET)
    args = ap.parse_args()

    d = args.tap.read_bytes()
    (n,) = struct.unpack_from("<H", d, 0)
    (length,) = struct.unpack_from("<H", d[2:2 + n], 12)

    limit = RAMTOP - HEADROOM
    prog_max = limit - PROG
    end = PROG + length
    slack = limit - end

    print(f"  tokenized BASIC   {length:6} bytes")
    print(f"  program ends at   {end:6} (${end:04X})")
    print(f"  ECM ceiling       {limit:6} (${limit:04X})  = RAMTOP {RAMTOP} - $1B00")
    print(f"  slack for vars    {slack:6} bytes")

    if length > prog_max:
        print(f"\nFAIL: over the ECM ceiling by {length - prog_max} bytes. "
              f"CHNG_VID will refuse to enter extended color mode.")
        raise SystemExit(1)

    if slack < args.var_budget:
        print(f"\nFAIL: only {slack} bytes for variables, workspace and the "
              f"calculator stack; want at least {args.var_budget}.")
        raise SystemExit(1)

    pct = 100 * length / prog_max
    print(f"\nOK: {pct:.0f}% of the {prog_max}-byte program budget used.")


if __name__ == "__main__":
    main()
