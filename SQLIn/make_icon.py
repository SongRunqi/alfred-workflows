#!/usr/bin/env python3
"""Generate icon.png for SQL In: "IN" in light blue on a dark rounded tile.

Pure-stdlib PNG writer (zlib + struct), 256x256. Rounded box via SDF,
5x7 bitmap font scaled up, soft glow around the glyphs.
"""

import struct
import zlib
from pathlib import Path

SIZE = 256
HERE = Path(__file__).parent

BG = (30, 32, 42, 255)
GLYPH = (120, 200, 255, 255)  # light SQL blue
GLOW = (120, 200, 255, 70)

# 5x7 bitmap font — glyphs for "IN"
FONT = {
    "I": [
        "..X..",
        "..X..",
        "..X..",
        "..X..",
        "..X..",
        "..X..",
        "..X..",
    ],
    "N": [
        "X...X",
        "XX..X",
        "X.X.X",
        "X..XX",
        "X...X",
        "X...X",
        "X...X",
    ],
}
GLYPH_W, GLYPH_H = 5, 7
GAP = 3  # empty columns between glyphs


def rounded_box_sdf(x, y, cx, cy, hw, hh, r):
    dx = abs(x - cx) - (hw - r)
    dy = abs(y - cy) - (hh - r)
    ox, oy = max(dx, 0.0), max(dy, 0.0)
    return min(max(dx, dy), 0.0) + (ox * ox + oy * oy) ** 0.5 - r


def glyph_pixels(text, scale, cx, cy):
    """Yield (x, y) pixel coordinates of lit glyph cells, centered at (cx, cy)."""
    total_w = (len(text) * GLYPH_W + (len(text) - 1) * GAP) * scale
    total_h = GLYPH_H * scale
    x0 = round(cx - total_w / 2)
    y0 = round(cy - total_h / 2)
    for gi, ch in enumerate(text):
        rows = FONT[ch]
        for row in range(GLYPH_H):
            for col in range(GLYPH_W):
                if rows[row][col] == "X":
                    px = x0 + (gi * (GLYPH_W + GAP) + col) * scale
                    py = y0 + row * scale
                    for dx in range(scale):
                        for dy in range(scale):
                            yield px + dx, py + dy


def pixel(x, y):
    px, py = x + 0.5, y + 0.5
    if rounded_box_sdf(px, py, 128, 128, 112, 112, 52) > 0:
        return (0, 0, 0, 0)

    scale = 18
    lit = set(glyph_pixels("IN", scale, 128, 128))

    # glow: 1px border around lit cells
    if (x, y) not in lit:
        for nx in (x - 1, x, x + 1):
            for ny in (y - 1, y, y + 1):
                if (nx, ny) in lit:
                    return GLOW
        return BG
    return GLYPH


def write_png(path, pixels):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(
        b"\x00" + b"".join(struct.pack("4B", *p) for p in row) for row in pixels
    )
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


pixels = [[pixel(x, y) for x in range(SIZE)] for y in range(SIZE)]
out = HERE / "icon.png"
write_png(out, pixels)
print(f"wrote {out}")
