; ================================================================
; SpaceTrader - ECM band display routines
;
; The hardware procedure here was established from the TS2068 ROM
; itself - CHNG_VID at EXROM $0E8E, what OPEN-DFILE relocates, and the
; RAMTOP check that gates the whole thing - cross-checked against the
; TS2068 reference library. See docs/memory-map.md for the trace.
;
; Jon Becker's ECMViewer was the reference implementation that showed
; the mode was usable at all, and is gratefully acknowledged; no code
; from it remains here.
;
; ----------------------------------------------------------------
; Why a band
;
; The TS2068 display is three bands of eight character rows, and the
; ECM attribute file is banded identically. Each third is therefore a
; contiguous 2048-byte block in both files:
;
;     band 0  rows  0-7   pixels $4000-$47FF  attrs $6000-$67FF
;     band 1  rows  8-15  pixels $4800-$4FFF  attrs $6800-$6FFF
;     band 2  rows 16-23  pixels $5000-$57FF  attrs $7000-$77FF
;
; SpaceTrader puts system art in band 0 and the text UI in bands 1-2,
; so an image costs 2 x 2048 = 4096 bytes instead of 12288, and loads
; in a third of the time. tools/build_art.py cuts converted images
; down to band blocks.
;
; ----------------------------------------------------------------
; Memory
;
;   $C000-$C7FF   this code (ORG $C000)
;   $C800-$CFFF   TEMP_ATR - 2048-byte attribute staging buffer
;   $D000-$DFFF   free (was staging buffer in the full-screen version)
;   $E000-$F7BF   free
;   $F7C0-$FFFF   RESERVED - relocated dispatcher and machine stack
;
; BASIC must reserve all of this with:
;       CLEAR $BFFF     (CLEAR 49151)
;
; The $F7C0 reservation is not optional and not a safety margin.
; Entering ECM makes the ROM relocate the function dispatcher and the
; machine stack there. Becker's v2 put the staging buffer at
; $E800-$FFFF and reset real hardware; his notes attribute that to the
; TS-Pico needing the region for SD transfers, but the actual cause is
; the relocated stack. $C800 clears it by a wide margin either way.
;
; Also note: program + variables must end at least $1B00 (6912) bytes
; below RAMTOP, or CHNG_VID refuses to enter ECM at all.
; ================================================================

                ORG     $C000

PORT_HSR        EQU     $F4
PORT_CTRL       EQU     $FF
CHNG_VID        EQU     $0E8E
VIDMOD          EQU     $5CC2

PIX_BASE        EQU     $4000
ATR_BASE        EQU     $6000

BAND            EQU     0                   ; 0=top, 1=middle, 2=bottom
BAND_SIZE       EQU     2048
BAND_ROWS       EQU     64                  ; pixel rows in one band
BAND_COLS       EQU     32                  ; byte columns across

BAND_OFF        EQU     BAND*BAND_SIZE
PIX_BAND        EQU     PIX_BASE+BAND_OFF
ATR_BAND        EQU     ATR_BASE+BAND_OFF

TEMP_ATR        EQU     $C800               ; 2048 bytes, page aligned

; Attribute area used by the text UI - everything outside the art
; band. Assumes BAND 0, so the text area is one contiguous run.
TEXT_ATR        EQU     ATR_BASE+BAND_SIZE
TEXT_ATR_LEN    EQU     6144-BAND_SIZE

; ================================================================
; Jump table - fixed entry points for BASIC.
; Keep these first and in this order so the addresses BASIC calls
; stay stable when the code below changes.
; ================================================================

CODESTART:

; ----------------------------------------------------------------
; Parameters come FIRST, at fixed addresses, so that adding an entry
; to the jump table never moves them - and adding a parameter never
; moves the jump table. Both have grown twice already.
; ----------------------------------------------------------------

