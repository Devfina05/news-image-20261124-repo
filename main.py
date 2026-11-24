#!/usr/bin/env python3
"""Draw the front page of Tuesday, 24 November 2026, in one image.

The program renders a 1024x1024 newspaper-style poster that sums up
the world news of Tuesday 24 November 2026 and writes it to
``entry.png`` in the output directory the grader reads.

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

Everything is drawn with Pillow primitives from fixed coordinates, so
the program needs no network, no input files and no clock: two runs
produce the same bytes. Before writing, the rendered image is checked
(size, dimensions, PNG integrity); after writing it is read back and
compared byte for byte, so a failed write can never pass silently.

Usage:
    MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- constants

WIDTH = 1024
HEIGHT = 1024
MAX_BYTES = 1_048_576

PAPER = (247, 243, 234)
INK = (20, 20, 20)
WHITE = (255, 255, 255)
RED = (179, 38, 30)
NAVY = (27, 42, 74)
GREEN = (14, 122, 61)
GREEN_DARK = (9, 84, 42)
GOLD = (201, 162, 39)
GOLD_SOFT = (232, 196, 90)
MUTED = (96, 90, 80)
ORANGE = (224, 108, 24)
FLAME_YELLOW = (246, 196, 60)
PANEL_LINE = (20, 20, 20)

BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REGULAR_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ------------------------------------------------------------------- fonts


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default(size)


def fonts():
    return {
        "masthead": load_font(BOLD_PATH, 56),
        "dateline": load_font(BOLD_PATH, 30),
        "kicker": load_font(BOLD_PATH, 19),
        "lead_head": load_font(BOLD_PATH, 46),
        "head": load_font(BOLD_PATH, 29),
        "body": load_font(REGULAR_PATH, 21),
        "lead_body": load_font(REGULAR_PATH, 24),
        "footer": load_font(REGULAR_PATH, 20),
        "footer_bold": load_font(BOLD_PATH, 20),
        "chip": load_font(BOLD_PATH, 30),
    }


# -------------------------------------------------------------- text tools


def wrap_text(draw, text, font, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_wrapped(draw, x, y, text, font, fill, max_width, line_gap=6):
    lines = wrap_text(draw, text, font, max_width)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def centred(draw, cx, y, text, font, fill):
    width = draw.textlength(text, font=font)
    draw.text((cx - width / 2, y), text, font=font, fill=fill)
    return y + font.size


# ------------------------------------------------------------------ icons


def draw_chip(draw, x, y, w, h):
    """A green processor with pins and a rising share-price line."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=14,
                           fill=GREEN_DARK, outline=INK, width=3)
    inner = 14
    draw.rounded_rectangle([x + inner, y + inner, x + w - inner,
                            y + h - inner], radius=8, fill=GREEN)
    for i in range(4):
        px = x + 30 + i * 52
        draw.rectangle([px, y - 12, px + 16, y], fill=GOLD)
        draw.rectangle([px, y + h, px + 16, y + h + 12], fill=GOLD)
    for i in range(3):
        py = y + 28 + i * 52
        draw.rectangle([x - 12, py, x, py + 16], fill=GOLD)
        draw.rectangle([x + w, py, x + w + 12, py + 16], fill=GOLD)
    label = "NVDA"
    lw = draw.textlength(label, font=load_font(BOLD_PATH, 30))
    draw.text((x + (w - lw) / 2, y + h / 2 - 34), label,
              font=load_font(BOLD_PATH, 30), fill=WHITE)
    # Rising line: the day's ~31% jump.
    pts = [(x + 26, y + h - 34), (x + 66, y + h - 52),
           (x + 106, y + h - 46), (x + 146, y + h - 74),
           (x + 186, y + h - 96)]
    draw.line(pts, fill=GOLD_SOFT, width=5, joint="curve")
    tip = pts[-1]
    draw.polygon([(tip[0] - 2, tip[1] - 12), (tip[0] + 14, tip[1] - 2),
                  (tip[0] - 2, tip[1] + 2)], fill=GOLD_SOFT)


