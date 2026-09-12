# -*- coding: utf-8 -*-
"""提醒中心（M6）：触发留痕列表 + 未读标识 + 全部已读。"""
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import (BodyLabel, CaptionLabel, CardWidget, FluentIcon as FIF,
                            PrimaryPushButton, StrongBodyLabel, SubtitleLabel,
                            TitleLabel, isDarkTheme)

import db
from app.ui import tokens


class AlertsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("page_alerts")
        self.icon_ = getattr(FIF, "RINGER", FIF.INFO)
        self.title = "提醒中心"
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(tokens.SPACE["xl"], tokens.SPACE["l"],
                                tokens.SPACE["xl"], tokens.SPACE["m"])
        root.setSpacing(tokens.SPACE["m"])
        root.addWidget(TitleLabel("提醒中心"))
        self.sub = CaptionLabel("每次课前/日程提醒都会留痕")
        root.addWidget(self.sub)

        bar = QHBoxLayout()
        self.btn_read = PrimaryPushButton("全部标记已读")
        self.btn_read.clicked.connect(self._mark_all)
        bar.addWidget(self.btn_read)
        bar.addStretch(1)
        root.addLayout(bar)

        from PySide6.QtWidgets import QScrollArea, QFrame
        self.list_lay = QVBoxLayout()
        self.list_lay.setSpacing(tokens.SPACE["s"])
        holder = QWidget()
        holder.setLayout(self.list_lay)
        scroll = QScrollArea()
        scroll.setWidget(holder)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll, 1)

    def refresh(self):
        while self.list_lay.count():
            item = self.list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        dark = isDarkTheme()
        mode = "dark" if dark else "light"
        items = db.list_reminders()
        if not items:
            tip = BodyLabel("还没有提醒记录 · 课前提醒会自动出现在这里")
            tip.setStyleSheet("color: " + tokens.NEUTRAL[mode]["text3"])
            self.list_lay.addWidget(tip)
        unread = sum(1 for r in items if not r["read"])
        self.sub.setText(f"每次课前/日程提醒都会留痕"
                         + (f" · 未读 {unread}" if unread else ""))

        for r in items:
            card = CardWidget(self)
            accent = tokens.ACCENT[mode]
            dot_color = accent if not r["read"] else tokens.NEUTRAL[mode]["text3"]
            card.setStyleSheet(
                f"CardWidget {{ background: {tokens.NEUTRAL[mode]['layer1']};"
                f" border-left: 3px solid {dot_color}; border-radius: 8px; }}")
            lay = QHBoxLayout(card)
            lay.setContentsMargins(tokens.SPACE["l"], tokens.SPACE["s"],
                                   tokens.SPACE["s"], tokens.SPACE["s"])
            info = QVBoxLayout()
            info.setSpacing(1)
            kind_cn = {"course": "下节课", "event": "日程提醒"}.get(r["kind"], r["kind"])
            title = StrongBodyLabel(f"{kind_cn} · {r['title']}")
            meta = CaptionLabel(f"{r['fired_at'][:16].replace('T', ' ')}  ·  {r['detail']}")
            meta.setStyleSheet("color: " + tokens.NEUTRAL[mode]["text2"])
            info.addWidget(title)
            info.addWidget(meta)
            lay.addLayout(info, 1)
            if not r["read"]:
                dot = CaptionLabel("未读")
                dot.setStyleSheet(f"color: {accent};")
                lay.addWidget(dot)
            self.list_lay.addWidget(card)
        self.list_lay.addStretch(1)

    def _mark_all(self):
        for r in db.list_reminders(only_unread=True):
            db.update_reminder(r["id"], read=1)
        self.refresh()

    def showEvent(self, ev):
        super().showEvent(ev)
        self.refresh()

    def ensure_built(self):
        pass
