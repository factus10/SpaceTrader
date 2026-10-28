# ECM UI layout

Screen design for the stay-in-ECM display. Art occupies band 0; the interface lives in
bands 1 and 2. The mode is entered once at startup and never left, so the buggy
CLOSE-DFILE path is never called.

## Screen division

```
rows  0-7    band 0    ECM system art          256 x 64 px, loaded per arrival
rows  8-21   bands 1-2 game UI                 14 rows, PRINT AT
rows 22-23   band 2    command line            BASIC lower screen, PRINT #1 / INPUT
```

`PRINT AT` addresses the upper screen only, rows 0–21. Rows 22–23 are BASIC's lower
screen and are reached with `PRINT #1;` or used implicitly by `INPUT`. Rather than fight
that, the command line lives there — which is where `INPUT` would put its prompt anyway.

Nothing may `PRINT AT` into rows 0–7 or the art is overwritten.

### The art stays up

This is a departure from the brief worth stating plainly. The original plan was a
full-screen splash shown on arrival and then discarded. Here the art is *persistent
context*: it remains on screen the whole time the player is docked, under every trade and
market screen, and is replaced only on the next jump. The player always sees where they
are.

## Column grid

32 columns. The market screen sets the grid everything else follows:

| Field | Columns | Width | Alignment |
|---|---|---:|---|
| Good name | 0–10 | 11 | left |
| Price | 12–16 | 5 | right |
| Status | 18–19 | 2 | left (`EX` / `IM` / `--`) |
| Held | 22–25 | 4 | right |
| Contraband flag | 27 | 1 | `!` if restricted here |

Good names fit 11 columns without abbreviation, `ELECTRONICS` being the longest.

## Screens

### Market — the default docked view

```
0         1         2         3
01234567890123456789012345678901
CORIOLIS GATE      TL15 LAW 8     row 8   header
                                  row 9   1px rule (attribute only)
GOOD        PRICE ST  HELD        row 10  column headings
FOODSTUFFS     14 EX     0        row 11
ORE            48 IM     0        row 12
TEXTILES       45 --     0        row 13
MEDICAL        76 EX     0        row 14
ELECTRONICS    98 EX     6        row 15
WEAPONS       252 --     0 !      row 16
MACHINERY      77 EX     0        row 17
LUXURIES      340 --     2 !      row 18
                                  row 19  1px rule
B)UY S)ELL J)UMP I)NFO            row 20  menu
CR123450 FUEL6 HULL8 HEAT12       row 21  status
> _                               row 22  command line (PRINT #1)
```

### Jump

Neighbours are derived from hex coordinates at jump time, so the list is short — three to
six systems. `F` is fuel cost.

```
JUMP FROM CORIOLIS GATE           row 8
                                  row 9   rule
1 MERIDIAN      TL14 LAW 9  F2    row 10
2 VERITY        TL14 LAW 7  F3    row 11
3 ALDEBAR PRIME TL13 LAW 6  F2    row 12
4 PELLUCID      TL12 LAW 6  F4    row 13
                                  rows 14-18 free
KNOWN: MED ELEC  WANTS: ORE       row 19  selected system's trade
                                  row 20  rule
CR123450 FUEL6 HULL8 HEAT12       row 21
SELECT 1-4, OR C)ANCEL            row 22
```

The highlighted row is the current selection — see the color scheme below.

### Encounter

```
PIRATE CORVETTE CLOSING           row 8
                                  row 9   rule
  THEIR HULL  6                   row 11
  YOUR HULL   8                   row 12
  CARGO AT RISK  18 TONS          row 14
                                  row 17  rule
  E)VADE      F)IGHT              row 18
  B)RIBE      R)UN                row 19
                                  row 20  rule
CR123450 FUEL6 HULL8 HEAT12       row 21
CHOOSE                            row 22
```

### Customs

Same frame as the encounter, which is deliberate — both are the same state machine and
should read as the same kind of moment.