def draw_flame(draw, cx, top, size):
    """A stylised flame, orange outside and yellow inside."""
    s = size
    outer = [(cx, top), (cx + 0.42 * s, top + 0.42 * s),
             (cx + 0.30 * s, top + 0.62 * s), (cx + 0.52 * s, top + 0.72 * s),
             (cx + 0.28 * s, top + s), (cx - 0.28 * s, top + s),
             (cx - 0.52 * s, top + 0.72 * s), (cx - 0.30 * s, top + 0.62 * s),
             (cx - 0.42 * s, top + 0.42 * s)]
    draw.polygon(outer, fill=ORANGE)
    inner = [(cx, top + 0.34 * s), (cx + 0.26 * s, top + 0.66 * s),
             (cx + 0.16 * s, top + 0.80 * s), (cx - 0.16 * s, top + 0.80 * s),
             (cx - 0.26 * s, top + 0.66 * s)]
    draw.polygon(inner, fill=FLAME_YELLOW)


def draw_ship(draw, x, y, w, h):
    """A cargo ship on the water with smoke and a flame above it."""
    s = w / 180.0
    hull_top = y + h * 0.52
    draw.polygon([(x, hull_top), (x + w, hull_top),
                  (x + w - 18 * s, y + h), (x + 18 * s, y + h)], fill=NAVY)
    draw.rectangle([x + 14 * s, y + h * 0.18, x + 62 * s, hull_top],
                   fill=RED)
    draw.rectangle([x + 70 * s, y + h * 0.30, x + 118 * s, hull_top],
                   fill=GOLD)
    draw.rectangle([x + 126 * s, y + h * 0.10, x + 150 * s, hull_top],
                   fill=WHITE)
    draw.rectangle([x + 126 * s, y + h * 0.10, x + 150 * s, y + h * 0.24],
                   fill=NAVY)
    # Smoke puffs and a flame where the strike hit.
    for sx, sy, r in [(x + 96 * s, y + 6 * s, 13 * s),
                      (x + 122 * s, y - 2 * s, 16 * s),
                      (x + 150 * s, y + 8 * s, 12 * s)]:
        draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=MUTED)
    draw_flame(draw, x + 96 * s, y + 18 * s, 34 * s)
    # Water lines.
    for wy in [y + h + 8 * s, y + h + 18 * s]:
        draw.line([(x + 6 * s, wy), (x + w - 6 * s, wy)], fill=NAVY,
                  width=max(2, int(3 * s)))


def draw_burst(draw, cx, cy, r, fill):
    """A twelve-point starburst, for the strike on the Kyiv region."""
    import math
    points = []
    for i in range(24):
        angle = math.pi * i / 12
        radius = r if i % 2 == 0 else r * 0.45
        points.append((cx + radius * math.cos(angle),
                       cy + radius * math.sin(angle)))
    draw.polygon(points, fill=fill)


def draw_chessboard(draw, x, y, size):
    """A 4x4 board with a white king standing on it."""
    cell = size // 4
    for row in range(4):
        for col in range(4):
            colour = WHITE if (row + col) % 2 == 0 else INK
            draw.rectangle([x + col * cell, y + row * cell,
                            x + (col + 1) * cell, y + (row + 1) * cell],
                           fill=colour, outline=INK, width=1)
    kx, ky = x + size + 16, y + 8
    draw.ellipse([kx, ky, kx + 58, ky + 58], fill=WHITE,
                 outline=INK, width=3)
    draw.text((kx + 19, ky + 8), "K", font=load_font(BOLD_PATH, 38),
              fill=INK)


def draw_chess_mini(draw, x, y, size):
    """A small 2x2 board, for the corner of the chess panel."""
    cell = size // 2
    for row in range(2):
        for col in range(2):
            colour = WHITE if (row + col) % 2 == 0 else INK
            draw.rectangle([x + col * cell, y + row * cell,
                            x + (col + 1) * cell, y + (row + 1) * cell],
                           fill=colour, outline=INK, width=2)


# ------------------------------------------------------------------ panels


def panel(draw, x, y, w, h):
    draw.rectangle([x, y, x + w, y + h], fill=WHITE,
                   outline=PANEL_LINE, width=3)


def story_panel(draw, f, x, y, w, h, kicker, headline, body,
                icon=None):
    """One news panel: kicker, headline, body text, optional corner art.

    When an icon is given it is drawn in the top-right corner and the
    headline starts below it, so words and pictures never overlap.
    """
    panel(draw, x, y, w, h)
    pad = 20
    text_x = x + pad
    text_w = w - 2 * pad
    cursor = y + 16
    if icon is not None:
        icon(draw, x + w - 64, y + 12)
        cursor = y + 60
    else:
        draw.text((text_x, cursor), kicker, font=f["kicker"], fill=RED)
        cursor += f["kicker"].size + 10
        cursor = draw_wrapped(draw, text_x, cursor, headline, f["head"],
                              INK, text_w, line_gap=4)
        cursor += 6
        draw_wrapped(draw, text_x, cursor, body, f["body"], INK, text_w)
        return
    draw.text((text_x, y + 16), kicker, font=f["kicker"], fill=RED)
    cursor = draw_wrapped(draw, text_x, cursor, headline, f["head"],
                          INK, text_w, line_gap=4)
    cursor += 6
    draw_wrapped(draw, text_x, cursor, body, f["body"], INK, text_w)