MODE_BYTE:      DB      2                   ; $C000  49152  2=ECM
WIPE_MODE:      DB      0                   ; $C001  49153  0=instant
                                             ;   1=L-R 2=R-L 3=curtain 4=blinds
WIPE_SPEED:     DB      0                   ; $C002  49154  0=fastest
TEXT_ATTR:      DB      $47                 ; $C003  49155  bright white on black
UI_ROW:         DB      0                   ; $C004  49156  char row 0-23
UI_LINE:        DB      0                   ; $C005  49157  pixel line 0-7
UI_ATTR:        DB      $47                 ; $C006  49158  attribute to write
UI_COL:         DB      0                   ; $C007  49159  start column 0-31
UI_LEN:         DB      0                   ; $C008  49160  cells to color
UI_IDX:         DB      1                   ; $C009  49161  record number, 1-based
UI_TAB:         DB      0                   ; $C00A  49162  0=system names 1=goods
                DS      5                   ; $C00B-$C00F spare

; ----------------------------------------------------------------
; Jump table - fixed entry points for BASIC
; ----------------------------------------------------------------

                JP      MODESET             ; $C010  49168
                JP      CLR_ATR_BAND        ; $C013  49171
                JP      CLR_PIX_BAND        ; $C016  49174
                JP      REVEAL_ATR          ; $C019  49177
                JP      INIT_TEXT_ATR       ; $C01C  49180
                JP      EXIT_ECM            ; $C01F  49183
                JP      COLOR_ROW           ; $C022  49186
                JP      COLOR_LINE          ; $C025  49189
                JP      COLOR_SPAN          ; $C028  49192
                JP      PRINT_REC           ; $C02B  49195
                JP      MENU_KEYS           ; $C02E  49198

; ================================================================
; MODESET - enter the video mode in MODE_BYTE
;
; CHNG_VID lives in the EXROM, so page it in around the call. It also
; relocates the BASIC program and the machine stack; see the header.
; ================================================================

MODESET:
                DI
                LD      A,1
                OUT     (PORT_HSR),A        ; EXROM into chunk 0
                IN      A,(PORT_CTRL)
                SET     7,A
                OUT     (PORT_CTRL),A       ; enable EXROM

                LD      A,(MODE_BYTE)
                PUSH    AF
                EI
                CALL    CHNG_VID
                DI

                IN      A,(PORT_CTRL)
                RES     7,A
                OUT     (PORT_CTRL),A
                XOR     A
                OUT     (PORT_HSR),A        ; back to all-HOME

                POP     AF
                CP      $80
                JR      NZ,MS_DONE
                LD      (VIDMOD),A
MS_DONE:
                EI
                RET

; ================================================================
; EXIT_ECM - restore standard video mode
;
; Does NOT call the ROM's CLOSE-DFILE, which is documented as broken:
; once the second display file is open it cannot be reliably closed.
; This only puts the video mode back. Prefer staying in ECM for the
; whole program run rather than round-tripping.
; ================================================================

EXIT_ECM:
                XOR     A
                LD      (MODE_BYTE),A
                CALL    MODESET
                RET

; ================================================================
; CLR_ATR_BAND - black out the art band's attributes only
;
; Scoped to the band. Clearing all 6144 attribute bytes, as the
; full-screen version did, would blank the text UI in bands 1-2.
; ================================================================

CLR_ATR_BAND:
                LD      HL,ATR_BAND
                LD      DE,ATR_BAND+1
                LD      BC,BAND_SIZE-1
                XOR     A
                LD      (HL),A
                LDIR
                RET

; ================================================================
; CLR_PIX_BAND - zero the art band's pixels only
;
; Not needed before loading an image (the load overwrites all 2048
; bytes), but useful for clearing the art area without one.
; ================================================================

CLR_PIX_BAND:
                LD      HL,PIX_BAND
                LD      DE,PIX_BAND+1
                LD      BC,BAND_SIZE-1
                XOR     A
                LD      (HL),A
                LDIR
                RET

