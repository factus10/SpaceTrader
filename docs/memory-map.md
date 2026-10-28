# TS2068 memory map, ECM, and what it costs the BASIC design

Sources: `TS2068 Ref Library/docs/` (memory map, video, system variables, errata) and
direct disassembly of `gus-home.rom` / `gus-exrom.rom`. **Note those are the TS-Pico
modified ROMs**, not stock — the values below were cross-checked against the sysvar
reference and agree, but a stock machine is worth a spot-check.

## Two different Timex modes, often conflated

The DECR register (port `$FF`) selects these independently:

| DECR bit | Mode | Memory used |
|---:|---|---|
| 0 | Second display file (page flipping) | `$6000`–`$7BFF` |
| 1 | **Extended Color Mode** (one attribute per pixel pair) | pixels `$4000`–`$57FF`, attributes `$6000`–`$77FF` |
| 2 | 64-column | standard file |

This project uses **bit 1**. Becker's loader passes mode `2` (`POKE 49164,2` →
`LD A,2` → `CALL CHNG_VID`), and its `ecmroutine.asm:38-39` matches: `PIX_BASE $4000`,
`ATR_BASE $6000`.

Either mode needs chunk 3 (`$6000`–`$7FFF`) freed, so both go through OPEN-DFILE.

## What entering ECM actually does

OPEN-DFILE (EXROM `$0DB0`) does far more than set a register:

1. Moves the UDG down by `$0840`
2. **Relocates the dispatcher code and machine stack from `$6000` to `$F7C0`–`$FFFF`**
3. Adjusts `SP` by `+$97C0`, updates `MSTBOT`, `ERRSP`, and all internal pointers
   via a fix table at EXROM `$1D00`
4. Sets `VIDMOD` (`$5CC2`)
5. Clears `$6000`–`$7AFF` to zero
6. Sets DECR, preserving bit 7

After it runs, the dispatcher entry moves from `$6200` to **`$F9C0`**, and the machine
stack lives just below that.

## This explains Becker's "TS-Pico reset" — and it wasn't the TS-Pico

`ecmroutine.asm:12-19` records that v2 placed the staging buffer at `$E800`–`$FFFF` and
**reset real hardware** during `ecm-atr` transfers, attributing it to "the TS-Pico
interface … needing some of that top-of-memory region for its own SD-card transfer
workspace," with the new 8K margin left "still unverified."

That attribution is almost certainly wrong. In ECM the machine stack and dispatcher sit
at **`$F7C0`–`$FFFF`**. A 6144-byte buffer at `$E800`–`$FFFF` lands squarely on top of
the live stack — which resets the machine regardless of whether a TS-Pico is attached.

Consequences:

- The `$E000`–`$FFFF` reservation is **architecturally required**, not a guess, and not
  a margin that might be shrunk. It holds the relocated stack and dispatcher whenever
  ECM is on.
- It is also not a margin that needs to *grow*. `$E000` clears `$F7C0` by 6 KB.
- Any machine code of ours must respect it for the same reason.

## PROG is at $6856 — inside the ECM attribute area

ROM-verified. EXROM `$096C`:

```
$096C: 21 40 68     LD HL,$6840      ; CHANS
$096F: 11 15 00     LD DE,$0015      ; 21 bytes of channel data
$0972: 19           ADD HL,DE        ; $6855
$0973: 22 57 5C     LD ($5C57),HL    ; DATADD
$0976: 23           INC HL           ; $6856
$0977: 22 53 5C     LD ($5C53),HL    ; PROG  = $6856
$097A: 22 4B 5C     LD ($5C4B),HL    ; VARS  = $6856
```

`docs/ts2068_system_variables.md` agrees: `CHANS $6840`, `PROG $6856`.

That is the **standard-mode** value. It changes when ECM is entered — see below.

## Resolved: CHNG_VID relocates the BASIC area before opening the display file

`$6856` sits inside the range OPEN-DFILE clears, so entering ECM ought to wipe any BASIC
program. It doesn't, because `CHNG_VID` (EXROM `$0E8E`) moves the BASIC area up *first*:

