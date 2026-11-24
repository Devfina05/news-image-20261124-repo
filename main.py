#!/usr/bin/env python3
"""Place the front page of Tuesday, 24 November 2026, in one image.

The program writes the 1024x1024 newspaper-style poster that sums up
the world news of Tuesday 24 November 2026 to ``entry.png`` in the
output directory the grader reads.

The five stories on the page, each checked against the day's reporting:

  1. BUSINESS -- Jensen Huang returns as chief executive of Nvidia
     and the shares jump about 31% in a single day.
  2. DISASTER -- A fire at a candy factory in Indonesia kills at
     least 24 people; rescuers keep searching for the missing.
  3. WAR AT SEA -- The Russian cargo ship Sparta II catches fire in
     the Gulf of Finland after a drone strike.
  4. WAR -- Russian drone and missile strikes kill civilians in
     Ukraine's Kyiv region.
  5. SPORT -- The World Chess Championship opens in Geneva, with
     champion D. Gukesh defending his title against Javokhir Sindarov.

A footer strip carries three more items from the same day: the brief
ground stop at Chicago O'Hare in the Thanksgiving rush, Narendra Modi
opening an AI centre at IIT Patna, and Indian and Chinese generals
holding border talks in Arunachal Pradesh.

Why this program copies instead of drawing: the competition's rules
say a program runs with the standard library only -- nothing is
installed before it runs -- so the drawing library the first version
used (Pillow) is not there in the grader's container, and that
version exited with code 1 on its very first import. The rules name
the fix outright: the simplest entry is a repository holding the
image and a one-line program that copies it there. That is what this
does: the poster itself is committed beside this file as
``entry.png``, byte for byte the image the first version drew, and
this program copies it to the output directory. Before writing, the
image is checked (size, dimensions, PNG integrity); after writing it
is read back and compared byte for byte, so a failed write can never
pass silently. Two runs produce the same bytes.

Usage:
    MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

# ---------------------------------------------------------------- constants

WIDTH = 1024
HEIGHT = 1024
MAX_BYTES = 1_048_576
SOURCE_NAME = "entry.png"

# ---------------------------------------------------------------- validation


def die(message):
    print(f"main.py: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_png(data):
    if len(data) > MAX_BYTES:
        die(f"poster is {len(data)} bytes, over the 1 MiB limit")
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        die("poster does not start with the PNG magic bytes")
    if len(data) < 33:
        die("poster is too short to hold an IHDR chunk")
    chunk_len = struct.unpack(">I", data[8:12])[0]
    if data[12:16] != b"IHDR" or chunk_len != 13:
        die("first chunk is not a 13-byte IHDR")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != (WIDTH, HEIGHT):
        die(f"poster is {width}x{height}, expected {WIDTH}x{HEIGHT}")
    offset = 8
    saw_iend = False
    while offset < len(data):
        if offset + 8 > len(data):
            die("truncated chunk header")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        ctype = data[offset + 4:offset + 8]
        end = offset + 12 + length
        if end > len(data):
            die(f"chunk {ctype!r} runs past the end of the file")
        stored_crc = struct.unpack(">I", data[end - 4:end])[0]
        actual_crc = zlib.crc32(ctype + data[offset + 8:end - 4]) & 0xFFFFFFFF
        if stored_crc != actual_crc:
            die(f"chunk {ctype!r} has a bad CRC")
        if ctype == b"IEND":
            saw_iend = True
            if end != len(data):
                die("bytes after the IEND chunk")
            break
        offset = end
    if not saw_iend:
        die("poster has no IEND chunk")
    return width, height


def find_source():
    """Locate the committed poster next to this file, or in the cwd."""
    here = Path(__file__).resolve().parent / SOURCE_NAME
    if here.is_file():
        return here
    cwd = Path.cwd() / SOURCE_NAME
    if cwd.is_file():
        return cwd
    die(f"could not find {SOURCE_NAME} next to main.py or in the "
        f"working directory")


def main():
    source = find_source()
    data = source.read_bytes()
    width, height = check_png(data)
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"
    target.write_bytes(data)
    written = target.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if (hashlib.sha256(written).hexdigest() != digest
            or len(written) != len(data)):
        die("written copy does not match the poster byte for byte")
    print(f"wrote {target} ({width}x{height}, {len(data)} bytes, "
          f"sha256 {digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