```
CUSTOMS INSPECTION                row 8
                                  row 9   rule
  SCANNING CARGO...               row 11
  CONTRABAND FOUND                row 12
    WEAPONS      6 TONS           row 13
    LUXURIES     2 TONS           row 14
  FINE ASSESSED   2400 CR         row 16
                                  row 17  rule
  C)OMPLY     B)RIBE              row 18
  S)URRENDER  R)ESIST             row 19
                                  row 20  rule
CR123450 FUEL6 HULL8 HEAT12       row 21
CHOOSE                            row 22
```

### Arrival

Shown while the band image loads and reveals. Rows 10–18 stay clear so the wipe has the
player's attention.

```
ARRIVED AT MERIDIAN               row 8
                                  row 9   rule
                                  rows 10-18 clear during reveal
IMPERSONAL BUREAUCRACY  POP 12    row 19
                                  row 20  rule
CR123450 FUEL6 HULL8 HEAT12       row 21
PRESS ANY KEY                     row 22
```

## Using ECM rather than working around it

Three things here are only possible because attributes are per 8×1 strip. In standard mode
each would cost a full 8-pixel character row.

**One-pixel rules.** A separator is 32 attribute bytes on a single pixel line — a crisp
hairline, not a row of `─` characters and not an 8-pixel-thick band. It must set the
**paper** color, not the ink: a bare pixel line has no pixels set, so an ink color
renders as solid paper and the rule is invisible. Note also that `COLOR_ROW` repaints
all eight pixel lines, so a rule sharing a character row must be drawn *after* it. It costs no
character cells at all, so rows 9, 19 and 20 in the mockups still hold text if wanted;
the rule sits on the top or bottom pixel line of the row. The art/UI boundary gets one
too, on pixel line 0 of row 8.

**Row highlight.** Inverting a menu selection is 8 attribute bytes × 32 columns, written
directly — no reprinting of text, so no flicker and no cursor artifacts.

**Heat as color.** The `HEAT` field on the status line shifts through its attribute as
heat climbs — white, then yellow, then bright red — without changing a character. Same for
`HULL` going red under damage and `FUEL` under 2. Color carries the warning, so the
status line never has to grow.

### Color scheme

| Element | Attribute | Notes |
|---|---|---|
| Body text | `$47` bright white on black | set by `INIT_TEXT_ATR` |
| Header row 8 | `$46` bright yellow | system identity |
| Column headings | `$45` bright cyan | |
| Rules | `$60` bright green **paper** | single pixel line |
| Contraband `!` | `$42` bright red | per-cell, column 27 only |
| Selected row | `$78` black on white | inverse |
| Heat 0–5 / 6–15 / 16+ | `$47` / `$46` / `$42` | white / yellow / red |

## Attribute addressing

The ECM attribute file mirrors the display file's banded, interleaved layout, so a
character row is *not* contiguous. For character row `R` (0–23), pixel line `s` (0–7),
column `c`:

```
offset = (R >> 3) * 2048  +  s * 256  +  (R & 7) * 32  +  c
attr   = $6000 + offset
```

A whole character row is therefore eight 32-byte runs, stepping 256 bytes apart. A
one-pixel rule is a single 32-byte run.

Note `(R >> 3) * 2048` is `(R & $18) * 256`, so the band contributes directly to the high
byte: `H = $60 + (R & $18)`. For `R = 23` that gives `$70`, and the last pixel line lands
at `$77E0`–`$77FF` — exactly the end of the attribute file.

Low byte base is `(R & 7) * 32`, at most 224, so a 32-byte run never crosses a page
boundary and `INC L` needs no carry handling.

### Routines

`COLOR_ROW` and `COLOR_LINE` are implemented in [`src/ecmband.asm`](../src/ecmband.asm).
`USR` cannot pass registers, so they read their arguments from parameter bytes; assembly
callers can enter at `CROW_CORE` / `CLINE_CORE` with registers set instead.