; ================================================================
; INIT_TEXT_ATR - fill the text area's ECM attributes
;
; Call once after entering ECM, before printing anything.
;
; After the mode change the whole attribute file is zero, which is
; black ink on black paper - PRINT appears to do nothing at all.
; INK and PAPER do not help, because they write to the standard
; attribute area at $5800, which ECM does not read.
;
; Attributes are per 8x1 pixel strip here, so a single text line can
; be recolored later by filling 8 rows x 32 bytes at its position.
; ================================================================

INIT_TEXT_ATR:
                LD      A,(TEXT_ATTR)
                LD      HL,TEXT_ATR
                LD      DE,TEXT_ATR+1
                LD      BC,TEXT_ATR_LEN-1
                LD      (HL),A
                LDIR
                RET

; ================================================================
; COLOR_SPAN - color a run of cells on one character row
;
; This is what makes a single letter a different color: ECM has the
; same horizontal granularity as standard mode (one attribute per
; character cell) but eight times the vertical, so a one-cell span
; over all 8 pixel lines recolors exactly one character.
;
; BASIC: POKE 49156,row: POKE 49159,col: POKE 49160,len
;        POKE 49158,attr: RANDOMIZE USR 49192
; ================================================================

COLOR_SPAN:
                LD      A,(UI_LEN)
                OR      A
                RET     Z                   ; DJNZ with B=0 would run 256 times
                LD      A,(UI_ROW)
                LD      C,A
                LD      A,(UI_ATTR)
                LD      E,A
                CALL    ROW_ADDR            ; reads C, so set the row first
                LD      A,(UI_COL)
                ADD     A,L                 ; base L is a multiple of 32 and the
                LD      L,A                 ; column is < 32, so no page crossing
                LD      A,(UI_LEN)
                LD      C,A
                LD      D,8
CS_OUTER:
                PUSH    HL
                LD      B,C
CS_INNER:
                LD      (HL),E
                INC     L
                DJNZ    CS_INNER
                POP     HL
                INC     H                   ; next pixel line
                DEC     D
                JR      NZ,CS_OUTER
                RET

; ================================================================
; PRINT_REC - draw a fixed-width record straight into the display
;
; Replaces a BASIC loop that built the string a character at a time
; with CHR$ PEEK and concatenation. Sinclair string concatenation
; reallocates on every += , so the jump menu was doing 104 of them to
; put eight system names on screen. This blits glyphs instead.
;
; Both tables use a 13-byte stride; only the printed length differs,
; because a goods record is 11 name bytes then price and law level.
;
; Entry: UI_IDX record 1-based, UI_TAB 0=systems 1=goods,
;        UI_ROW, UI_COL
;
; Writes pixels only. Color comes from whatever attributes are already
; in place, which is what INIT_TEXT_ATR put there.
; ================================================================

; Derived from the stdata block layout rather than hand-converted, which is
; how this got written as $C26C the first time:
;   +0   sector table   120
;   +120 art presence    20
;   +140 system names   260  (20 x 13)
;   +400 trade goods    104  (8 x 13)
STDATA          EQU     $C400               ; 50176
NAMES_BASE      EQU     STDATA+140          ; 50316
GOODS_BASE      EQU     STDATA+400          ; 50576
CHARS_SV        EQU     $5C36               ; -> $3C00, glyph = CHARS + code*8

PRINT_REC:
                LD      A,(UI_IDX)
                DEC     A
                LD      L,A
                LD      H,0
                LD      D,H
                LD      E,L                 ; DE = record number
                ADD     HL,HL               ; x2
                ADD     HL,HL               ; x4
                ADD     HL,DE               ; x5
                ADD     HL,HL               ; x10
                ADD     HL,DE               ; x11
                ADD     HL,DE               ; x12
                ADD     HL,DE               ; x13 - the stride
                LD      A,(UI_TAB)
                OR      A
                LD      DE,NAMES_BASE
                JR      Z,PR_BASE
                LD      DE,GOODS_BASE
