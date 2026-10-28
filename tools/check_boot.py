#!/usr/bin/env python3
"""
Boots the built TAP in an emulator and fails the build if the game does not come up.

This exists because the interesting failure is silent. A program that has grown
slightly too large still assembles, still tokenizes, and still passes check_fit -
and then wedges the machine somewhere between CLEAR and the title screen, with
the sysvars destroyed and a stripe field where the picture should be. Nothing
on the build output says anything is wrong.

check_fit models CHNG_VID's `STKEND + $1B00 <= RAMTOP` test, which is real but
is not the constraint that bites first: it was measured with about 1000 bytes
still spare on a build that would not boot. Whatever the binding constraint
actually is, it is not currently modelled, so this checks the only thing that
settles the question - run it and look.

It drives the game as far as the market screen, which exercises the whole
startup path: the CODE blocks load, the font is in place, ECM engages, the
title displays, the sector tables unpack and the first system's art band and
market table draw.

Needs ZEsarUX. Without it the check skips rather than failing, so the build
still works on a machine that has no emulator installed; set SPACETRADER_
REQUIRE_BOOT_CHECK=1 to make a missing emulator an error instead.

Usage:
    python3 tools/check_boot.py build/spacetrader.tap
"""

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

PORT = 10099          # not ZEsarUX's default, so a session you are using survives
BOOT_TIMEOUT = 90     # seconds to reach the title
STEP_TIMEOUT = 60     # seconds for each step after that

CANDIDATES = [
    "zesarux",
    "/Applications/zesarux.app/Contents/MacOS/zesarux",
    "/usr/local/bin/zesarux",
    "/opt/homebrew/bin/zesarux",
]


def find_emulator():
    for c in CANDIDATES:
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
        else:
            found = shutil.which(c)
            if found:
                return found
    return None


class Zrcp:
    """Just enough of ZEsarUX's remote protocol to read the screen."""

    PROMPT = b"command> "

    def __init__(self, port, timeout=20):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.sock.settimeout(timeout)
        self.buf = b""
        self._read()                      # banner

    def _read(self):
        while self.PROMPT not in self.buf:
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            self.buf += chunk
        out, _, rest = self.buf.partition(self.PROMPT)
        self.buf = rest
        return out.decode("utf-8", "replace")

    def cmd(self, text):
        self.sock.sendall(text.encode() + b"\n")
        return self._read().strip("\r\n")

    def screen(self):
        return self.cmd("get-ocr")

    def press(self, ch):
        code = 13 if ch == "\n" else ord(ch)
        self.cmd(f"send-keys-ascii 120 {code}")

    def close(self):
        try:
            self.sock.sendall(b"quit\n")
        except OSError:
            pass
        self.sock.close()


def connect(port, deadline):
    while time.time() < deadline:
        try:
            return Zrcp(port)
        except OSError:
            time.sleep(0.5)
    return None


def wait_for(zrcp, needles, timeout, what, nudge=None, nudge_every=3.0):
    """Wait until every string in `needles` is on screen at once.

    `nudge` presses a key periodically, for the screens that wait on one. The
    title is drawn as an image, so it reads as a blank screen here and cannot
    be waited for directly - we press past it and look for what follows.
    """
    deadline = time.time() + timeout
    next_nudge = time.time() + nudge_every
    last = ""
    while time.time() < deadline:
        last = zrcp.screen()
        if all(n in last for n in needles):
            return True, last
        if nudge and time.time() >= next_nudge:
            zrcp.press(nudge)
            next_nudge = time.time() + nudge_every
        time.sleep(0.5)
    print(f"\nFAIL: never reached {what} within {timeout}s. Last screen:\n")
    body = [ln for ln in last.split("\n") if ln.strip()]
    if body:
        for line in body:
            print(f"    |{line}")
    else:
        print("    (blank - no text on screen at all)")
    return False, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tap", type=Path)
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args()

    emulator = find_emulator()
    if emulator is None:
        msg = "   ZEsarUX not found, skipping the boot check"
        if os.environ.get("SPACETRADER_REQUIRE_BOOT_CHECK"):
            print(f"\nFAIL:{msg[3:]} (SPACETRADER_REQUIRE_BOOT_CHECK is set)")
            return 1
        print(f"{msg} (set SPACETRADER_REQUIRE_BOOT_CHECK=1 to require it)")
        return 0

    # --autorewind because the art blocks are found by name and the ROM only
    # searches forward; the TS-Pico's mount loops, an emulator's tape does not.
    proc = subprocess.Popen(
        [emulator, "--noconfigfile", "--machine", "TS2068",
         "--vo", "null", "--ao", "null", "--autorewind",
         "--enable-remoteprotocol", "--remoteprotocol-port", str(args.port),
         "--tape", str(args.tap.resolve())],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        zrcp = connect(args.port, time.time() + 30)
        if zrcp is None:
            print("\nFAIL: the emulator never opened its remote protocol port.")
            return 1

        ok, _ = wait_for(zrcp, ["NAME YOUR FREE TRADER"], BOOT_TIMEOUT,
                         "the ship-naming prompt", nudge=" ")
        if not ok:
            print("\n   The game did not get through loading, ECM and the title "
                  "screen.\n   If the program just grew, that is the first thing "
                  "to suspect: see\n   the note in this file.")
            return 1
        print("   title screen and naming prompt OK")

        zrcp.press("\n")                       # ENTER alone names her Beowulf
        ok, last = wait_for(zrcp, ["CORIOLIS GATE", "BUY SELL JUMP PORT"],
                            STEP_TIMEOUT, "the market screen")
        if not ok:
            return 1
        print("   docked at Coriolis Gate, market screen drawn")

        time.sleep(1.5)                        # let the status line finish drawing
        for row in zrcp.screen().split("\n"):
            if "CR " in row and "FUEL" in row:
                print(f"   {row.strip()}")
                break
        zrcp.close()
        return 0
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        proc.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())
