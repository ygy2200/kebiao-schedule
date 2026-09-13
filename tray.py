# -*- coding: utf-8 -*-
"""系统托盘：图标 + 右键菜单（打开 / 暂停提醒 / 退出）。"""
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class TrayIcon(QSystemTrayIcon):
    def __init__(self, icon_path, window, on_quit):
        super().__init__(QIcon(icon_path))
        self.window = window
        menu = QMenu()
        act_open = QAction("打开主窗口", menu)
        act_open.triggered.connect(window.bring_up)
        self.act_pause = QAction("暂停提醒", menu)
        self.act_pause.setCheckable(True)
        act_quit = QAction("退出", menu)
        act_quit.triggered.connect(on_quit)
        menu.addAction(act_open)
        menu.addAction(self.act_pause)
        self.act_quick = QAction("快速添加日程", menu)
        self.act_quick.setVisible(False)
        self.act_quick.triggered.connect(self._quick_add)
        menu.addAction(self.act_quick)
        menu.addSeparator()
        menu.addAction(act_quit)
        self._quick_add_fn = None
        menu.setStyleSheet(menu.styleSheet())
        self.setContextMenu(menu)
        self.activated.connect(self._activated)

    def _activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # 左键单击：快速今日面板
            from app.ui.tray_panel import QuickTodayPanel
            from PySide6.QtGui import QCursor
            panel = QuickTodayPanel(on_open_main=self.window.bring_up)
            panel.popup_at(QCursor.pos())
        elif reason == QSystemTrayIcon.DoubleClick:
            self.window.bring_up()

    def set_quick_add(self, fn):
        """注入快速添加迷你窗的弹出函数并显示菜单项。"""
        self._quick_add_fn = fn
        self.act_quick.setVisible(fn is not None)

    def _quick_add(self):
        if self._quick_add_fn:
            self._quick_add_fn()

    @property
    def paused(self):
        return self.act_pause.isChecked()
