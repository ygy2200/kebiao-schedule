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
        # 侧边栏：展开宽度收窄 + 持久展开（点汉堡切换，不自动收起）
        self.navigationInterface.setExpandWidth(190)
        self.navigationInterface.setCollapsible(False)
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

    def showEvent(self, ev):
        super().showEvent(ev)
        # 从托盘恢复时关闭按钮可能残留 hover 红态（无 leave 事件），强制清除
        try:
            from PySide6.QtCore import QEvent
            app = QApplication.instance()
            for btn in (self.titleBar.closeBtn, self.titleBar.minBtn,
                        self.titleBar.maxBtn):
                if btn.underMouse():
                    continue
                btn.setAttribute(Qt.WA_UnderMouse, False)
                app.sendEvent(btn, QEvent(QEvent.Leave))
                btn.update()
        except Exception:
            pass

    def bring_up(self):
        self.show()
        self.raise_()
        self.activateWindow()
        for p in self.pages.values():
            p.refresh()

    # ---------- 效率层挂钩 ----------

    def tray_toggle(self):
        """托盘提醒暂停/恢复（InfoBar 反馈）。"""
        if not getattr(self, "tray", None):
            return
        new_state = not self.tray.paused
        self.tray.act_pause.setChecked(new_state)
        from qfluentwidgets import InfoBar
        if new_state:
            InfoBar.warning("提醒已暂停", "托盘菜单可恢复", duration=3000, parent=self)
        else:
            InfoBar.success("提醒已恢复", None, duration=3000, parent=self)

    def open_data_folder(self):
        import subprocess
        import db
        subprocess.Popen(["explorer", "/select,", db.DB_PATH])

    def setup_shortcuts(self, tray):
        """main.py 注入 tray 后调用：Ctrl+K 命令面板等。"""
        self.tray = tray
        from PySide6.QtGui import QKeySequence, QShortcut
        from app.ui.command_palette import CommandPalette
        self._palette = CommandPalette(self)
        sc = QShortcut(QKeySequence("Ctrl+K"), self)
        sc.activated.connect(self._palette.popup)
        # Ctrl+N 快速添加日程（选中日）；Ctrl+1-4 切页
        QShortcut(QKeySequence("Ctrl+N"), self,
                  activated=self.pages["page_events"]._add)
        for i, name in enumerate(["page_today", "page_schedule", "page_calendar",
                                  "page_events"], start=1):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self,
                      activated=lambda name=name: self.switchTo(self.pages[name]))
