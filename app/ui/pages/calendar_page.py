# -*- coding: utf-8 -*-
"""月历页（对齐系统日历风格）：大数字+农历/节日+休班细标、单击选中、
底部干支详情行+当日列表、今/加按钮。"""
import calendar
import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QScrollArea, QVBoxLayout, QWidget)

from qfluentwidgets import (BodyLabel, CaptionLabel, CardWidget,
                            FluentIcon as FIF, PrimaryPushButton, PushButton,
                            StrongBodyLabel, SubtitleLabel, isDarkTheme)

import db
import lunar
import reminder
from app.core import schedule_query
from app.ui import tokens
from app.ui.dialogs.event_dialog import EventDialog

WEEKDAY_CN = ["日", "一", "二", "三", "四", "五", "六"]  # 周日起
RED_FESTIVALS = {"春节", "元宵节", "清明节", "端午节", "七夕", "中秋节", "重阳节",
                 "元旦", "劳动节", "国庆节"}


class DayCell(QFrame):
    """月历格：大数字 + 休班细标 + 农历/节日（可单击选中）。"""

    def __init__(self, day, side_text, side_kind, holiday, is_today, selected,
                 dark, tip, parent=None):
        super().__init__(parent)
        mode = "dark" if dark else "light"
        self.day = day
        self.setObjectName("dayCell")
        num_color = "#e0443c" if is_today else tokens.NEUTRAL[mode]["text1"]
        bg = tokens.NEUTRAL[mode]["layer2"] if selected else "transparent"
        border = (f"1px solid {tokens.NEUTRAL[mode]['stroke']}" if selected
                  else "none")
        self.setStyleSheet(
            f"QFrame#dayCell {{ background: {bg}; border: {border};"
            f" border-radius: 8px; }}"
            f"QFrame#dayCell:hover {{ background: {tokens.NEUTRAL[mode]['layer2']}; }}")
        self.setToolTip(tip)
        self.setCursor(Qt.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(2)

        num_row = QHBoxLayout()
        num_row.setSpacing(2)
        if holiday:
            hol = CaptionLabel("休" if holiday == "off" else "班")
            hol.setStyleSheet(
                "color: " + (tokens.SEMANTIC[mode]["danger"] if holiday == "off"
                             else tokens.SEMANTIC[mode]["warning"]) + ";")
            num_row.addWidget(hol, 0, Qt.AlignTop)
        num = StrongBodyLabel(str(day))
        num.setStyleSheet(f"color: {num_color}; font-size: 17pt; font-weight: 600;")
        num.setAlignment(Qt.AlignCenter)
        num_row.addWidget(num, 0, Qt.AlignCenter)
        num_row.addStretch(1)
        lay.addLayout(num_row)

        if side_text:
            side_color = {
                "red": "#e0443c" if not dark else "#ff6b5e",
                "strong": tokens.NEUTRAL[mode]["text1"],
                "gray": tokens.NEUTRAL[mode]["text3"],
            }[side_kind]
            side = CaptionLabel(side_text)
            side.setAlignment(Qt.AlignCenter)
            if side_kind != "gray":
                side.setStyleSheet(f"color: {side_color}; font-weight: 600;")
            else:
                side.setStyleSheet(f"color: {side_color};")
            lay.addWidget(side)
        lay.addStretch(1)

        if selected:
            indicator = QFrame()
            indicator.setFixedSize(20, 3)
            indicator.setStyleSheet(
                f"background: {tokens.NEUTRAL[mode]['text2']}; border-radius: 1px;")
            ind_lay = QHBoxLayout()
            ind_lay.setContentsMargins(0, 0, 0, 0)
            ind_lay.addWidget(indicator, 0, Qt.AlignHCenter)
            lay.addLayout(ind_lay)


class CalendarPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("page_calendar")
        self.icon_ = FIF.DATE_TIME
        self.title = "月历"
        self._cursor = dt.date.today().replace(day=1)
        self._selected = dt.date.today()
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(tokens.SPACE["xl"], tokens.SPACE["s"],
                                tokens.SPACE["xl"], tokens.SPACE["m"])
        root.setSpacing(tokens.SPACE["s"])

        head = QHBoxLayout()
        title_lay = QHBoxLayout()
        title_lay.setSpacing(2)
        self.year_label = StrongBodyLabel(str(self._cursor.year))
        self.year_label.setStyleSheet("font-size: 22pt; font-weight: 600;")
        self.slash = StrongBodyLabel("/")
        self.slash.setStyleSheet("font-size: 22pt; font-weight: 600;")
        self.month_label = StrongBodyLabel(f"{self._cursor.month:02d}")
        self.month_label.setStyleSheet(
            "font-size: 22pt; font-weight: 600; color: #e0443c;")
        title_lay.addWidget(self.year_label)
        title_lay.addWidget(self.slash)
        title_lay.addWidget(self.month_label)
        title_lay.addStretch(1)
        head.addLayout(title_lay)
        head.addStretch(1)
        prev = PushButton("上月")
        prev.clicked.connect(lambda: self._shift(-1))
        nxt = PushButton("下月")
        nxt.clicked.connect(lambda: self._shift(1))
        today_btn = PrimaryPushButton("本月")
        today_btn.clicked.connect(self._back_today)
        head.addWidget(prev)
        head.addWidget(nxt)
        head.addWidget(today_btn)
        root.addLayout(head)

        head_holder = QWidget()
        self.head_lay = QGridLayout(head_holder)
        self.head_lay.setSpacing(4)
        root.addWidget(head_holder)

        grid_holder = QWidget()
        self.grid = QGridLayout(grid_holder)
        self.grid.setSpacing(4)
        root.addWidget(grid_holder, 1)
        for r in range(1, 7):
            self.grid.setRowStretch(r, 1)
        root.addSpacing(tokens.SPACE["s"])

        self.detail_label = CaptionLabel("")
        self.detail_label.setStyleSheet("font-size: 13pt;")
        detail_row = QHBoxLayout()
        detail_row.setSpacing(tokens.SPACE["m"])
        detail_row.addWidget(self.detail_label, 1)
        self.btn_today_fab = PrimaryPushButton("今")
        self.btn_today_fab.setFixedSize(36, 36)
        self.btn_today_fab.clicked.connect(self._back_today)
        self.btn_add_fab = PrimaryPushButton("+")
        self.btn_add_fab.setFixedSize(36, 36)
        self.btn_add_fab.setStyleSheet(
            "PrimaryPushButton { background: #d64541; border-radius: 18px;"
            " font-size: 16pt; font-weight: 600; }")
        self.btn_add_fab.clicked.connect(self._add_event)
        detail_row.addWidget(self.btn_today_fab)
        detail_row.addWidget(self.btn_add_fab)
        root.addLayout(detail_row)

        self.day_list_lay = QVBoxLayout()
        self.day_list_lay.setSpacing(tokens.SPACE["s"])
        day_holder = QWidget()
        day_holder.setLayout(self.day_list_lay)
        scroll = QScrollArea()
        scroll.setWidget(day_holder)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setFixedHeight(170)
        root.addWidget(scroll)

    def refresh(self):
        dark = isDarkTheme()
        mode = "dark" if dark else "light"
        y, m = self._cursor.year, self._cursor.month
        self.year_label.setText(str(y))
        self.month_label.setText(f"{m:02d}")

        while self.head_lay.count():
            item = self.head_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for c, name in enumerate(WEEKDAY_CN):
            weekend = c in (0, 6)
            h = StrongBodyLabel(name)
            h.setAlignment(Qt.AlignCenter)
            if weekend:
                h.setStyleSheet("color: #e0443c;")
            self.head_lay.addWidget(h, 0, c)

        first_monday = db.get_setting("first_monday", reminder.DEFAULT_FIRST_MONDAY)
        courses = db.list_courses()
        events = db.list_events()
        cal = calendar.Calendar(firstweekday=6).monthdatescalendar(y, m)
        today = dt.date.today()

        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cells = []

        from app.core import holidays as _hol

        for r, week in enumerate(cal, start=0):
            for c, day in enumerate(week):
                in_month = day.month == m
                if not in_month:
                    self.grid.addWidget(QLabel(""), r, c)
                    continue

                entries = schedule_query.today_courses(
                    dt.datetime(day.year, day.month, day.day, 23, 59),
                    courses, first_monday)
                hues = []
                for e in entries:
                    digest = __import__("hashlib").md5(
                        e["name"].encode("utf-8")).hexdigest()
                    hues.append(int(digest[:4], 16) % 360)
                day_events = [e for e in events if e["date"] == day.isoformat()]

                lines = [f"{day.month}月{day.day}日（周{WEEKDAY_CN[day.isoweekday() % 7]}）"]
                for e in entries:
                    lines.append(f"· {e['start']} {e['name']}"
                                 + (f"（{e['room']}）" if e["room"] else ""))
                for e in day_events:
                    lines.append(f"· {e['time'] or '全天'} {e['title']}"
                                 + ("（已完成）" if e["done"] else ""))
                if len(lines) == 1:
                    lines.append("当日无安排")
                tip = "\n".join(lines)

                try:
                    _ly, lm, ld, leap = lunar.solar_to_lunar(day)
                    festival = lunar.festival_name(day)
                    lunar_text = "" if festival else lunar.lunar_day_str(ld)
                except ValueError:
                    festival, lunar_text = "", ""

                if festival:
                    side_text = festival
                    side_kind = "red" if festival in RED_FESTIVALS else "strong"
                elif lunar_text == "初一":
                    side_text, side_kind = lunar.lunar_month_str(lm, leap), "gray"
                else:
                    side_text, side_kind = lunar_text, "gray"

                cell = DayCell(day.day, side_text, side_kind,
                               _hol.status(day), day == today,
                               day == self._selected, dark, tip)
                cell.mousePressEvent = lambda ev, dd=day: self._select(dd)
                self.grid.addWidget(cell, r, c)
                self._cells.append(cell)

        self._render_detail()

    def _select(self, day):
        self._selected = day
        self.refresh()

    def _render_detail(self):
        day = self._selected
        days_after = (day - dt.date.today()).days
        self.detail_label.setText(lunar.day_detail_line(day, days_after))

        while self.day_list_lay.count():
            item = self.day_list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        dark = isDarkTheme()
        mode = "dark" if dark else "light"
        first_monday = db.get_setting("first_monday", reminder.DEFAULT_FIRST_MONDAY)
        entries = schedule_query.today_courses(
            dt.datetime(day.year, day.month, day.day, 23, 59),
            db.list_courses(), first_monday)
        day_events = [e for e in db.list_events() if e["date"] == day.isoformat()]

        if not entries and not day_events:
            empty = BodyLabel("无日程")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: " + tokens.NEUTRAL[mode]["text3"]
                                + "; font-size: 14pt;")
            self.day_list_lay.addWidget(empty)
            self.day_list_lay.addStretch(1)
            return

        for e in entries:
            state = {"current": "进行中", "done": "已结束",
                     "upcoming": "未开始"}[e["state"]]
            row = CardWidget(self)
            bg, fg, bar = tokens.course_color(e["name"], mode)
            if e["state"] == "done":
                bg = tokens.NEUTRAL[mode]["layer2"]
                fg = tokens.NEUTRAL[mode]["text3"]
            row.setStyleSheet(
                f"CardWidget {{ background: {bg}; border-left: 3px solid {bar};"
                f" border-radius: 8px; }}")
            lay = QHBoxLayout(row)
            lay.setContentsMargins(tokens.SPACE["l"], tokens.SPACE["s"],
                                   tokens.SPACE["s"], tokens.SPACE["s"])
            t = StrongBodyLabel(f"{e['start']}  {e['name']}")
            t.setStyleSheet(f"color: {fg};")
            m2 = CaptionLabel(f"{state} · {e['sec']}节"
                              + (f" · {e['room']}" if e["room"] else ""))
            m2.setStyleSheet(f"color: {fg};")
            lay.addWidget(t)
            lay.addStretch(1)
            lay.addWidget(m2)
            self.day_list_lay.addWidget(row)
        for e in day_events:
            row = CardWidget(self)
            row.setStyleSheet(
                f"CardWidget {{ background: {tokens.NEUTRAL[mode]['layer1']};"
                f" border-left: 3px solid {tokens.SEMANTIC[mode]['danger']};"
                f" border-radius: 8px; }}")
            lay = QHBoxLayout(row)
            lay.setContentsMargins(tokens.SPACE["l"], tokens.SPACE["s"],
                                   tokens.SPACE["s"], tokens.SPACE["s"])
            t = BodyLabel(f"{e['time'] or '全天'}  {e['title']}"
                          + (f"（{e['note']}）" if e["note"] else ""))
            lay.addWidget(t)
            lay.addStretch(1)
            self.day_list_lay.addWidget(row)
        self.day_list_lay.addStretch(1)

    def _shift(self, delta):
        y, m = self._cursor.year, self._cursor.month + delta
        if m == 0:
            y, m = y - 1, 12
        elif m == 13:
            y, m = y + 1, 1
        self._cursor = dt.date(y, m, 1)
        self._selected = dt.date(y, m, min(self._selected.day, 28))
        self.refresh()

    def _back_today(self):
        self._cursor = dt.date.today().replace(day=1)
        self._selected = dt.date.today()
        self.refresh()

    def _add_event(self):
        dlg = EventDialog(self.window(), default_date=self._selected)
        if dlg.exec() and not dlg.deleted:
            d = dlg.result_data()
            db.add_event(d["title"], d["date"], d["time"], d["remind_minutes"],
                         d["note"], d["priority"])
            self.refresh()

    def ensure_built(self):
        pass
