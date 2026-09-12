# -*- coding: utf-8 -*-
"""月历页（M5 大改版）：格子内嵌农历/节日/课程日程点，无双击交互（悬停即详情）。"""
import calendar
import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)

from qfluentwidgets import (BodyLabel, CaptionLabel, FluentIcon as FIF,
                            PrimaryPushButton, PushButton, StrongBodyLabel,
                            SubtitleLabel, isDarkTheme)

import db
import lunar
import reminder
from app.core import schedule_query
from app.ui import tokens

WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]


class DayCell(QFrame):
    """月历单格：公历日 + 农历/节日 + 课程与日程点（悬停显示当日详情）。"""

    def __init__(self, day, lunar_text, festival, course_hues, course_count,
                 event_count, is_today, dark, tip, parent=None):
        super().__init__(parent)
        mode = "dark" if dark else "light"
        self.day = day
        border = f"2px solid {tokens.ACCENT[mode]}" if is_today \
            else f"1px solid {tokens.NEUTRAL[mode]['stroke']}"
        bg = tokens.ACCENT[mode] + "26" if is_today else tokens.NEUTRAL[mode]["layer1"]
        self.setObjectName("dayCell")
        self.setStyleSheet(
            f"QFrame#dayCell {{ background: {bg}; border: {border};"
            f" border-radius: 8px; }}")
        self.setToolTip(tip)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 5, 8, 5)
        lay.setSpacing(1)

        # 第一行：公历日（左）+ 节日/农历（右）
        top = QHBoxLayout()
        top.setSpacing(4)
        num = StrongBodyLabel(str(day))
        top.addWidget(num)
        top.addStretch(1)
        side_text = festival or lunar_text
        side_color = tokens.SEMANTIC[mode]["danger"] if festival \
            else tokens.NEUTRAL[mode]["text3"]
        side = CaptionLabel(side_text)
        side.setStyleSheet(f"color: {side_color};")
        top.addWidget(side)
        lay.addLayout(top)

        # 第二行：当日有安排时显示首条摘要 + 数量
        if course_count or event_count:
            bits = []
            if course_count:
                bits.append(f"{course_count} 节课")
            if event_count:
                bits.append(f"{event_count} 项日程")
            summary = CaptionLabel(" · ".join(bits))
            summary.setStyleSheet(f"color: {tokens.NEUTRAL[mode]['text2']};")
            lay.addWidget(summary)

        # 第三行：色点（课程 hue 点 + 日程红点）
        if course_hues or event_count:
            dots = QHBoxLayout()
            dots.setSpacing(3)
            for hue in list(course_hues)[:5]:
                d = QFrame()
                d.setFixedSize(7, 7)
                d.setStyleSheet(f"background: hsl({hue}, 45%, 55%); border-radius: 3px;")
                dots.addWidget(d)
            if event_count:
                d = QFrame()
                d.setFixedSize(7, 7)
                d.setStyleSheet(
                    f"background: {tokens.SEMANTIC[mode]['danger']}; border-radius: 3px;")
                dots.addWidget(d)
            dots.addStretch(1)
            lay.addLayout(dots)
        lay.addStretch(1)


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
        title_lay = QVBoxLayout()
        title_lay.setSpacing(2)
        self.title_label = SubtitleLabel("")
        self.month_hint = CaptionLabel("")
        title_lay.addWidget(self.title_label)
        title_lay.addWidget(self.month_hint)
        bar.addLayout(title_lay)
        bar.addStretch(1)
        prev = PushButton("上月")
        prev.clicked.connect(lambda: self._shift(-1))
        nxt = PushButton("下月")
        nxt.clicked.connect(lambda: self._shift(1))
        today_btn = PrimaryPushButton("本月")
        today_btn.clicked.connect(self._back_today)
        bar.addWidget(prev)
        bar.addWidget(nxt)
        bar.addWidget(today_btn)
        root.addLayout(bar)

        # 周表头（周末列标橙）
        head_holder = QWidget()
        self.head_lay = QGridLayout(head_holder)
        self.head_lay.setSpacing(tokens.SPACE["xs"])
        root.addWidget(head_holder)

        grid_holder = QWidget()
        self.grid = QGridLayout(grid_holder)
        self.grid.setSpacing(tokens.SPACE["xs"])
        root.addWidget(grid_holder, 1)
        self._cells = []

    def refresh(self):
        dark = isDarkTheme()
        mode = "dark" if dark else "light"
        y, m = self._cursor.year, self._cursor.month
        self.title_label.setText(f"{y} 年 {m} 月")
        now = dt.date.today()
        self.month_hint.setText(
            f"今天 {now.month}月{now.day}日 · 第 {max(reminder.current_week(now, db.get_setting('first_monday', reminder.DEFAULT_FIRST_MONDAY)), 0) or '—'} 周"
            if reminder.current_week(now, db.get_setting('first_monday', reminder.DEFAULT_FIRST_MONDAY)) >= 1
            else "假期中")

        # 清空周表头与格子
        while self.head_lay.count():
            item = self.head_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cells = []

        for c, name in enumerate(WEEKDAY_CN):
            weekend = c >= 5
            h = StrongBodyLabel(name)
            h.setAlignment(Qt.AlignCenter)
            if weekend:
                h.setStyleSheet(
                    f"color: {tokens.SEMANTIC[mode]['warning']};")
            self.head_lay.addWidget(h, 0, c)

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

                # 当日课程与日程
                entries = schedule_query.today_courses(
                    dt.datetime(day.year, day.month, day.day, 23, 59),
                    courses, first_monday)
                hues = []
                for e in entries:
                    digest = __import__("hashlib").md5(e["name"].encode("utf-8")).hexdigest()
                    hues.append(int(digest[:4], 16) % 360)
                day_events = [e for e in events if e["date"] == day.isoformat()]

                # 悬停详情（替代双击）
                lines = [f"{day.month}月{day.day}日（周{WEEKDAY_CN[day.isoweekday() - 1]}）"]
                for e in entries:
                    lines.append(f"· {e['start']} {e['name']}"
                                 + (f"（{e['room']}）" if e["room"] else ""))
                for e in day_events:
                    lines.append(f"· {e['time'] or '全天'} {e['title']}"
                                 + ("（已完成）" if e["done"] else ""))
                if len(lines) == 1:
                    lines.append("当日无安排")
                tip = "\n".join(lines)

                # 农历/节日（节日当天以节日名替代农历日）
                try:
                    _ly, lm, ld, leap = lunar.solar_to_lunar(day)
                    festival = lunar.festival_name(day)
                    lunar_text = "" if festival else lunar.lunar_day_str(ld)
                except ValueError:
                    festival, lunar_text = "", ""

                cell = DayCell(day.day,
                               lunar_text,
                               festival,
                               hues, len(entries), len(day_events),
                               day == today, dark, tip)
                self.grid.addWidget(cell, r, c)
                self._cells.append(cell)

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

    def ensure_built(self):
        pass

