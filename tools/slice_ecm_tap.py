#!/usr/bin/env python3
"""
Slices a full-screen ECM TAP down to a single horizontal band.

A full-screen ECM image is two 6144-byte CODE blocks: pixels at $4000 and color
attributes at $6000. The TS2068 display is three bands of eight character rows, and both
files are banded identically, so each third of the screen is a *contiguous* 2048-byte
block in each file:

    band 0   char rows  0-7    pixels $4000-$47FF   attributes $6000-$67FF
    band 1   char rows  8-15   pixels $4800-$4FFF   attributes $6800-$6FFF
    band 2   char rows 16-23   pixels $5000-$57FF   attributes $7000-$77FF

So a band-only image is 2 x 2048 = 4096 bytes instead of 12288.

The saving has to be made in the file, not in the LOAD. `LOAD "x" CODE addr,len` limits
what the ROM stores but the block still streams past in full, so it saves no time. This
tool rewrites the TAP headers so the blocks genuinely are 2048 bytes, after which a plain
`LOAD "ecm-pix" CODE 16384` transfers a third as much data.

Usage:
    python3 tools/slice_ecm_tap.py in.tap out.tap
    python3 tools/slice_ecm_tap.py in.tap out.tap --band 1
    python3 tools/slice_ecm_tap.py --verify in.tap
    python3 tools/slice_ecm_tap.py --batch src_dir/ dest_dir/
"""

import sys
import struct
import argparse
from pathlib import Path

BAND_SIZE = 2048
FULL_SIZE = 6144
PIX_BASE = 0x4000
ATR_BASE = 0x6000
BANDS = 3

TYPE_PROGRAM, TYPE_NUM_ARRAY, TYPE_CHR_ARRAY, TYPE_CODE = 0, 1, 2, 3


class TapError(Exception):
    pass


def checksum(data: bytes) -> int:
    c = 0
    for b in data:
        c ^= b
    return c


def read_blocks(path: Path):
    """Split a TAP into raw blocks (flag byte .. checksum byte inclusive)."""
    raw = path.read_bytes()
    blocks, i = [], 0
    while i < len(raw):
        if i + 2 > len(raw):
            raise TapError(f"{path.name}: truncated block length at offset {i}")
        (n,) = struct.unpack_from("<H", raw, i)
        i += 2
        if n == 0:
            raise TapError(f"{path.name}: zero-length block at offset {i - 2}")
        if i + n > len(raw):
            raise TapError(
                f"{path.name}: block at offset {i - 2} claims {n} bytes, "
                f"only {len(raw) - i} remain"
            )
        blocks.append(raw[i:i + n])
        i += n
    if not blocks:
        raise TapError(f"{path.name}: no blocks found")
    return blocks


def verify_block(block: bytes, index: int):
    """The last byte is the XOR of everything before it, flag byte included."""
    if len(block) < 2:
        raise TapError(f"block {index}: too short ({len(block)} bytes)")
    want = block[-1]
    got = checksum(block[:-1])
    if want != got:
        raise TapError(
            f"block {index}: checksum ${want:02X}, computed ${got:02X}"
        )


def parse_header(block: bytes):
    if block[0] != 0x00 or len(block) != 19:
        return None
    typ = block[1]
    name = block[2:12].decode("ascii", "replace").rstrip()
    length, p1, p2 = struct.unpack_from("<HHH", block, 12)
    return {"type": typ, "name": name, "length": length, "p1": p1, "p2": p2}


def make_header(typ: int, name: str, length: int, p1: int, p2: int) -> bytes:
    if len(name) > 10:
        raise TapError(f"filename {name!r} exceeds 10 characters")
    body = (
        bytes([0x00, typ])
        + name.ljust(10).encode("ascii")
        + struct.pack("<HHH", length, p1, p2)
    )
    return body + bytes([checksum(body)])


def make_data(payload: bytes) -> bytes:
    body = b"\xff" + payload
    return body + bytes([checksum(body)])


def write_tap(path: Path, blocks):
    out = bytearray()
    for b in blocks:
        out += struct.pack("<H", len(b)) + b
    path.write_bytes(bytes(out))


def classify(hdr):
    """Return 'pix', 'atr', or None, preferring the load address over the name."""
    if hdr["type"] != TYPE_CODE:
        return None
    if hdr["p1"] == PIX_BASE:
        return "pix"
    if hdr["p1"] == ATR_BASE:
        return "atr"
    name = hdr["name"].lower()
    if "pix" in name:
        return "pix"
    if "atr" in name or "att" in name:
        return "atr"
    return None


def load_pairs(path: Path):
    """Return [(header_dict, payload_bytes, kind)] for each CODE header+data pair."""
    blocks = read_blocks(path)
    for i, b in enumerate(blocks):
        verify_block(b, i)

    pairs, i = [], 0
    while i < len(blocks):
        hdr = parse_header(blocks[i])
        if hdr is None:
            i += 1
            continue
        if i + 1 >= len(blocks):
            raise TapError(f"{path.name}: header '{hdr['name']}' has no data block")
        data = blocks[i + 1]
        if data[0] != 0xFF:
            raise TapError(
                f"{path.name}: block after header '{hdr['name']}' is not a data block"
            )
        payload = data[1:-1]
        if len(payload) != hdr["length"]:
            raise TapError(
                f"{path.name}: '{hdr['name']}' header says {hdr['length']} bytes, "
                f"data block carries {len(payload)}"
            )
        pairs.append((hdr, payload, classify(hdr)))
        i += 2
    return pairs