| Address | Name | Purpose |
|---:|---|---|
| 49170 | `COLOR_ROW` | all 8 pixel lines of one character row |
| 49173 | `COLOR_LINE` | a single pixel line — hairline rules |
| 49180 | `UI_ROW` | character row 0–23 |
| 49181 | `UI_LINE` | pixel line 0–7, `COLOR_LINE` only |
| 49182 | `UI_ATTR` | attribute byte to write |

```basic
REM hairline rule under the art: row 8, pixel line 0, bright green
POKE 49180,8: POKE 49181,0: POKE 49182,96: RANDOMIZE USR 49173

REM highlight menu row 20 in inverse
POKE 49180,20: POKE 49182,120: RANDOMIZE USR 49170

REM heat turning red - recolor row 21 without reprinting it
POKE 49180,21: POKE 49182,66: RANDOMIZE USR 49170
```

Folding these in pushed the older parameter bytes up by six: `MODE_BYTE` is now 49176 and
`WIPE_MODE` 49177.

Source listing, for reference:

```z80
; ----------------------------------------------------------------
; COLOR_ROW - set all 8 pixel lines of one character row
; Entry: A = attribute, C = character row 0-23
; ----------------------------------------------------------------
COLOR_ROW:
                LD      E,A                 ; attribute
                LD      A,C
                AND     $18                 ; band -> high byte
                ADD     A,ATR_BASE/256
                LD      H,A
                LD      A,C
                AND     7                   ; row within band
                ADD     A,A
                ADD     A,A
                ADD     A,A
                ADD     A,A
                ADD     A,A                 ; x32
                LD      L,A
                LD      D,8                 ; 8 pixel lines
CR_OUTER:
                PUSH    HL
                LD      B,32
CR_INNER:
                LD      (HL),E
                INC     L                   ; never crosses a page
                DJNZ    CR_INNER
                POP     HL
                INC     H                   ; next pixel line, +256
                DEC     D
                JR      NZ,CR_OUTER
                RET

; ----------------------------------------------------------------
; COLOR_LINE - set a single pixel line: hairline rules
; Entry: A = attribute, C = character row 0-23, B = pixel line 0-7
; ----------------------------------------------------------------
COLOR_LINE:
                LD      E,A
                LD      A,C
                AND     $18
                ADD     A,ATR_BASE/256
                ADD     A,B                 ; pixel line = +256 each
                LD      H,A
                LD      A,C
                AND     7
                ADD     A,A
                ADD     A,A
                ADD     A,A
                ADD     A,A
                ADD     A,A
                LD      L,A
                LD      B,32
CL_LOOP:
                LD      (HL),E
                INC     L
                DJNZ    CL_LOOP
                RET
```

Both share a `ROW_ADDR` helper rather than duplicating the address arithmetic.

## Confirmed in emulation

`ecmtest.tap` (built by `tools/build_ecmtest.sh`) exercises this layout end to end on a
Timex TC2068 in Fuse. All of it works:

- ECM engages — the `CHNG_VID` relocation and the `STKEND + $1B00` budget are correct
- `INIT_TEXT_ATR` makes `PRINT` visible, and ROM `PRINT` does **not** disturb the ECM
  attribute file. It writes color to `$5800`–`$5AFF`, which ECM ignores, as expected.
- the hairline rule renders one pixel tall, once given a *paper* color
- `COLOR_ROW` inverts and recolors a row without reprinting it
- a 2048-byte band image loads and reveals through all five wipe modes
- the lower screen at rows 22–23 coexists with band 2's attributes

Everything on a single TAP, loaded by name — no TS-Pico mount.

## Open questions

- **Fuel gauge.** A bar drawn in attributes rather than characters would suit ECM well, but
  it is not in the brief's state model — worth deciding before the status line is fixed.
- **Load time by system index.** A single TAP means `LOAD` by name is a linear scan, so
  reaching system 20 streams past roughly 76 KB of earlier image blocks. Fine from SD at
  4 KB per image; worth measuring before the full art set is baked in.