PR_BASE:
                ADD     HL,DE               ; HL = source record
                LD      A,(UI_TAB)
                OR      A
                LD      B,13
                JR      Z,PR_DEST
                LD      B,11                ; goods name is 11 of the 13
PR_DEST:
                LD      A,(UI_ROW)
                AND     $18                 ; band -> high byte
                ADD     A,PIX_BASE/256
                LD      D,A
                LD      A,(UI_ROW)
                AND     7
                ADD     A,A
                ADD     A,A
                ADD     A,A
                ADD     A,A
                ADD     A,A                 ; x32
                LD      E,A
                LD      A,(UI_COL)
                ADD     A,E                 ; col + len <= 32, so no carry
                LD      E,A                 ; DE = display cell, pixel line 0

PR_CHAR:
                LD      A,(HL)              ; character code
                PUSH    HL
                PUSH    DE
                PUSH    BC
                LD      L,A
                LD      H,0
                ADD     HL,HL
                ADD     HL,HL
                ADD     HL,HL               ; code * 8
                LD      BC,(CHARS_SV)
                ADD     HL,BC               ; HL = glyph
                LD      B,8
PR_ROW:
                LD      A,(HL)
                LD      (DE),A
                INC     HL
                INC     D                   ; next pixel line, +256
                DJNZ    PR_ROW
                POP     BC
                POP     DE
                POP     HL
                INC     HL                  ; next source byte
                INC     E                   ; next column
                DJNZ    PR_CHAR
                RET

; ================================================================
; MENU_KEYS - color the four command letters of an encounter menu
;
; The customs and combat screens both print a 2x2 menu at rows 17-18,
; column 2, with the second option at column 13. Those positions are
; fixed by the shared frame, so they are constants here - doing it
; from BASIC would be four COLOR_SPAN calls per screen, about 150
; bytes, against 40 for one POKE and a USR.
;
; Entry: UI_ATTR
; ================================================================

MK_ROW1         EQU     17
MK_COL1         EQU     2
MK_COL2         EQU     13

MENU_KEYS:
                LD      C,MK_ROW1
                CALL    MK_ROW
                LD      C,MK_ROW1+1
                JP      MK_ROW              ; tail call, saves a RET

MK_ROW:
                CALL    ROW_ADDR            ; HL = row C, pixel line 0
                LD      A,L
                ADD     A,MK_COL1
                LD      E,A                 ; first key cell
                LD      A,L
                ADD     A,MK_COL2
                LD      D,A                 ; second key cell
                LD      A,(UI_ATTR)
                LD      B,8                 ; eight pixel lines
MK_L:
                LD      L,E
                LD      (HL),A
                LD      L,D
                LD      (HL),A
                INC     H
                DJNZ    MK_L
                RET

; ================================================================
; ROW_ADDR - attribute address of character row C, pixel line 0
; Entry: C = character row 0-23
; Exit:  HL = ATR_BASE + (C & $18)*256 + (C & 7)*32
; Clobbers: A
;
; The attribute file is banded and interleaved exactly like the
; display file, so a character row is NOT contiguous - it is eight
; 32-byte runs stepping 256 bytes apart. The band contributes
; directly to the high byte because (R>>3)*2048 == (R & $18)*256.
; ================================================================

ROW_ADDR:
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
                RET

; ================================================================
; COLOR_ROW - set all 8 pixel lines of one character row
;
; Used for menu highlighting: an inverse row is a pure attribute
; write, so the text never has to be reprinted - no flicker.
;
; BASIC: POKE 49180,row: POKE 49182,attr: RANDOMIZE USR 49170
; ASM:   A = attribute, C = character row 0-23, enter at CROW_CORE
; ================================================================

COLOR_ROW:
                LD      A,(UI_ROW)
                LD      C,A
                LD      A,(UI_ATTR)
