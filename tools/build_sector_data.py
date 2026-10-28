#!/usr/bin/env python3
"""
Builds derived artifacts from data/systems.json, the authoritative sector table.

Outputs:
  build/sectordata.bas            packed sector table as Sinclair BASIC DATA lines
  docs/sector-table.md            human-readable sector table
  midjourney/system_art_prompts.json   regenerated so art indices stay 1:1 with
                                       the sector table (style_suffix preserved)

Packing is 6 bytes per system, matching the design brief:
    byte 0   col<<4 | row        hex coordinate, packed nibbles
    byte 1   TL<<4  | law        tech level / law level
    byte 2   gov<<4 | pop        government / population tier
    byte 3   export bitmask
    byte 4   import bitmask
    byte 5   name index          (also the ECM art image index)

Usage:
    python3 tools/build_sector_data.py
    python3 tools/build_sector_data.py --check    # verify only, write nothing
"""

import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "systems.json"
ART = ROOT / "midjourney" / "system_art_prompts.json"

NAME_LEN = 13
GOOD_LEN = 11
BASIC_START_LINE = 9000
BASIC_LINE_STEP = 10
VALUES_PER_LINE = 12


def load():
    with open(SRC, encoding="utf-8") as f:
        return json.load(f)


def bit_for(goods, abbr):
    for g in goods:
        if g["abbr"] == abbr:
            return g["bit"]
    raise KeyError(f"unknown good {abbr!r}")


def mask(goods, abbrs):
    m = 0
    for a in abbrs:
        m |= bit_for(goods, a)
    return m


def pack(system, goods):
    """Return the 6 bytes for one system, validating every field fits."""
    def nib(name, v):
        if not 0 <= v <= 15:
            raise ValueError(f"{system['name']}: {name}={v} does not fit in a nibble")
        return v

    return [
        nib("col", system["col"]) << 4 | nib("row", system["row"]),
        nib("tl", system["tl"]) << 4 | nib("law", system["law"]),
        nib("gov", system["gov"]) << 4 | nib("pop", system["pop"]),
        mask(goods, system["exports"]),
        mask(goods, system["imports"]),
        system["index"],
    ]


def validate(data):
    """Sanity checks that would otherwise show up as confusing in-game behavior."""
    goods, systems, problems = data["goods"], data["systems"], []

    seen_coords, seen_index = {}, set()
    for s in systems:
        coord = (s["col"], s["row"])
        if coord in seen_coords:
            problems.append(
                f"{s['name']} shares hex {coord} with {seen_coords[coord]}"
            )
        seen_coords[coord] = s["name"]

        if s["index"] in seen_index:
            problems.append(f"duplicate index {s['index']} ({s['name']})")
        seen_index.add(s["index"])

        overlap = set(s["exports"]) & set(s["imports"])
        if overlap:
            problems.append(
                f"{s['name']} both exports and imports {sorted(overlap)}"
            )

    for g in goods:
        if not 0 <= g["base_price"] <= 255:
            problems.append(
                f"good {g['abbr']} base price {g['base_price']} does not fit a byte"
            )

    # Display names must fit the 11-column field in the market screen grid.
    for g in goods:
        if not g.get("short"):
            problems.append(f"good {g['abbr']} has no short display name")
        elif len(g["short"]) > 11:
            problems.append(
                f"good {g['abbr']} short name {g['short']!r} is "
                f"{len(g['short'])} cols, grid allows 11"
            )

    # Every good should be obtainable somewhere, or it is dead weight in the table.
    exported = {a for s in systems for a in s["exports"]}
    for g in goods:
        if g["abbr"] not in exported:
            problems.append(f"good {g['abbr']} is exported by no system")

    # Contraband only matters if a restricted good can actually be bought
    # somewhere legal enough to carry it away from.
    for g in goods:
        if g["law_threshold"] >= 15:
            continue
        sources = [s for s in systems if g["abbr"] in s["exports"]]
        if not sources:
            problems.append(f"restricted good {g['abbr']} has no source system")

    return problems


