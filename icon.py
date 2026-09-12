# -*- coding: utf-8 -*-
"""纯标准库生成应用图标（蓝底日历），不依赖 PIL。"""
import os
import struct
import sys
import zlib

SIZE = 256
_BLUE = (0, 103, 192, 255)
_WHITE = (255, 255, 255, 255)
_SHEET = (250, 250, 252, 255)
_GRAY = (96, 105, 120, 255)
_TRANSPARENT = (0, 0, 0, 0)


def _put(px, x, y, color):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        px[y * SIZE + x] = color


def _blend(px, x, y, color, alpha):
    x0, y0, b = px[y * SIZE + x]
    a = color[3] * alpha / 255
    px[y * SIZE + x] = (
        int(x0 * (255 - a) + color[0] * a),
        int(y0 * (255 - a) + color[1] * a),
        int(b * (255 - a) + color[2] * a),
        255,
    )


def _rounded(px, x0, y0, x1, y1, r, color):
    for y in range(max(0, y0), min(SIZE, y1)):
        for x in range(max(0, x0), min(SIZE, x1)):
            # 圆角判定：四角区域到圆心的距离
            cx = min(max(x, x0 + r), x1 - r)
            cy = min(max(y, y0 + r), y1 - r)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                _put(px, x, y, color)


def _png(png_px):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    raw = b"".join(b"\x00" + bytes(v for p in png_px[y * SIZE:(y + 1) * SIZE] for v in p)
                   for y in range(SIZE))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def make_icon_bytes():
    px = [_TRANSPARENT] * (SIZE * SIZE)
    # 蓝色圆底
    _rounded(px, 8, 8, SIZE - 8, SIZE - 8, 56, _BLUE)
    # 白色日历纸
    _rounded(px, 44, 64, SIZE - 44, SIZE - 40, 28, _SHEET)
    # 蓝色表头（覆盖纸张顶部，配圆角）
    _rounded(px, 44, 64, SIZE - 44, 112, 28, _BLUE)
    _rounded(px, 44, 96, SIZE - 44, 118, 0, _BLUE)
    # 两个装订环
    _rounded(px, 84, 44, 100, 96, 8, _WHITE)
    _rounded(px, 156, 44, 172, 96, 8, _WHITE)
    # 网格点（3 列 2 行）
    for gy in (148, 192):
        for gx in (72, 120, 168):
            _rounded(px, gx, gy, gx + 20, gy + 20, 6, _GRAY)
    return _png(px)


def save_icon(path):
    png = make_icon_bytes()
    ico = (struct.pack("<HHH", 0, 1, 1)
           + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22)
           + png)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(ico)
    return path


if getattr(sys, "frozen", False):
    ICON_PATH = os.path.join(os.path.dirname(sys.executable), "app.ico")
else:
    ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico")

if __name__ == "__main__":
    print(save_icon(ICON_PATH))
