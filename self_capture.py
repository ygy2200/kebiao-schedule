# -*- coding: utf-8 -*-
"""真实窗口渲染抓图：PrintWindow(PW_RENDERFULLCONTENT) 走系统真实绘制，存 PNG。

用途：终局定责 grab() 渲染怪癖——本脚本产出的是窗口真实像素。
用法: python self_capture.py
"""
import ctypes
import os
import sys
import zlib
from ctypes import wintypes

from PySide6.QtCore import QTimer

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


def capture_window(hwnd, path):
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    ok = user32.PrintWindow(hwnd, mem, 2)  # PW_RENDERFULLCONTENT
    bmi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    raw = buf.raw
    rows = []
    stride = w * 4
    for y in range(h):
        row = bytearray(raw[y * stride:(y + 1) * stride])
        for x in range(0, stride, 4):  # BGRA -> RGBA
            row[x], row[x + 2] = row[x + 2], row[x]
        rows.append(b"\x00" + bytes(row))
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", __import__("struct").pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(b"".join(rows), 6))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return ok, w, h


def _chunk(tag, data):
    c = tag + data
    return __import__("struct").pack(">I", len(data)) + c + __import__("struct").pack(">I", zlib.crc32(c))


def find_hwnd(title_substr):
    found = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _lp):
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            b = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, b, n + 1)
            if title_substr in b.value and user32.IsWindowVisible(hwnd):
                found.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    return found[0] if found else None


def main():
    app_qt = __import__("PySide6.QtWidgets", fromlist=["QApplication"]).QApplication(sys.argv)
    import db
    import main_window
    db.init_db()
    win = main_window.MainWindow()
    win.show()
    plan = [("real_light.png", None), ("real_dark.png", "dark"),
            ("real_events.png", None), ("real_settings.png", None),
            ("real_dialog_course.png", "dlg_course"),
            ("real_dialog_event.png", "dlg_event")]
    it = iter(plan)

    def step():
        try:
            name, mode = next(it)
        except StopIteration:
            QTimer.singleShot(800, lambda: os._exit(0))  # item view+QSS 下 quit 可能挂起
            app_qt.quit()
            return
        if mode and mode not in ("dlg_course", "dlg_event"):
            import db as _db
            _db.set_setting("theme_mode", mode)
        else:
            import db as _db
            _db.set_setting("theme_mode", "auto")
        win.apply_theme(force_solid=True)
        dlg = None
        if name == "real_dialog_course.png":
            win.nav.setCurrentRow(0)
            from page_schedule import CourseDialog
            dlg = CourseDialog(win)
            dlg.show()
        elif name == "real_dialog_event.png":
            win.nav.setCurrentRow(1)
            from page_events import EventDialog
            dlg = EventDialog(win)
            dlg.show()
        elif name == "real_events.png":
            win.nav.setCurrentRow(1)
        elif name == "real_settings.png":
            win.nav.setCurrentRow(2)
        else:
            win.nav.setCurrentRow(0)

        def grab():
            if dlg is not None:
                titles = {"real_dialog_course.png": "添加课程",
                          "real_dialog_event.png": "添加日程"}
                hwnd = find_hwnd(titles[name])
                if hwnd:
                    ok, w, h = capture_window(hwnd, name)
                    print(f"{name}: {w}x{h} ok={ok}")
                else:
                    print(f"{name}: DIALOG NOT FOUND")
                dlg.close()
                QTimer.singleShot(400, step)
                return
            hwnd = find_hwnd("课表日程助手")
            if hwnd:
                ok, w, h = capture_window(hwnd, name)
                print(f"{name}: hwnd={hwnd} {w}x{h} PrintWindow_ok={ok}")
            else:
                print(f"{name}: WINDOW NOT FOUND")
            QTimer.singleShot(400, step)

        QTimer.singleShot(700, grab)

    QTimer.singleShot(2500, step)
    app_qt.exec()


if __name__ == "__main__":
    main()
