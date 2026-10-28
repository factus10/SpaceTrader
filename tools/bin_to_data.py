#!/usr/bin/env python3
"""
Turns an assembled binary into Sinclair BASIC DATA statements plus a POKE loader.

Usage:
    python3 tools/bin_to_data.py build/ecmband.bin --org 49152 --line 9000
    python3 tools/bin_to_data.py build/ecmband.bin --org 49152 --verify
"""

import argparse
from pathlib import Path

PER_LINE = 16


def emit(data: bytes, org: int, start_line: int, step: int, loader_line: int):
    end = org + len(data) - 1
    lines = [
        f"{loader_line} REM INSTALL MACHINE CODE AT {org}",
        f"{loader_line + 10} RESTORE {start_line}",
        f"{loader_line + 20} FOR A={org} TO {end}",
        f"{loader_line + 30} READ X: POKE A,X",
        f"{loader_line + 40} NEXT A",
        f"{loader_line + 50} RETURN",
        "",
        f"{start_line} REM {len(data)} BYTES, {org}-{end} - GENERATED",
    ]
    line_no = start_line + step
    for i in range(0, len(data), PER_LINE):
        chunk = data[i:i + PER_LINE]
        lines.append(f"{line_no} DATA " + ",".join(str(b) for b in chunk))
        line_no += step
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("binary", type=Path)
    ap.add_argument("--org", type=int, required=True, help="load address, decimal")
    ap.add_argument("--line", type=int, default=9000, help="first DATA line number")
    ap.add_argument("--step", type=int, default=10, help="line number step")
    ap.add_argument("--loader-line", type=int, default=8000,
                    help="first line number of the POKE loader")
    ap.add_argument("-o", "--out", type=Path, help="write here instead of stdout")
    ap.add_argument("--verify", action="store_true",
                    help="parse the emitted DATA back and compare to the binary")
    args = ap.parse_args()

    data = args.binary.read_bytes()
    text = emit(data, args.org, args.line, args.step, args.loader_line)

    if args.verify:
        got = []
        for line in text.splitlines():
            _, _, rest = line.partition(" DATA ")
            if rest:
                got.extend(int(v) for v in rest.split(","))
        assert bytes(got) == data, "round trip mismatch"
        print(f"OK: {len(data)} bytes round-trip cleanly "
              f"({len([l for l in text.splitlines() if ' DATA ' in l])} DATA lines)")
        return

    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out} ({len(data)} bytes)")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
