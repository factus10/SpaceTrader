#!/usr/bin/env python3
"""
Appends binary files to a TAP as CODE blocks.

Numeric DATA is expensive in Sinclair BASIC: every literal is stored as its
digits *plus* a 6-byte binary float. The 478 numbers needed to POKE the machine
code and the sector table cost roughly 4 KB that way. Shipping them as CODE
blocks instead costs their actual size - 358 and 120 bytes.

The BASIC loader then does:

    CLEAR 49151
    LOAD "stcode" CODE
    LOAD "stdata" CODE

Usage:
    python3 tools/append_code.py base.tap out.tap \\
        --code build/ecmband.bin:stcode:49152 \\
        --code build/sector.bin:stdata:49664
"""

import struct
import argparse
from pathlib import Path

TYPE_CODE = 3


def checksum(b: bytes) -> int:
    c = 0
    for x in b:
        c ^= x
    return c


def make_header(name: str, length: int, start: int) -> bytes:
    if len(name) > 10:
        raise SystemExit(f"error: block name {name!r} exceeds 10 characters")
    body = (bytes([0x00, TYPE_CODE]) + name.ljust(10).encode("ascii")
            + struct.pack("<HHH", length, start, 32768))
    return body + bytes([checksum(body)])


def make_data(payload: bytes) -> bytes:
    body = b"\xff" + payload
    return body + bytes([checksum(body)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base", type=Path, help="TAP to append to")
    ap.add_argument("out", type=Path)
    ap.add_argument("--code", action="append", default=[], metavar="FILE:NAME:ADDR",
                    help="binary to append, e.g. build/ecmband.bin:stcode:49152")
    args = ap.parse_args()

    out = bytearray(args.base.read_bytes())

    for spec in args.code:
        try:
            path, name, addr = spec.rsplit(":", 2)
            addr = int(addr)
        except ValueError:
            raise SystemExit(f"error: bad --code spec {spec!r}, want FILE:NAME:ADDR")
        payload = Path(path).read_bytes()
        for blk in (make_header(name, len(payload), addr), make_data(payload)):
            out += struct.pack("<H", len(blk)) + blk
        print(f"  + {name:10} {len(payload):5} bytes @ {addr} (${addr:04X})")

    args.out.write_bytes(bytes(out))
    print(f"wrote {args.out} ({len(out)} bytes)")


if __name__ == "__main__":
    main()