CROW_CORE:
                LD      E,A                 ; attribute
                CALL    ROW_ADDR
                LD      D,8                 ; 8 pixel lines
CR_OUTER:
                PUSH    HL
                LD      B,BAND_COLS
CR_INNER:
                LD      (HL),E
                INC     L                   ; base L is a multiple of 32 and
                DJNZ    CR_INNER            ; at most 224, so never crosses a page
                POP     HL
                INC     H                   ; next pixel line, +256
                DEC     D
                JR      NZ,CR_OUTER
                RET

; ================================================================
; COLOR_LINE - set a single pixel line
;
; This is the hairline rule: one pixel tall, costing no character
; cells. Set the PAPER color, not the ink - a bare pixel line has
; no pixels set, so an ink color renders as solid paper. Standard mode cannot do it - there, color granularity is
; the full 8-pixel character row.
;
; BASIC: POKE 49180,row: POKE 49181,line: POKE 49182,attr
;        RANDOMIZE USR 49173
; ASM:   A = attribute, C = char row 0-23, B = pixel line 0-7,
;        enter at CLINE_CORE
; ================================================================

COLOR_LINE:
                LD      A,(UI_ROW)
                LD      C,A
                LD      A,(UI_LINE)
                LD      B,A
                LD      A,(UI_ATTR)
CLINE_CORE:
                LD      E,A                 ; attribute
                CALL    ROW_ADDR            ; preserves B
                LD      A,H
                ADD     A,B                 ; each pixel line is +256
                LD      H,A
                LD      B,BAND_COLS
CL_LOOP:
                LD      (HL),E
                INC     L
                DJNZ    CL_LOOP
                RET

; ================================================================
; BAND_ROW - point HL and DE at one pixel row of the band
;
; Entry: A = pixel row 0-63
; Exit:  HL = TEMP_ATR + offset, DE = ATR_BAND + offset
; Clobbers: A, C
;
; A band row is 32 contiguous bytes. Within a band the offset is
;
;     (y & 7) * 256  +  (y >> 3) * 32
;
; so the row number lands in the high byte and the band-relative
; character row in the low byte. (y >> 3) * 32 is (y & $38) * 4,
; which is two shifts rather than a divide.
;
; Both planes share the offset, so one computation serves both.
; ================================================================

BAND_ROW:
                LD      C,A
                AND     7
                ADD     A,TEMP_ATR/256
                LD      H,A
                ADD     A,(ATR_BAND/256)-(TEMP_ATR/256)
                LD      D,A
                LD      A,C
                AND     $38
                ADD     A,A
                ADD     A,A                 ; (y >> 3) * 32
                LD      L,A
                LD      E,A
                RET

; ================================================================
; COPY_ROW - reveal one pixel row, then pause
; Entry: A = pixel row 0-63
; ================================================================

COPY_ROW:
                CALL    BAND_ROW
                LD      BC,BAND_COLS
                LDIR
                ; fall through to the delay

; ================================================================
; REVEAL_DELAY - tunable pause between reveal steps
; ================================================================

REVEAL_DELAY:
                LD      A,(WIPE_SPEED)
                OR      A
                RET     Z
                LD      B,A
RD_OUTER:
                PUSH    BC
                LD      C,0
RD_INNER:
                DEC     C
                JR      NZ,RD_INNER
                POP     BC
                DJNZ    RD_OUTER
                RET

; ================================================================
; REVEAL_ATR - copy the staged attributes into view
;
; Call once TEMP_ATR and the band's pixels are both loaded.
; Dispatches on WIPE_MODE.
;
; Every mode works a row at a time rather than a column at a time.
; A band is 256 wide and 64 tall, so a row is 32 contiguous bytes
; and one LDIR; a column would be 64 scattered bytes stepping 32
; apart. Row order is also what suits a letterbox image - the
; picture arrives along its long axis.
; ================================================================

