#!/usr/bin/env python3
"""
Generates full Midjourney prompts for TS2068 trading game system splash art.

Reads system_art_prompts.json (a constant style suffix + one entry per
system with a bespoke "subject" clause) and produces:

  - prompts_output.txt        one ready-to-paste Midjourney prompt per system
  - system_art_manifest.csv   index, name, archetype, suggested filename, prompt

The "index" field is meant to line up with the system's index in the sector
table, so the suggested filename doubles as the image lookup key for the
in-game ECM loader.

Usage:
    python generate_prompts.py              # generate both output files
    python generate_prompts.py --index 3     # print one system's prompt only
"""

import json
import csv
import argparse
from pathlib import Path

DATA_FILE = Path(__file__).parent / "system_art_prompts.json"


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(subject: str, style_suffix: str) -> str:
    return f"{subject.strip().rstrip(',')}, {style_suffix}"


def main():
    parser = argparse.ArgumentParser(
        description="Generate Midjourney prompts for TS2068 system splash art."
    )
    parser.add_argument(
        "--index", type=int, help="Only print the prompt for this system index"
    )
    args = parser.parse_args()

    data = load_data()
    style_suffix = data["style_suffix"]
    systems = data["systems"]

    if args.index is not None:
        match = next((s for s in systems if s["index"] == args.index), None)
        if not match:
            print(f"No system with index {args.index}")
            return
        print(build_prompt(match["subject"], style_suffix))
        return

    txt_blocks = []
    csv_rows = []

    for s in systems:
        prompt = build_prompt(s["subject"], style_suffix)
        txt_blocks.append(f"[{s['index']:02d}] {s['name']} ({s['archetype']})\n{prompt}")
        filename = f"sys{s['index']:02d}_{s['archetype']}"
        csv_rows.append([s["index"], s["name"], s["archetype"], filename, prompt])

    out_txt = Path("prompts_output.txt")
    out_txt.write_text("\n\n".join(txt_blocks) + "\n", encoding="utf-8")

    out_csv = Path("system_art_manifest.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "name", "archetype", "suggested_filename", "prompt"])
        writer.writerows(csv_rows)

    print(f"Wrote {len(systems)} prompts to {out_txt} and {out_csv}")


if __name__ == "__main__":
    main()
