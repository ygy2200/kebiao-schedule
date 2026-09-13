# -*- coding: utf-8 -*-
"""Ctrl+K 命令面板：搜索并执行动作 / 跳页 / 定位课程与日程。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from PySide6.QtWidgets import QListWidgetItem
from qfluentwidgets import (BodyLabel, CaptionLabel, FluentIcon as FIF,
                            LineEdit, ListWidget, SubtitleLabel)

import db


class CommandPalette(QWidget):
    """置顶搜索面板。actions: [(icon, 标题, callable)]"""

    def __init__(self, parent_window):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._window = parent_window
        self.actions = []
        self.setWindowTitle("命令面板")

        card = QWidget(self)
        card.setObjectName("cpCard")
        card.setStyleSheet(
            "QWidget#cpCard { background: #2b2b31; border: 1px solid #3a3a42;"
            " border-radius: 12px; }")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        title = SubtitleLabel("命令面板", card)
        lay.addWidget(title)

        self.search = LineEdit(card)
        self.search.setPlaceholderText("搜索页面 / 动作 / 课程 / 日程…（Ctrl+K 唤出）")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(36)
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._run_first)
        lay.addWidget(self.search)

        self.listw = ListWidget(card)
        self.listw.setFixedHeight(280)
        self.listw.itemActivated.connect(self._run_item)
        self.listw.itemClicked.connect(self._run_item)
        lay.addWidget(self.listw)
        hint = CaptionLabel("快捷键：Ctrl+K 命令面板 · Ctrl+N 快速添加日程 · "
                            "Ctrl+1/2/3/4 切换页面")
        hint.setStyleSheet("color: #6a6a72; font-size: 10pt;")
        lay.addWidget(hint)

        self.setFixedSize(520, 448)

    def popup(self):
        """收集动作 + 显示。"""
        w = self._window
        self.actions = [
            (FIF.HOME, "打开：今日", lambda: w.switchTo(w.pages["page_today"])),
            (FIF.CALENDAR, "打开：课表", lambda: w.switchTo(w.pages["page_schedule"])),
            (FIF.DATE_TIME, "打开：月历", lambda: w.switchTo(w.pages["page_calendar"])),
            (FIF.ACCEPT, "打开：日程", lambda: w.switchTo(w.pages["page_events"])),
            (getattr(FIF, "RINGER", FIF.INFO), "打开：提醒中心",
             lambda: w.switchTo(w.pages["page_alerts"])),
            (FIF.SETTING, "打开：设置", lambda: w.switchTo(w.pages["page_settings"])),
            (FIF.ADD, "动作：添加日程（今天）",
             lambda: (w.switchTo(w.pages["page_events"]),
                      w.pages["page_events"]._add())),
            (FIF.DOWNLOAD, "动作：导入课表 xlsx",
             lambda: (w.switchTo(w.pages["page_schedule"]),
                      w.pages["page_schedule"].import_xlsx())),
            (FIF.PAUSE, "动作：暂停 / 恢复提醒", w.tray_toggle),
            (FIF.FOLDER, "动作：打开数据文件夹", w.open_data_folder),
        ]
        # 动态条目：课程 → 课表页；日程 → 日程页
        for c in db.list_courses():
            self.actions.append((FIF.CALENDAR, f"课程：{c['name']}（周{c['weekday']}）",
                                 lambda: w.switchTo(w.pages["page_schedule"])))
        for e in db.list_events():
            self.actions.append((FIF.ACCEPT, f"日程：{e['title']}（{e['date']}）",
                                 lambda: w.switchTo(w.pages["page_events"])))

        self.search.clear()
        self._filter("")
        geo = self._window.screen().availableGeometry()
        self.move(geo.center().x() - self.width() // 2,
                  geo.top() + int(geo.height() * 0.14))
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()

    def _filter(self, text):
        text = text.strip().lower()
        self.listw.clear()
        from qfluentwidgets import FluentIconBase
        for icon, title, fn in self.actions:
            if text and text not in title.lower():
                continue
            if isinstance(icon, FluentIconBase):
                it = QListWidgetItem(icon.icon(), title)
            else:
                it = QListWidgetItem(icon, title)
            it.setData(Qt.UserRole, title)
            self.listw.addItem(it)
        if self.listw.count():
            self.listw.setCurrentRow(0)

    def _run_first(self):
        it = self.listw.currentItem()
        if it:
            self._run_item(it)

    def _run_item(self, it):
        title = it.data(Qt.UserRole)
        for _icon, t, fn in self.actions:
            if t == title:
                self.hide()
                self._window.bring_up()
                fn()
                return

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape:
            self.hide()
        super().keyPressEvent(ev)