```
$0E9D: 21 C0 12     LD HL,$12C0
$0EA2: 11 40 08     LD DE,$0840      ; dispatcher + stack
$0EA5: 19           ADD HL,DE        ; HL = $1B00 required
$0EA6: ED 5B 65 5C  LD DE,($5C65)    ; STKEND
$0EAA: 19           ADD HL,DE
$0EAB: ED 5B B2 5C  LD DE,($5CB2)    ; RAMTOP
$0EAF: A7 / ED 52   SBC HL,DE
$0EB2: D2 3A 0F     JP NC,$0F3A      ; not enough room -> error exit
...
$0EC5: CD D0 65     CALL $65D0       ; RAM dispatcher helper (pointer fixups)
$0ECC: ED B8        LDDR             ; <-- moves the BASIC area UP
$0ED0: CD B0 0D     CALL $0DB0       ; then OPEN-DFILE clears $6000-$7AFF
$0ED3: 01 C0 97     LD BC,$97C0      ; ERRSP / LISTSP / MSTBOT += $97C0
```

So the program is out of the way before the clear happens. `CHNG_VID` itself fixes up
`ERRSP`, `LISTSP` and `MSTBOT`; the `PROG`/`VARS`/`STKEND` bookkeeping is handled inside
the RAM dispatcher helper at `$65D0` (copied from EXROM `$1000`), which is why no direct
`PROG` store appears in `CHNG_VID`'s body.

**This reconciles the reference docs rather than contradicting them.** The chunk table's
"chunk 4 (`$8000`–`$9FFF`) — BASIC program, variables, workspace" describes the *ECM*
state; the sysvar table's `PROG $6856` describes *standard* mode. Both are correct for
their respective modes. The relocation is `$1B00` (6912 bytes) of headroom, which puts
`PROG` in chunk 4 as the table says.

### The constraint that follows

`$0EA6`–`$0EB2` is a hard check: `STKEND + $1B00` must not exceed `RAMTOP`, or `CHNG_VID`
bails to an error exit at `$0F3A` and never enters ECM. So:

> **Our BASIC program + variables must end at least 6912 bytes below RAMTOP.**

With `CLEAR 49151` (RAMTOP `$BFFF`) that is satisfied with room to spare, but it is not
optional, and it is a real ceiling on program growth. If ECM silently refuses to engage
later in development, this check is the first thing to suspect.

`PRINT PEEK 23635+256*PEEK 23636` before and after entering ECM will give the exact
relocated base on hardware.

## Design consequence: the "display then discard" plan is at risk

The brief specifies full-screen ECM art that is *"discarded before returning to standard
mode."* But `ts2068_errata_and_notes.md:24-30` documents:

> **Bug:** The CLOSE-DFILE routine … Once the second display file is opened, it cannot be
> reliably closed. **Workaround:** Avoid opening the second display file unless you intend
> for it to remain open for the duration of the program's execution. If you need to close
> it, write your own relocation code modeled on OPEN-DFILE.

Becker's viewer sidesteps this — `RANDOMIZE USR 49225` (`RETURN TO NORMAL VIDEO MODE`) is
its own small routine, not a CLOSE-DFILE call, and it simply restores the video mode
without moving the stack back.

So switching in and out of ECM per system arrival is the one part of the brief that
should not be assumed to work. Three options, cheapest first:

1. **Stay in ECM for the whole game.** Draw the standard UI in ECM too. Costs nothing at
   runtime; the UI just has to tolerate the attribute layout.
2. **Use Becker's mode-restore routine** as-is and verify it survives repeated round trips.
3. **Write our own CLOSE-DFILE** modeled on OPEN-DFILE. Most work, most risk.

Option 1 is worth serious consideration — the game is menu- and table-driven, so a
permanently-ECM display is not obviously a loss, and it removes an entire class of bug.

## Working memory map (ECM active)

```
$4000-$57FF   ECM pixel bitmap             6144
$5800-$5AFF   standard attributes           768   (unused in ECM)
$5B00-$5BFF   printer buffer
$5C00-$5CCB   system variables                    (VIDMOD $5CC2, MSTBOT $5CC0)
$5CCB-$5EE9   reserved expansion area
$5EEA-$5FFF   SYSCON table
$6000-$77FF   ECM attribute bitmap         6144
$6840         CHANS
$6856         PROG  <-- collides with the above; see "remaining contradiction"
     ...      VARS / WORKSP / STKBOT
$C000-$C7FF   our machine code                    (ORG $C000)
$C800-$DFFF   ECM attribute staging buffer 6144
$E000-$F7BF   free
$F7C0-$FFFF   relocated dispatcher + machine stack  <-- MUST stay reserved in ECM
$F9C0         dispatcher entry point (vs $6200 in standard mode)
```

With `CLEAR 49151` the BASIC program and variables occupy `$6856`–`$BFFF`, about 22 KB —
generous for this game — *if* the contradiction above resolves in our favor.
