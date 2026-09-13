# -*- coding: utf-8 -*-
"""托盘左键快速今日面板（Qt.Popup：点击外部自动关闭）。"""
import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout, QWidget)

from qfluentwidgets import BodyLabel, CaptionLabel, StrongBodyLabel

import db
import lunar
import reminder
from app.core import schedule_query
from app.ui import tokens

WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]


class QuickTodayPanel(QWidget):
    def __init__(self, on_open_main):
        super().__init__(None, Qt.Popup | Qt.FramelessWindowHint)
        self.on_open_main = on_open_main
        card = QWidget(self)
        card.setObjectName("qtCard")
        card.setStyleSheet(
            "QWidget#qtCard { background: #2b2b31; border: 1px solid #3a3a42;"
            " border-radius: 12px; }")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)
        self.card_lay = QVBoxLayout(card)
        self.card_lay.setContentsMargins(16, 14, 16, 14)
        self.card_lay.setSpacing(8)

    def popup_at(self, global_pos):
        now = dt.datetime.now()
        dark = True  # 托盘面板固定深色（与托盘菜单一致）
        mode = "dark"
        while self.card_lay.count():
            item = self.card_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        wk = reminder.current_week(now.date(),
                                   db.get_setting("first_monday",
                                                  reminder.DEFAULT_FIRST_MONDAY))
        title = StrongBodyLabel(f"{now.month}月{now.day}日 周{WEEKDAY_CN[now.isoweekday() - 1]}"
                                f" · {'第 %d 周' % wk if wk >= 1 else '假期中'}")
        title.setStyleSheet("color: #f3f3f3; font-size: 14pt;")
        self.card_lay.addWidget(title)
        self.card_lay.addWidget(CaptionLabel(lunar.date_line(now.date()).split('  ', 1)[-1]))

        entries = schedule_query.today_courses(
            now, db.list_courses(), db.get_setting("first_monday",
                                                   reminder.DEFAULT_FIRST_MONDAY))
        self.card_lay.addSpacing(4)
        head = BodyLabel("今日课程")
        head.setStyleSheet("color: #a4a4ac;")
        self.card_lay.addWidget(head)
        if entries:
            for e in entries:
                row = QHBoxLayout()
                t = BodyLabel(f"{e['start']}  {e['name']}")
                t.setStyleSheet("color: #f3f3f3;")
                r = CaptionLabel(e["room"] or "")
                r.setStyleSheet("color: #a4a4ac;")
                row.addWidget(t, 1)
                row.addWidget(r)
                holder = QWidget()
                holder.setLayout(row)
                self.card_lay.addWidget(holder)
        else:
            none_l = BodyLabel("今天没有课程")
            none_l.setStyleSheet("color: #6a6a72;")
            self.card_lay.addWidget(none_l)

        evs = [e for e in db.list_events() if e["date"] == now.date().isoformat()]
        self.card_lay.addSpacing(4)
        head2 = BodyLabel("今日日程")
        head2.setStyleSheet("color: #a4a4ac;")
        self.card_lay.addWidget(head2)
        if evs:
            for e in evs:
                mark = "✓ " if e["done"] else ""
                row = BodyLabel(f"· {e['time'] or '全天'}  {mark}{e['title']}")
                row.setStyleSheet("color: #f3f3f3;")
                self.card_lay.addWidget(row)
        else:
            none_e = BodyLabel("今天没有日程")
            none_e.setStyleSheet("color: #6a6a72;")
            self.card_lay.addWidget(none_e)

        open_btn = BodyLabel("打开主窗口 →")
        open_btn.setStyleSheet("color: #4cc2ff;")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.mousePressEvent = lambda ev: (self.close(), self.on_open_main and
                                               self.on_open_main())
        self.card_lay.addSpacing(4)
        self.card_lay.addWidget(open_btn, 0, Qt.AlignRight)

        self.adjustSize()
        self.setFixedWidth(330)
        self.move(global_pos.x() - self.width() + 20, global_pos.y() - self.height() - 8)
        self.show()