REVEAL_ATR:
                LD      A,(WIPE_MODE)
                CP      1
                JR      Z,RV_DOWN
                CP      2
                JR      Z,RV_UP
                CP      3
                JR      Z,RV_OUT
                CP      4
                JR      Z,RV_LACE

                ; mode 0, or anything unrecognised - all at once
                LD      HL,TEMP_ATR
                LD      DE,ATR_BAND
                LD      BC,BAND_SIZE
                LDIR
                RET

; ----------------------------------------------------------------
; Mode 1: top down
; ----------------------------------------------------------------
RV_DOWN:
                LD      C,0
RV_DOWN_LOOP:
                LD      A,C
                PUSH    BC
                CALL    COPY_ROW
                POP     BC
                INC     C
                LD      A,C
                CP      BAND_ROWS
                JR      NZ,RV_DOWN_LOOP
                RET

; ----------------------------------------------------------------
; Mode 2: bottom up
; ----------------------------------------------------------------
RV_UP:
                LD      C,BAND_ROWS-1
RV_UP_LOOP:
                LD      A,C
                PUSH    BC
                CALL    COPY_ROW
                POP     BC
                DEC     C
                LD      A,C
                CP      255                 ; wrapped past zero
                JR      NZ,RV_UP_LOOP
                RET

; ----------------------------------------------------------------
; Mode 3: out from the middle, a row above and a row below at a time
; ----------------------------------------------------------------
RV_OUT:
                LD      C,BAND_ROWS/2       ; lower half, walking down
                LD      B,BAND_ROWS/2-1     ; upper half, walking up
RV_OUT_LOOP:
                PUSH    BC
                LD      A,C
                CALL    COPY_ROW
                POP     BC
                PUSH    BC
                LD      A,B
                CALL    COPY_ROW
                POP     BC
                INC     C
                DEC     B
                LD      A,C
                CP      BAND_ROWS
                JR      NZ,RV_OUT_LOOP
                RET

; ----------------------------------------------------------------
; Mode 4: interlace - every fourth row, then the rows between
; ----------------------------------------------------------------
RV_LACE:
                LD      B,0                 ; starting offset 0,1,2,3
RV_LACE_PASS:
                LD      C,B
RV_LACE_LOOP:
                PUSH    BC
                LD      A,C
                CALL    COPY_ROW
                POP     BC
                LD      A,C
                ADD     A,4
                LD      C,A
                CP      BAND_ROWS
                JR      C,RV_LACE_LOOP
                INC     B
                LD      A,B
                CP      4
                JR      NZ,RV_LACE_PASS
                RET

CODEEND:

; ================================================================
; Load sequence from BASIC (band 0), assuming CLEAR 49151 and the
; code POKEd to $C000:
;
;   POKE 49176,2  : RANDOMIZE USR 49152   : REM enter ECM
;   RANDOMIZE USR 49164                   : REM fill text attributes
;   ...
;   RANDOMIZE USR 49155                   : REM black out art band
;   LOAD "ecm-atr" CODE 51200             : REM staging buffer $C800
;   LOAD "ecm-pix" CODE 16384             : REM band pixels $4000
;   POKE 49177,3 : RANDOMIZE USR 49161    : REM reveal, curtain wipe
;
; Both LOADs move 2048 bytes, taken from the header, so no length
; argument is needed. Keep attributes first in the TAP.
;
; UI painting, once in ECM:
;
;   REM hairline under the art: row 8, pixel line 0, green PAPER.
;   REM must be a paper color - a bare pixel line has no pixels
;   REM set, so an ink color shows as solid black.
;   POKE 49180,8: POKE 49181,0: POKE 49182,96: RANDOMIZE USR 49173
;
;   REM highlight menu row 20 in inverse
;   POKE 49180,20: POKE 49182,120: RANDOMIZE USR 49170
;
;   REM heat turning red - recolor row 21 without reprinting it
;   POKE 49180,21: POKE 49182,66: RANDOMIZE USR 49170
; ================================================================
