#!/bin/sh
# Builds spacetrader.tap from source.
#
# The program has a hard ceiling: CHNG_VID refuses to enter ECM unless
# STKEND + $1B00 is still below RAMTOP. With CLEAR 49151 that means the
# program plus variables must end below $A4FF (42239). Two things keep it
# there, and both matter - the naive build overran by 4.3 KB:
#
#   - machine code and the sector table ship as CODE blocks, not numeric
#     DATA. Every numeric literal in Sinclair BASIC costs its digits plus
#     a 6-byte float; 478 of them is about 4 KB.
#   - REM comments are stripped from the shipped build, keeping only the
#     lines that are jump targets.
#
# Resulting TAP has four blocks:
#   1 BASIC   spacetrdr
#   2 CODE    stcode  ->  49152  ECM band routines
#   3 CODE    stdata  ->  49664  packed sector table

set -e
cd "$(dirname "$0")/.."

ASM=${ASM:-z88dk-z80asm}
command -v "$ASM" >/dev/null 2>&1 || ASM="$HOME/z88dk/z88dk/bin/z88dk-z80asm"

mkdir -p build

echo "1. assembling src/ecmband.asm"
"$ASM" -b -m -o=build/ecmband.bin src/ecmband.asm

echo "2. sector table -> build/sector.bin, names and goods -> DATA"
python3 tools/build_sector_data.py >/dev/null

echo "3. concatenating source"
cp src/spacetrader.bas build/spacetrader_full.bas

echo "4. stripping REM comments"
python3 tools/strip_rem.py build/spacetrader_full.bas -o build/spacetrader_ship.bas

echo "5. checking"
python3 tools/check_basic.py build/spacetrader_ship.bas --art-band

# After the checks, so they see real line numbers and real PRINT AT rows, and
# only the shipped file is rewritten. Literals are 40% of the program.
echo "5a. packing numeric literals"
python3 tools/pack_numbers.py build/spacetrader_ship.bas -o build/spacetrader_packed.bas

echo "6. tokenizing"
zmakebas -n spacetrdr -a 40 -o build/basic_only.tap build/spacetrader_packed.bas

echo "6a. font"
python3 tools/make_font.py >/dev/null
cp art/ui/font.bin build/font.bin
echo "   drew 96 glyphs, pixel row 0 left clear for the rule"

echo "6b. title screen (full-screen ECM, 6144-byte planes)"
python3 tools/png_to_ecm.py art/ui/title.png --out-dir build/title --height 192 --report

# Rows 22-23 are BASIC's lower screen. The game never clears their pixels -
# PRINT AT cannot reach them - so anything the title screen leaves there shows
# through under the white text attributes. Black them in the plane instead.
python3 - <<'PY'
import pathlib
p = pathlib.Path("build/title/titlepix.bin"); d = bytearray(p.read_bytes())
n = 0
for y in range(176, 192):
    base = (y >> 6) * 2048 + (y & 7) * 256 + ((y >> 3) & 7) * 32
    for c in range(32):
        d[base + c] = 0; n += 1
p.write_bytes(bytes(d))
print(f"   blanked {n} bytes of title rows 22-23")
PY

echo "7. art blocks from converted TAPs"
python3 tools/build_art.py || true
ART=""
if [ -f build/art/blocks.txt ]; then
    while IFS= read -r spec; do
        [ -n "$spec" ] && ART="$ART --code $spec"
    done < build/art/blocks.txt
fi

# stdata = 120-byte sector table then the 20-byte art presence table, so the
# game can check whether a block exists before naming it. A mounted TAP loops,
# so a name that is not on the tape searches forever - not an error ON ERR can
# catch. The presence table is the only thing preventing that hang.
cat build/sector.bin build/art/present.bin build/names.bin build/goods.bin > build/stdata.bin
echo "   stdata.bin = $(wc -c < build/stdata.bin | tr -d ' ') bytes (120 sector + 20 presence + 260 names + 104 goods)"

echo "8. appending CODE blocks"
# shellcheck disable=SC2086
python3 tools/append_code.py build/basic_only.tap build/spacetrader.tap \
    --code build/ecmband.bin:stcode:49152 \
    --code build/stdata.bin:stdata:50176 \
    --code build/font.bin:font:53248 \
    --code build/title/titleatr.bin:titatr:24576 \
    --code build/title/titlepix.bin:titpix:16384 $ART

echo "   verifying block names match what BASIC will construct"
python3 tools/check_art_names.py build/spacetrader.tap build/stdata.bin
echo "   checking the memory layout"
python3 tools/check_layout.py build/spacetrader.tap

echo "9. memory check"
python3 tools/check_fit.py build/basic_only.tap

# check_fit only models CHNG_VID's STKEND + $1B00 <= RAMTOP test, and that is
# not the constraint that bites first - a program slightly too large passes it
# and still wedges the machine before the title screen, silently. Boot it.
echo
echo "10. boot check"
python3 tools/check_boot.py build/spacetrader.tap


echo
ls -l build/spacetrader.tap
echo "runs as-is in Fuse (Timex TC2068 or TS2068) and on the TS-Pico"
