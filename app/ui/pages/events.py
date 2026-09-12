# -*- coding: utf-8 -*-
"""日程页（M4）：日期分组 + 任务体系（优先级/过期红显/完成勾选）。"""
import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import (BodyLabel, CaptionLabel, CardWidget, CheckBox,
                            FluentIcon as FIF, InfoBar, PrimaryPushButton,
                            PushButton, StrongBodyLabel, SubtitleLabel,
                            TitleLabel, isDarkTheme)

import db
from app.ui import tokens
from app.ui.dialogs.event_dialog import EventDialog

WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]
PRI_COLOR = {2: "danger", 1: "warning", 0: "text3"}


def _rel_label(d, today):
    delta = (d - today).days
    if delta == 0:
        return "今天"
    if delta == 1:
        return "明天"
    if delta == -1:
        return "昨天"
    if delta < 0:
        return f"过期 {-delta} 天"
    if delta < 7:
        return f"周{WEEKDAY_CN[d.isoweekday() - 1]}"
    return f"{d.month}月{d.day}日"


class EventsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("page_events")
        self.icon_ = FIF.ACCEPT
        self.title = "日程"
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(tokens.SPACE["xl"], tokens.SPACE["l"],
                                tokens.SPACE["xl"], tokens.SPACE["m"])
        root.setSpacing(tokens.SPACE["m"])

        head = TitleLabel("日程")
        sub = CaptionLabel("任务按优先级与日期分组；过期未完成红色显示")
        head_lay = QVBoxLayout()
        head_lay.setSpacing(2)
        head_lay.addWidget(head)
        head_lay.addWidget(sub)
        root.addLayout(head_lay)

        bar = QHBoxLayout()
        self.btn_add = PrimaryPushButton("添加日程")
        self.btn_add.clicked.connect(self._add)
        self.btn_done = PushButton("已完成")
        self.btn_done.setCheckable(True)
        self.btn_done.toggled.connect(self.refresh)
        bar.addWidget(self.btn_add)
        bar.addWidget(self.btn_done)
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
            elif item.layout():
                self._clear_layout(item.layout())

        dark = isDarkTheme()
        today = dt.date.today()
        evs = db.list_events()
        show_done = self.btn_done.isChecked()

        groups = {"已过期": [], "今天": [], "未来": [], "已完成": []}
        for e in evs:
            try:
                d = dt.date.fromisoformat(e["date"])
            except ValueError:
                continue
            if e["done"]:
                if show_done:
                    groups["已完成"].append((d, e))
            elif d < today:
                groups["已过期"].append((d, e))
            elif d == today:
                groups["今天"].append((d, e))
            else:
                groups["未来"].append((d, e))
        for g in groups.values():
            g.sort(key=lambda t: (t[0], t[1]["time"]))

        order = ["已过期", "今天", "未来", "已完成"]
        any_item = False
        for gname in order:
            items = groups[gname]
            if not items:
                continue
            any_item = True
            title_color = tokens.SEMANTIC["dark" if dark else "light"]["danger"] \
                if gname == "已过期" else tokens.NEUTRAL["dark" if dark else "light"]["text2"]
            sec = SubtitleLabel(f"{gname}（{len(items)}）")
            sec.setStyleSheet(f"color: {title_color};")
            self.list_lay.addWidget(sec)
            for d, e in items:
                self.list_lay.addWidget(self._event_row(e, d, today, dark))
        if not any_item:
            tip = BodyLabel("还没有日程 · 点「添加日程」创建")
            tip.setStyleSheet("color: " + tokens.NEUTRAL["dark" if dark else "light"]["text3"])
            self.list_lay.addWidget(tip)
        self.list_lay.addStretch(1)

    def _clear_layout(self, lay):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _event_row(self, e, d, today, dark):
        overdue = (not e["done"]) and d < today
        card = CardWidget(self)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(tokens.SPACE["l"], tokens.SPACE["s"], tokens.SPACE["s"],
                               tokens.SPACE["s"])
        lay.setSpacing(tokens.SPACE["m"])

        mode = "dark" if dark else "light"
        pri = e["priority"] if "priority" in e.keys() else 1
        bar_color = tokens.SEMANTIC[mode][PRI_COLOR.get(pri, "text3")] \
            if pri != 1 else tokens.ACCENT[mode]
        card.setStyleSheet(
            f"CardWidget {{ background: {tokens.NEUTRAL[mode]['layer1']};"
            f" border-left: 3px solid {bar_color}; border-radius: 8px; }}")

        chk = CheckBox()
        chk.setChecked(bool(e["done"]))
        chk.toggled.connect(lambda on, eid=e["id"]: self._toggle(eid, on))
        lay.addWidget(chk)

        info = QVBoxLayout()
        info.setSpacing(1)
        title_style = "text-decoration: line-through; color: " \
            + tokens.NEUTRAL[mode]["text3"] if e["done"] else "font-weight: 600; color: " \
            + (tokens.SEMANTIC[mode]["danger"] if overdue else tokens.NEUTRAL[mode]["text1"])
        title = StrongBodyLabel(e["title"])
        title.setStyleSheet(title_style)
        info.addWidget(title)
        time_part = e["time"] or "全天"
        meta_bits = [f"{d.month}月{d.day}日 {_rel_label(d, today)}", time_part]
        if e["time"] and e["remind_minutes"]:
            meta_bits.append(f"提前{e['remind_minutes']}分提醒")
        if e["note"]:
            meta_bits.append(e["note"])
        pri_name = {2: "高", 0: "低", 1: ""}.get(pri, "")
        if pri_name:
            meta_bits.append(f"优先级{pri_name}")
        meta = CaptionLabel("  ·  ".join(meta_bits))
        meta.setStyleSheet("color: " + tokens.NEUTRAL[mode]["text2"])
        info.addWidget(meta)
        lay.addLayout(info, 1)

        edit_btn = PushButton("编辑")
        edit_btn.clicked.connect(lambda: self._edit(e["id"]))
        lay.addWidget(edit_btn)
        return card

    def _toggle(self, eid, on):
        db.update_event(eid, done=1 if on else 0)
        self.refresh()

    def _add(self):
        dlg = EventDialog(self.window())
        if dlg.exec() and not dlg.deleted:
            d = dlg.result_data()
            db.add_event(d["title"], d["date"], d["time"], d["remind_minutes"],
                         d["note"], d["priority"])
            self.refresh()
            InfoBar.success("已添加", d["title"], duration=2500, parent=self)

    def _edit(self, eid):
        ev = next((e for e in db.list_events() if e["id"] == eid), None)
        if not ev:
            return
        dlg = EventDialog(self.window(), ev)
        if not dlg.exec():
            return
        if dlg.deleted:
            db.delete_event(eid)
        else:
            db.update_event(eid, **dlg.result_data())
        self.refresh()

    def ensure_built(self):
        pass