def emit_basic(data):
    goods, systems = data["goods"], data["systems"]
    flat = [b for s in systems for b in pack(s, goods)]

    # The packed sector table ships as a CODE block (build/sector.bin), not as
    # numeric DATA. Every numeric literal in Sinclair BASIC costs its digits plus
    # a 6-byte float, so 120 of them would waste about a kilobyte - and the
    # program has to fit under the ECM headroom check in CHNG_VID.
    lines = [
        "9000 REM GENERATED - DO NOT EDIT BY HAND",
    ]

    line_no = 9500
    lines.append("9499 REM SYSTEM NAMES, INDEXED BY NAMEIDX")
    for s in systems:
        lines.append(f'{line_no} DATA "{s["name"].upper()}"')
        line_no += 10

    line_no = 9800
    lines.append("9799 REM TRADE GOODS: NAME, BASE PRICE, LAW THRESHOLD")
    for g in goods:
        lines.append(
            f'{line_no} DATA "{g["short"]}",{g["base_price"]},{g["law_threshold"]}'
        )
        line_no += 10

    return "\n".join(lines) + "\n", len(flat)


def emit_markdown(data):
    goods, systems = data["goods"], data["systems"]
    govs = data["government_types"]

    rows = [
        "# Sector table",
        "",
        "Generated from `data/systems.json` by `tools/build_sector_data.py`. Do not edit by hand.",
        "",
        "`Idx` doubles as the ECM art image index. Law level drives both the encounter table",
        "and customs inspection odds; goods with a law threshold below a system's law level",
        "are contraband there.",
        "",
        "| Idx | System | Hex | TL | Law | Government | Pop | Exports | Imports |",
        "|----:|--------|:---:|---:|----:|------------|----:|---------|---------|",
    ]
    for s in systems:
        rows.append(
            f"| {s['index']} | {s['name']} | {s['col']},{s['row']} | {s['tl']} | {s['law']} "
            f"| {govs[str(s['gov'])]} | {s['pop']} "
            f"| {' '.join(s['exports'])} | {' '.join(s['imports'])} |"
        )

    rows += [
        "",
        "## Trade goods",
        "",
        "| ID | Good | Abbr | Base price | Law threshold |",
        "|---:|------|------|-----------:|--------------:|",
    ]
    for g in goods:
        thr = "—" if g["law_threshold"] >= 15 else str(g["law_threshold"])
        rows.append(
            f"| {g['id']} | {g['name']} | {g['abbr']} | {g['base_price']} | {thr} |"
        )

    rows += [
        "",
        "A law threshold of — means the good is legal everywhere. Otherwise the good is",
        "contraband in any system whose law level exceeds the threshold: Weapons (4) are",
        "illegal across the whole core and most of the middle band, which is what makes the",
        "frontier free ports worth the risk.",
        "",
    ]
    return "\n".join(rows)


def emit_art_prompts(data):
    """Regenerate the Midjourney prompt data from the authoritative sector table."""
    return {
        "_comment": "GENERATED from data/systems.json by tools/build_sector_data.py. "
                    "Edit subjects and art_style_suffix there, not here.",
        "style_suffix": data["art_style_suffix"],
        "systems": [
            {
                "index": s["index"],
                "name": s["name"],
                "archetype": s["archetype"],
                "subject": s["subject"],
            }
            for s in data["systems"]
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="validate only; write no files")
    args = ap.parse_args()

    data = load()

    problems = validate(data)
    if problems:
        print("Validation failed:")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)

    basic, nbytes = emit_basic(data)
    n = len(data["systems"])
    print(f"OK: {n} systems, {nbytes} bytes packed ({nbytes / n:.0f} bytes/system)")

    if args.check:
        return

    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "sectordata.bas").write_text(basic, encoding="utf-8")
    flat = bytes(b for s in data["systems"] for b in pack(s, data["goods"]))
    (ROOT / "build" / "sector.bin").write_bytes(flat)

    # 13 bytes per system name, space padded
    names = b"".join(s["name"].upper().ljust(NAME_LEN)[:NAME_LEN].encode("ascii")
                     for s in data["systems"])
    (ROOT / "build" / "names.bin").write_bytes(names)

    # 11 bytes name, 1 base price, 1 law threshold
    goods = b"".join(g["short"].ljust(GOOD_LEN)[:GOOD_LEN].encode("ascii")
                     + bytes([g["base_price"], g["law_threshold"]])
                     for g in data["goods"])
    (ROOT / "build" / "goods.bin").write_bytes(goods)
    print(f"    names.bin {len(names)} bytes, goods.bin {len(goods)} bytes")
    (ROOT / "docs" / "sector-table.md").write_text(emit_markdown(data), encoding="utf-8")
    with open(ART, "w", encoding="utf-8") as f:
        json.dump(emit_art_prompts(data), f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("Wrote build/sectordata.bas, docs/sector-table.md, "
          "midjourney/system_art_prompts.json")


if __name__ == "__main__":
    main()
