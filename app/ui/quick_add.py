# -*- coding: utf-8 -*-
"""Alt+A 全局热键快速添加日程：迷你置顶窗（标题+日期+时间，回车即存）。"""
import datetime as dt

from PySide6.QtCore import QObject, Qt, QTime, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QHBoxLayout, QVBoxLayout, QWidget)

from qfluentwidgets import (BodyLabel, FluentIcon as FIF, LineEdit,
                            PrimaryPushButton, TimePicker)

import db
import icon


class _HotkeyBridge(QObject):
    """keyboard 回调在子线程，经信号转回主线程。"""
    triggered = Signal()


class QuickAddWindow(QWidget):
    def __init__(self, on_saved=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.on_saved = on_saved
        self.setWindowTitle("快速添加日程")

        card = QWidget(self)
        card.setObjectName("qaCard")
        card.setStyleSheet(
            "QWidget#qaCard { background: #2b2b31; border: 1px solid #3a3a42;"
            " border-radius: 12px; }")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        self.title_edit = LineEdit(card)
        self.title_edit.setPlaceholderText("要做什么？（回车保存）")
        self.title_edit.setClearButtonEnabled(True)
        self.title_edit.setMinimumHeight(34)
        self.title_edit.returnPressed.connect(self._save)
        lay.addWidget(self.title_edit)

        time_row = QHBoxLayout()
        time_row.setSpacing(8)
        self.time_pick = TimePicker(card)
        self.time_pick.setTime(QTime(9, 0))
        self.time_pick.setMinimumHeight(34)
        time_row.addWidget(BodyLabel("时间", card))
        time_row.addWidget(self.time_pick, 1)
        save_btn = PrimaryPushButton("保存", card)
        save_btn.setMinimumHeight(34)
        save_btn.clicked.connect(self._save)
        time_row.addWidget(save_btn)
        lay.addLayout(time_row)

        self.setFixedSize(380, 150)
        self.setWindowIcon(QIcon(icon.ICON_PATH))

    def popup(self):
        """屏幕中上方显示并聚焦标题框。"""
        geo = self.screen().availableGeometry()
        self.move(geo.center().x() - self.width() // 2,
                  geo.top() + int(geo.height() * 0.18))
        self.title_edit.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        self.title_edit.setFocus()

    def _save(self):
        title = self.title_edit.text().strip()
        if not title:
            return
        t = self.time_pick.time()
        db.add_event(title, dt.date.today().isoformat(), t.toString("HH:mm"), 10, "")
        self.hide()
        self.title_edit.clear()
        if self.on_saved:
            self.on_saved()

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape:
            self.hide()
        super().keyPressEvent(ev)


class GlobalHotkeyManager:
    """Alt+A 全局热键。keyboard 回调在子线程触发，经信号切回主线程。"""

    def __init__(self, on_trigger):
        self.bridge = _HotkeyBridge()
        self.bridge.triggered.connect(on_trigger)
        self.ok = False

    HOTKEY = "ctrl+alt+a"  # 默认 Ctrl+Alt+A（Alt+A 与大量软件冲突）

    def register(self):
        try:
            import keyboard
            keyboard.add_hotkey(self.HOTKEY, lambda: self.bridge.triggered.emit(),
                                suppress=False)
            self.ok = True
        except Exception:
            self.ok = False
        return self.ok
