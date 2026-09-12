# -*- coding: utf-8 -*-
"""开机自启：HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run 键值 KebiaoReminder。

写/删该键值即可回滚，不影响系统其他项。
"""
import sys

import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "KebiaoReminder"


def _command():
    if getattr(sys, "frozen", False):  # PyInstaller 打包
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{sys.argv[0]}"'


def enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, VALUE_NAME)
            return True
    except OSError:
        return False


def set_enabled(on):
    if on:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.SetValueEx(k, VALUE_NAME, 0, winreg.REG_SZ, _command())
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, VALUE_NAME)
        except OSError:
            pass
