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
        menu.addSeparator()
        menu.addAction(act_quit)
        menu.setStyleSheet(menu.styleSheet())
        self.setContextMenu(menu)
        self.activated.connect(self._activated)

    def _activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # 左键单击
            self.window.bring_up()

    @property
    def paused(self):
        return self.act_pause.isChecked()
