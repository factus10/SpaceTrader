#!/bin/sh
# Builds ecmtest.tap - a single self-contained TAP that exercises the ECM band
# path end to end, with no TS-Pico and no mounting. Everything loads by name
# from this one tape:
#
#   1 BASIC   ecmtest
#   2 CODE    stcode  -> 49152  band routines
#   3 CODE    ossatr  -> $6000  attribute plane (loaded to $C800 by the program)
#   4 CODE    osspix  -> $4000  pixel plane
#
# Runs on either Timex machine in Fuse; the TC2068 ROM is close enough.
#
# Usage:  ./tools/build_ecmtest.sh [source-image]

set -e
cd "$(dirname "$0")/.."

IMAGE=${1:-art/ossuary.png}
ASM=${ASM:-z88dk-z80asm}
command -v "$ASM" >/dev/null 2>&1 || ASM="$HOME/z88dk/z88dk/bin/z88dk-z80asm"

mkdir -p build/ecm

echo "1. assembling band routines"
"$ASM" -b -m -o=build/ecmband.bin src/ecmband.asm

echo "2. converting $IMAGE to ECM planes"
python3 tools/png_to_ecm.py "$IMAGE" --out-dir build/ecm --preview --report
STEM=$(python3 -c "
import sys,pathlib
print(pathlib.Path(sys.argv[1]).stem.replace('-','')[:6])" "$IMAGE")

echo "3. checking test program"
python3 tools/check_basic.py src/ecmtest.bas --art-band

echo "4. tokenizing"
zmakebas -n ecmtest -a 20 -o build/ecmtest_basic.tap src/ecmtest.bas

echo "5. appending CODE blocks"
python3 tools/append_code.py build/ecmtest_basic.tap build/ecmtest.tap \
    --code build/ecmband.bin:stcode:49152 \
    --code "build/ecm/${STEM}atr.bin:ossatr:24576" \
    --code "build/ecm/${STEM}pix.bin:osspix:16384"

echo
ls -l build/ecmtest.tap
echo 'Fuse: Machine > Select > Timex TC2068 (or TS2068), Media > Tape > Open, LOAD ""'
