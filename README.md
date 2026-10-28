# SpaceTrader

A Traveller-inspired space trading game for the Timex Sinclair 2068, distributed as a
TAP file for emulators and for real hardware via TS-Pico.

Trade eight commodities across twenty star systems, run contraband past customs, and
try not to accumulate enough heat that the pirates and the patrols both start looking
for you. Menu- and table-driven rather than real-time. Each system arrival is
illustrated with a bespoke full-screen Extended Color Mode image.

## Build target

**Sinclair BASIC + machine-code routines**, built with
[zmakebas](https://github.com/z00m128/zmakebas) (or
[ZMakebas+](https://timex-sinclair-projects.github.io/zmakebas-plus/)).

BASIC was chosen over the z88dk `+ts2068` pipeline because the ECM image loader this
project depends on is already BASIC-native: it drives the TS-Pico mount (`LOAD "tpi:…"`)
and `LOAD … CODE` through the BASIC ROM. Reimplementing those paths in C would be real
work for no gain in a genre with no real-time computation.

> **Before writing game code, read [`docs/memory-map.md`](docs/memory-map.md).**
> There is an unresolved conflict between where TS2068 BASIC places its program area and
> where ECM puts its second bitmap. It is settled by a single `PEEK` on hardware, and it
> determines how large the BASIC program may be.

## Layout

```
data/systems.json         authoritative sector table — edit this
tools/build_sector_data.py  packs it to 6 bytes/system, regenerates the docs and art prompts
docs/sector-table.md      generated human-readable sector table
docs/memory-map.md        the TS2068 memory map, ECM, and what it costs
docs/ui-layout.md         screen layout and the attribute addressing
docs/how-to-play.md       player's guide, with a sector map
midjourney/               art prompt generation (subjects live in data/systems.json)
art/                      4:1 source images, one per system
art/ui/font.bin           the game font, drawn by tools/make_font.py
src/spacetrader.bas       the game
src/ecmband.asm           ECM mode, band images, and the screen routines
build/                    everything generated, including spacetrader.tap
```

Build it with:

```bash
./tools/build_game.sh
```

That assembles the Z80, draws the font, converts the art, checks the BASIC, tokenizes it
and assembles the TAP — refusing to finish if the program has outgrown the space ECM
needs or if two CODE blocks would land on top of each other.

## Working with the sector data

`data/systems.json` is the single source of truth. Everything else is generated:

```bash
python3 tools/build_sector_data.py
```

This validates the table (duplicate hexes, goods that are both imported and exported,
restricted goods with no source system), packs each system to six bytes, and rewrites
`build/sectordata.bas`, `docs/sector-table.md`, and `midjourney/system_art_prompts.json`.
Use `--check` to validate without writing.

Because a system's index is also its ECM art index, the art prompts are generated from
the same file — the two cannot drift apart.

To produce the Midjourney prompts themselves:

```bash
python3 midjourney/generate_prompts.py
```

## Art pipeline

Subjects are authored per system in `data/systems.json`, rendered in Midjourney (v8.2),
then converted to ECM assets with
[Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/).

Use the converter build that writes **attributes first** in the TAP. Loading attributes
second corrupts the display with the filename text on a standard machine.

Each image is ~12 KB; twenty systems is ~240 KB, trivial against the TS-Pico's storage.
Images are displayed full-screen and discarded before returning to the standard-mode UI —
never windowed alongside it.

## License

MIT — see [LICENSE](LICENSE). The font in `art/ui/font.bin` is drawn by
[`tools/make_font.py`](tools/make_font.py) and is covered by the same license.

## Acknowledgements

**Jon Becker's TS2068 ECMViewer** was the reference implementation that showed Extended
Color Mode was usable at all, and that the mode-change had to go through the ROM rather
than a bare `OUT`. None of its code is in this repository; the routines in
[`src/ecmband.asm`](src/ecmband.asm) were written from the ROM disassembly and the TS2068
reference library, as traced in [`docs/memory-map.md`](docs/memory-map.md).

Artwork is converted with
[Retro Pixel Converter](https://factus10.github.io/retro-pixel-converter/).
