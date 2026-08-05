#!/usr/bin/env python3
"""Generate icon.png for Pulse: a heartbeat line on a dark rounded tile.

Pure-stdlib PNG writer (zlib + struct), 256x256. Rounded box via SDF,
heartbeat polyline via point-to-segment distance with a soft glow.
"""

import struct
import zlib
from pathlib import Path

SIZE = 256
HERE = Path(__file__).parent

BG = (30, 32, 42, 255)
LINE = (255, 107, 107, 255)   # pulse red
GLOW = (255, 107, 107, 90)

# heartbeat polyline (x, y) — flat, spike up, spike down, settle, flat
PTS = [(12, 140), (78, 140), (96, 92), (106, 176), (116, 84), (126, 164),
       (134, 132), (148, 132), (244, 132)]


def rounded_box_sdf(x, y, cx, cy, hw, hh, r):
    dx = abs(x - cx) - (hw - r)
    dy = abs(y - cy) - (hh - r)
    ox, oy = max(dx, 0.0), max(dy, 0.0)
    return min(max(dx, dy), 0.0) + (ox * ox + oy * oy) ** 0.5 - r


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / (vx * vx + vy * vy)))
    dx, dy = wx - t * vx, wy - t * vy
    return (dx * dx + dy * dy) ** 0.5


def pixel(x, y):
    px, py = x + 0.5, y + 0.5
    if rounded_box_sdf(px, py, 128, 128, 112, 112, 52) > 0:
        return (0, 0, 0, 0)

    d = min(seg_dist(px, py, PTS[i][0], PTS[i][1], PTS[i + 1][0], PTS[i + 1][1])
            for i in range(len(PTS) - 1))
    if d <= 2.2:
        return LINE
    if d <= 7:
        t = 1.0 - (d - 2.2) / 4.8
        return tuple(int(a + (b - a) * (1 - t)) for a, b in zip(LINE, GLOW, strict=True))
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