def slice_tap(src: Path, dest: Path, band: int, quiet=False):
    pairs = load_pairs(src)

    found = {k: p for p in pairs if (k := p[2]) in ("pix", "atr")}
    for kind, label in (("atr", "attributes"), ("pix", "pixels")):
        if kind not in found:
            raise TapError(
                f"{src.name}: no {label} block found "
                f"(expected a CODE block loading at "
                f"${ATR_BASE if kind == 'atr' else PIX_BASE:04X})"
            )

    for hdr, payload, kind in pairs:
        if kind and len(payload) != FULL_SIZE:
            raise TapError(
                f"{src.name}: '{hdr['name']}' is {len(payload)} bytes, "
                f"expected {FULL_SIZE}. Already sliced?"
            )

    offset = band * BAND_SIZE
    out_blocks = []

    # Attributes first. Loading them second corrupts the display with the filename
    # text on a standard machine.
    for kind, base in (("atr", ATR_BASE), ("pix", PIX_BASE)):
        hdr, payload, _ = found[kind]
        chunk = payload[offset:offset + BAND_SIZE]
        if len(chunk) != BAND_SIZE:
            raise TapError(f"{src.name}: '{hdr['name']}' too short for band {band}")
        addr = base + offset
        out_blocks.append(
            make_header(TYPE_CODE, hdr["name"], BAND_SIZE, addr, hdr["p2"])
        )
        out_blocks.append(make_data(chunk))

    write_tap(dest, out_blocks)

    if not quiet:
        before, after = src.stat().st_size, dest.stat().st_size
        print(
            f"{src.name} -> {dest.name}  band {band}  "
            f"{before} -> {after} bytes ({before / after:.1f}x smaller)"
        )
    return dest


def verify(path: Path):
    pairs = load_pairs(path)
    print(f"{path.name}:")
    for hdr, payload, kind in pairs:
        tname = {0: "PROGRAM", 1: "NUM ARR", 2: "CHR ARR", 3: "CODE"}.get(
            hdr["type"], "?"
        )
        extra = f"@ ${hdr['p1']:04X}" if hdr["type"] == TYPE_CODE else ""
        tag = f"  [{kind}]" if kind else ""
        print(
            f"  {tname:8} {hdr['name']:<10} {len(payload):>5} bytes {extra}{tag}"
        )
    print("  all checksums OK")


def main():
    ap = argparse.ArgumentParser(
        description="Slice a full-screen ECM TAP to a single 2048-byte band."
    )
    ap.add_argument("src", type=Path, help="input .tap, or source directory with --batch")
    ap.add_argument("dest", type=Path, nargs="?",
                    help="output .tap, or destination directory with --batch")
    ap.add_argument("--band", type=int, default=0, choices=range(BANDS),
                    help="screen third to keep: 0=top (default), 1=middle, 2=bottom")
    ap.add_argument("--batch", action="store_true",
                    help="treat src/dest as directories and slice every .tap")
    ap.add_argument("--verify", action="store_true",
                    help="report block structure and checksums; write nothing")
    args = ap.parse_args()

    try:
        if args.verify:
            targets = sorted(args.src.glob("*.tap")) if args.src.is_dir() else [args.src]
            for t in targets:
                verify(t)
            return

        if not args.dest:
            ap.error("dest is required unless --verify is given")

        if args.batch:
            args.dest.mkdir(parents=True, exist_ok=True)
            srcs = sorted(args.src.glob("*.tap"))
            if not srcs:
                raise TapError(f"no .tap files in {args.src}")
            total_before = total_after = 0
            done, skipped = 0, []
            for s in srcs:
                # A source directory routinely holds loaders and utilities alongside
                # the images. Skip what isn't an ECM image rather than aborting.
                try:
                    d = slice_tap(s, args.dest / s.name, args.band)
                except TapError as e:
                    skipped.append(str(e))
                    continue
                total_before += s.stat().st_size
                total_after += d.stat().st_size
                done += 1

            if skipped:
                print(f"\nskipped {len(skipped)}:")
                for m in skipped:
                    print(f"  {m}")
            if not done:
                raise TapError(f"no ECM images found in {args.src}")
            print(
                f"\n{done} sliced: {total_before} -> {total_after} bytes "
                f"({total_before / total_after:.1f}x smaller)"
            )
        else:
            slice_tap(args.src, args.dest, args.band)

        print(
            f"\nLoader notes for band {args.band}:\n"
            f"  staging buffer needs {BAND_SIZE} bytes, not {FULL_SIZE}\n"
            f"  reveal/copy length is {BAND_SIZE} (LD BC,${BAND_SIZE:04X})\n"
            f"  attributes land at ${ATR_BASE + args.band * BAND_SIZE:04X}, "
            f"pixels at ${PIX_BASE + args.band * BAND_SIZE:04X}"
        )

    except TapError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
