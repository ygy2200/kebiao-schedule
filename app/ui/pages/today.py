# -*- coding: utf-8 -*-
"""今日页（M2）：时间线课程三态 + 今日任务勾选 + 天气/农历/周次聚合卡。"""
import datetime as dt

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import (BodyLabel, CaptionLabel, CardWidget, CheckBox,
                            FluentIcon as FIF, SubtitleLabel, TitleLabel,
                            isDarkTheme)

import db
import lunar
import reminder
import weather
from app.core import schedule_query
from app.ui import tokens
from app.ui.components.timeline_card import TimelineEntry

WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]


class TodayPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("page_today")
        self.icon_ = FIF.HOME
        self.title = "今日"
        self._build()
        self.refresh()
        self._timer = QTimer(self)
        self._timer.setInterval(60 * 1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

    def _build(self):
        from PySide6.QtWidgets import QScrollArea, QFrame
        self._content = QWidget()
        root = QHBoxLayout(self._content)
        root.setContentsMargins(tokens.SPACE["xl"], tokens.SPACE["xl"],
                                tokens.SPACE["xl"], tokens.SPACE["xl"])
        root.setSpacing(tokens.SPACE["l"])

        # 左列：日期头 + 时间线
        left = QVBoxLayout()
        left.setSpacing(tokens.SPACE["m"])
        self.date_label = TitleLabel("")
        self.date_label.setObjectName("todayDate")
        left.addWidget(self.date_label)
        self.lunar_label = CaptionLabel("")
        left.addWidget(self.lunar_label)
        left.addSpacing(tokens.SPACE["s"])
        self.timeline_lay = QVBoxLayout()
        self.timeline_lay.setSpacing(tokens.SPACE["m"])
        left.addLayout(self.timeline_lay)
        left.addStretch(1)
        left_w = QWidget()
        left_w.setLayout(left)
        root.addWidget(left_w, 3)

        # 右列：聚合卡
        right = QVBoxLayout()
        right.setSpacing(tokens.SPACE["m"])
        self.wx_card = self._make_card("天气")
        self.task_card = self._make_card("今日任务")
        right.addWidget(self.wx_card)
        right.addWidget(self.task_card)
        right.addStretch(1)
        right_w = QWidget()
        right_w.setLayout(right)
        right_w.setFixedWidth(340)
        root.addWidget(right_w, 0)
        root.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidget(self._content)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

    def _make_card(self, title):
        card = CardWidget(self)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(tokens.SPACE["l"], tokens.SPACE["l"],
                               tokens.SPACE["l"], tokens.SPACE["l"])
        lay.setSpacing(tokens.SPACE["s"])
        t = SubtitleLabel(title)
        lay.addWidget(t)
        body = BodyLabel("…")
        body.setWordWrap(True)
        lay.addWidget(body)
        card._body = body
        return card

    # ---------- 数据渲染 ----------

    def refresh(self):
        now = dt.datetime.now()
        dark = isDarkTheme()
        self.date_label.setText(
            f"{now.month}月{now.day}日 星期{WEEKDAY_CN[now.isoweekday() - 1]}")

        first_monday = db.get_setting("first_monday", reminder.DEFAULT_FIRST_MONDAY)
        try:
            _y, m, d, leap = lunar.solar_to_lunar(now.date())
            lunar_str = f"农历{lunar.lunar_month_str(m, leap)}{lunar.lunar_day_str(d)}"
        except ValueError:
            lunar_str = ""
        fest = lunar.festival_name(now.date())
        wk = reminder.current_week(now.date(), first_monday)
        week_str = f"第 {wk} 周" if wk >= 1 else "假期中"
        parts = [p for p in (lunar_str, fest, week_str) if p]
        self.lunar_label.setText("　·　".join(parts))

        # 时间线
        while self.timeline_lay.count():
            item = self.timeline_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        entries = schedule_query.today_courses(
            now, db.list_courses(), first_monday)
        if entries:
            for e in entries:
                self.timeline_lay.addWidget(TimelineEntry(e, dark))
        else:
            tip = BodyLabel("今天没有课程安排 🎉" if wk >= 1 else
                            "假期中 · 在课表页导入课表并设置学期周后显示")
            tip.setStyleSheet("color: "
                              + tokens.NEUTRAL["dark" if dark else "light"]["text2"])
            self.timeline_lay.addWidget(tip)
        self.timeline_lay.addStretch(1)

        # 天气卡
        key = db.get_setting("amap_key", "")
        city = db.get_setting("city", "")
        adcode = weather.geocode(city, key) if (key and city) else None
        lines = []
        if adcode:
            wx = weather.fetch(key, adcode)
            if wx:
                lines.append(f"现在：{wx['text']} {wx['temp']} {wx['wind']}")
            fc = weather.fetch_forecast(key, adcode, 3)
            if fc:
                import datetime as _dt
                for f in fc:
                    try:
                        wd = "周" + WEEKDAY_CN[_dt.date.fromisoformat(f["date"]).isoweekday() - 1]
                    except ValueError:
                        wd = f["date"]
                    lines.append(f"{wd}：{f['dayweather']} {f['nighttemp']}~{f['daytemp']}°C")
        self.wx_card._body.setText("\n".join(lines) if lines
                                   else "未配置 · 设置页填城市与高德 Key 后显示")

        # 今日任务卡
        today_iso = now.date().isoformat()
        evs = [e for e in db.list_events() if e["date"] == today_iso]
        task_lay = self.task_card.layout()
        # 清掉旧 body 与勾选行
        while task_lay.count() > 1:
            item = task_lay.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        if not evs:
            body = BodyLabel("今天没有日程任务")
            body.setStyleSheet("color: " + tokens.NEUTRAL["dark" if dark else "light"]["text2"])
            task_lay.addWidget(body)
        for e in evs:
            row_lay = QHBoxLayout()
            chk = CheckBox()
            chk.setChecked(bool(e["done"]))
            chk.toggled.connect(lambda on, eid=e["id"]: db.update_event(eid, done=1 if on else 0))
            row_lay.addWidget(chk)
            txt = BodyLabel(f"{e['title']}" + (f"  {e['time']}" if e["time"] else ""))
            if e["done"]:
                txt.setStyleSheet("color: " + tokens.NEUTRAL["dark" if dark else "light"]["text3"]
                                  + "; text-decoration: line-through;")
            row_lay.addWidget(txt, 1)
            holder = QWidget()
            holder.setLayout(row_lay)
            task_lay.addWidget(holder)

    def ensure_built(self):
        pass
