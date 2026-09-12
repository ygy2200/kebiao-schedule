# -*- coding: utf-8 -*-
"""FluentWindow 主窗口：六页导航（M1 骨架）。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PySide6.QtGui import QIcon
from qfluentwidgets import FluentWindow, NavigationItemPosition

import icon
from app.ui.pages import (AlertsPage, CalendarPage, EventsPage, SchedulePage,
                          SettingsPage, TodayPage)

PAGES = [
    (TodayPage, 0),
    (SchedulePage, 1),
    (CalendarPage, 2),
    (EventsPage, 3),
    (AlertsPage, 4),
]
SETTINGS_INDEX = 5


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("课表日程助手")
        self.setMinimumSize(1000, 660)
        self.resize(1120, 720)
        # Mica 由 DWM 合成：PrintWindow 抓不到且深浅与 qfw 主题判定脱钩
        # （系统模式/应用模式打架，实测深窗浅卡），关闭后用实底——观感为
        # Fluent 降级形态但确定性 100%
        self.setMicaEffectEnabled(False)

        if not os.path.exists(icon.ICON_PATH):
            icon.save_icon(icon.ICON_PATH)
        self.setWindowIcon(QIcon(icon.ICON_PATH))

        self.pages = {}
        for cls, idx in PAGES:
            page = cls()
            self.pages[page.objectName()] = page
            self.addSubInterface(page, page.icon_, page.title)

        self.settings_page = SettingsPage()
        self.addSubInterface(self.settings_page, self.settings_page.icon_,
                             self.settings_page.title, NavigationItemPosition.BOTTOM)
        self.pages[self.settings_page.objectName()] = self.settings_page

        # qfw 的 FluentWindow 不自带 Mica 主题联动，必须手动接：
        # setTheme 后重设 Mica 深浅，否则窗口底色停留旧主题（实测深窗浅卡）
        from qfluentwidgets import qconfig, isDarkTheme as _qfw_dark

        def _on_theme_changed():
            try:
                self.windowEffect.setMicaEffect(self.winId(), _qfw_dark())
            except Exception:
                pass
        qconfig.themeChanged.connect(lambda *_: _on_theme_changed())

    def bring_up(self):
        self.show()
        self.raise_()
        self.activateWindow()
        for p in self.pages.values():
            p.refresh()
