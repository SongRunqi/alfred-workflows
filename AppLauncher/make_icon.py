#!/usr/bin/env python3
"""Generate icon.png for App Launcher: a 3x3 key-cap grid, one cap lit.

Pure-stdlib PNG writer (zlib + struct), 256x256. Rounded boxes via SDF.
"""

import struct
import zlib
from pathlib import Path

SIZE = 256
HERE = Path(__file__).parent

# palette
BG = (30, 32, 42, 255)          # deep slate
CAP = (64, 68, 86, 255)         # key cap
CAP_TOP = (88, 93, 118, 255)    # key cap top bevel
ACCENT = (255, 158, 60, 255)    # Alfred orange — the lit key
ACCENT_TOP = (255, 190, 110, 255)
SHADOW = (12, 13, 18, 120)


def rounded_box_sdf(x, y, cx, cy, hw, hh, r):
    """Signed distance to a rounded box; <=0 inside."""
    dx = abs(x - cx) - (hw - r)
    dy = abs(y - cy) - (hh - r)
    ox, oy = max(dx, 0.0), max(dy, 0.0)
    return min(max(dx, dy), 0.0) + (ox * ox + oy * oy) ** 0.5 - r


def lerp(a, b, t):
    """Linear blend of two 4-channel colors."""
    if len(a) != 4 or len(b) != 4:
        raise ValueError("lerp requires 4-channel RGBA colors")
    return tuple(int(a_c + (b_c - a_c) * t) for a_c, b_c in zip(a, b, strict=True))


def pixel(x, y):
    px, py = x + 0.5, y + 0.5

    # rounded background
    bg = rounded_box_sdf(px, py, 128, 128, 112, 112, 52)
    if bg > 0:
        return (0, 0, 0, 0)

    color = BG
    # key caps: 3x3 grid centered
    for row in range(3):
        for col in range(3):
            cx = 70 + col * 58
            cy = 70 + row * 58
            d = rounded_box_sdf(px, py, cx, cy, 22, 22, 9)
            if d <= 0:
                # keycap: top bevel + body + bottom shadow
                if py < cy - 6:
                    t = 1 - (cy - 6 - py) / 8
                    color = lerp(CAP_TOP, CAP, max(0.0, min(1.0, t)))
                elif py > cy + 10:
                    t = (py - cy - 10) / 8
                    color = lerp(CAP, SHADOW, max(0.0, min(1.0, t)))
                else:
                    color = CAP
                if col == 1 and row == 1:  # center key lit
                    if py < cy - 4:
                        color = lerp(ACCENT_TOP, ACCENT, 0.4)
                    else:
                        color = ACCENT
                return color

    return BG


def write_png(path, pixels):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(
        b"\x00" + b"".join(struct.pack("4B", *p) for p in row)
        for row in pixels
    )
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


pixels = [[pixel(x, y) for x in range(SIZE)] for y in range(SIZE)]
out = HERE / "icon.png"
write_png(out, pixels)
print(f"wrote {out}")