# ------------------------------------------------------------------- poster


def render_poster():
    img = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(img)
    f = fonts()

    # Masthead: black band, paper title, gold dateline.
    draw.rectangle([0, 0, WIDTH, 118], fill=INK)
    centred(draw, WIDTH // 2, 14, "THE WORLD IN ONE IMAGE",
            f["masthead"], WHITE)
    centred(draw, WIDTH // 2, 76, "TUESDAY, 24 NOVEMBER 2026",
            f["dateline"], GOLD_SOFT)
    draw.rectangle([0, 118, WIDTH, 124], fill=RED)

    # Lead story: Nvidia. Art on the left, words on the right.
    lx, ly, lw, lh = 24, 136, 976, 316
    panel(draw, lx, ly, lw, lh)
    draw_chip(draw, lx + 28, ly + 78, 210, 160)
    tx = lx + 272
    tw = lw - 272 - 28
    cy = ly + 20
    draw.text((tx, cy), "BUSINESS  ·  SANTA CLARA, USA",
              font=f["kicker"], fill=RED)
    cy += f["kicker"].size + 12
    draw.text((tx, cy), "HUANG IS BACK", font=f["lead_head"], fill=INK)
    cy += f["lead_head"].size + 12
    cy = draw_wrapped(draw, tx, cy,
                      "Jensen Huang returns as Nvidia chief — "
                      "shares soar about 31% in a day.",
                      f["lead_body"], INK, tw, line_gap=6)
    cy += 8
    draw_wrapped(draw, tx, cy,
                 "The board reinstates its co-founder after an inquiry, "
                 "and Wall Street cheers the comeback.",
                 f["body"], MUTED, tw, line_gap=4)

    # Middle row: the factory fire and the ship on fire.
    my, mh = 464, 236
    pw = 476
    story_panel(draw, f, 24, my, pw, mh,
                "DISASTER  ·  INDONESIA",
                "24 KILLED IN FACTORY FIRE",
                "A blaze at a candy factory kills at least 24 people; "
                "rescuers keep searching for the missing.",
                icon=lambda d, ix, iy: draw_flame(d, ix + 22, iy, 44))
    story_panel(draw, f, 524, my, pw, mh,
                "WAR AT SEA  ·  GULF OF FINLAND",
                "SHIP ABLAZE AFTER DRONE STRIKE",
                "The Russian cargo ship Sparta II catches fire after a "
                "drone attack in the Gulf of Finland.",
                icon=lambda d, ix, iy: draw_ship(d, ix - 28, iy + 8, 92, 44))

    # Bottom row: Kyiv and the chess championship.
    by, bh = 712, 216
    story_panel(draw, f, 24, by, pw, bh,
                "WAR  ·  UKRAINE",
                "KYIV REGION HIT",
                "Russian drone and missile strikes kill civilians in the "
                "Kyiv region.",
                icon=lambda d, ix, iy: draw_burst(d, ix + 22, iy + 22,
                                                  24, RED))
    story_panel(draw, f, 524, by, pw, bh,
                "SPORT  ·  GENEVA",
                "CHESS CROWN ON THE LINE",
                "The World Chess Championship opens in Geneva: Gukesh "
                "defends his crown vs Sindarov.",
                icon=lambda d, ix, iy: draw_chess_mini(d, ix, iy, 44))

    # Footer: three more items from the same day.
    draw.rectangle([0, 940, WIDTH, HEIGHT], fill=NAVY)
    draw_wrapped(draw, 24, 952,
                 "ALSO TODAY:  O'Hare ground stop amid the Thanksgiving "
                 "rush  ·  Modi opens an AI centre at IIT Patna  ·  "
                 "India–China generals hold border talks",
                 f["footer"], WHITE, WIDTH - 48, line_gap=4)

    return img


# -------------------------------------------------------------- validation


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


def main():
    import io
    image = render_poster()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    data = buffer.getvalue()
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
