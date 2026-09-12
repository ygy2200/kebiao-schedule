# -*- coding: utf-8 -*-
"""月历页（M5）：月视图网格 + 日程/课程点 + 当日概要。"""
import calendar
import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)

from qfluentwidgets import (BodyLabel, CaptionLabel, FluentIcon as FIF,
                            PrimaryPushButton, PushButton, StrongBodyLabel,
                            SubtitleLabel, isDarkTheme)

import db
import reminder
from app.core import schedule_query
from app.ui import tokens

WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]


class DayCell(QFrame):
    """月历单格：日期数字 + 色点（课程 hue 点/日程红点）。"""

    def __init__(self, day, course_hues, has_event, is_today, dark, parent=None):
        super().__init__(parent)
        mode = "dark" if dark else "light"
        self.day = day
        radius = 8
        border = f"1px solid {tokens.ACCENT[mode]}" if is_today \
            else f"1px solid {tokens.NEUTRAL[mode]['stroke']}"
        bg = tokens.ACCENT[mode] + "22" if is_today else "transparent"
        self.setObjectName("dayCell")
        self.setStyleSheet(f"QFrame#dayCell {{ background: {bg}; border: {border};"
                           f" border-radius: {radius}px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)
        num = BodyLabel(str(day))
        num.setAlignment(Qt.AlignLeft)
        if is_today:
            num.setStyleSheet(f"color: {tokens.ACCENT[mode]}; font-weight: 600;")
        lay.addWidget(num)
        dots = QHBoxLayout()
        dots.setSpacing(3)
        for hue in list(course_hues)[:4]:
            d = QFrame()
            d.setFixedSize(7, 7)
            d.setStyleSheet(f"background: hsl({hue}, 45%, 55%); border-radius: 3px;")
            dots.addWidget(d)
        if has_event:
            d = QFrame()
            d.setFixedSize(7, 7)
            d.setStyleSheet(f"background: {tokens.SEMANTIC[mode]['danger']}; border-radius: 3px;")
            dots.addWidget(d)
        dots.addStretch(1)
        lay.addLayout(dots)
        lay.addStretch(1)
        if course_hues:
            self.setToolTip(f"{len(course_hues)} 节课" + ("、有日程" if has_event else ""))


class CalendarPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("page_calendar")
        self.icon_ = FIF.DATE_TIME
        self.title = "月历"
        self._cursor = dt.date.today().replace(day=1)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(tokens.SPACE["xl"], tokens.SPACE["l"],
                                tokens.SPACE["xl"], tokens.SPACE["m"])
        root.setSpacing(tokens.SPACE["m"])

        bar = QHBoxLayout()
        self.title_label = SubtitleLabel("")
        prev = PushButton("←")
        prev.setFixedWidth(44)
        prev.clicked.connect(lambda: self._shift(-1))
        nxt = PushButton("→")
        nxt.setFixedWidth(44)
        nxt.clicked.connect(lambda: self._shift(1))
        today_btn = PushButton("本月")
        today_btn.clicked.connect(self._back_today)
        bar.addWidget(self.title_label)
        bar.addStretch(1)
        bar.addWidget(prev)
        bar.addWidget(nxt)
        bar.addWidget(today_btn)
        root.addLayout(bar)

        grid_holder = QWidget()
        self.grid = QGridLayout(grid_holder)
        self.grid.setSpacing(tokens.SPACE["xs"])
        self.grid_holders = []
        root.addWidget(grid_holder, 1)
        self.detail_label = CaptionLabel("")
        self.detail_label.setWordWrap(True)
        root.addWidget(self.detail_label)

    def _shift(self, delta):
        y, m = self._cursor.year, self._cursor.month + delta
        if m == 0:
            y, m = y - 1, 12
        elif m == 13:
            y, m = y + 1, 1
        self._cursor = dt.date(y, m, 1)
        self.refresh()

    def _back_today(self):
        self._cursor = dt.date.today().replace(day=1)
        self.refresh()

    def refresh(self):
        dark = isDarkTheme()
        mode = "dark" if dark else "light"
        y, m = self._cursor.year, self._cursor.month
        self.title_label.setText(f"{y} 年 {m} 月")

        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for c, name in enumerate(WEEKDAY_CN):
            h = StrongBodyLabel(name)
            h.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(h, 0, c)

        first_monday = db.get_setting("first_monday", reminder.DEFAULT_FIRST_MONDAY)
        courses = db.list_courses()
        events = db.list_events()
        cal = calendar.Calendar(firstweekday=0).monthdatescalendar(y, m)
        today = dt.date.today()

        for r, week in enumerate(cal, start=1):
            for c, day in enumerate(week):
                in_month = day.month == m
                if not in_month:
                    self.grid.addWidget(QLabel(""), r, c)
                    continue
                day_courses = schedule_query.today_courses(
                    dt.datetime(day.year, day.month, day.day, 23, 59),
                    courses, first_monday)
                hues = []
                for e in day_courses:
                    digest = __import__("hashlib").md5(e["name"].encode("utf-8")).hexdigest()
                    hues.append(int(digest[:4], 16) % 360)
                has_event = any(e["date"] == day.isoformat() and not e["done"]
                                for e in events)
                cell = DayCell(day.day, hues, has_event, day == today, dark)
                cell.mouseDoubleClickEvent = lambda ev, dd=day: self._show_day(dd)
                self.grid.addWidget(cell, r, c)

        self.detail_label.setText("双击某天查看当日课程与日程")

    def _show_day(self, day):
        first_monday = db.get_setting("first_monday", reminder.DEFAULT_FIRST_MONDAY)
        entries = schedule_query.today_courses(
            dt.datetime(day.year, day.month, day.day, 23, 59),
            db.list_courses(), first_monday)
        evs = [e for e in db.list_events() if e["date"] == day.isoformat()]
        lines = [f"{day.month}月{day.day}日（周{WEEKDAY_CN[day.isoweekday() - 1]}）"]
        for e in entries:
            lines.append(f"  · {e['start']} {e['name']}" + (f"（{e['room']}）" if e["room"] else ""))
        for e in evs:
            lines.append(f"  · {e['time'] or '全天'} {e['title']}")
        if len(lines) == 1:
            lines.append("  当日无安排")
        self.detail_label.setText("\n".join(lines))

    def ensure_built(self):
        pass
