# -*- coding: utf-8 -*-
"""时间线课程卡（今日页）：左轴时刻 + 节点圆点 + 课程卡三态。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

from qfluentwidgets import CaptionLabel, StrongBodyLabel

from app.ui import tokens


def _dot(state, dark):
    if state == "current":
        return tokens.ACCENT["dark" if dark else "light"], 10
    if state == "done":
        return ("#5a5a62" if dark else "#c0c0c8"), 8
    return ("#8ea9c9" if dark else "#5b9bd5"), 8


class TimelineEntry(QFrame):
    """一条时间线课程。"""

    def __init__(self, entry, dark, parent=None):
        super().__init__(parent)
        bg, fg, bar = tokens.course_color(entry["name"], dark and "dark" or "light")
        if entry["state"] == "done":
            bg, fg, bar = "#242428" if dark else "#f1f1f3", \
                tokens.NEUTRAL["dark" if dark else "light"]["text3"], \
                ("#3a3a40" if dark else "#d8d8dc")

        self.setObjectName("tlCard")
        self.setStyleSheet(
            f"QFrame#tlCard {{ background: {bg}; border-radius: 8px; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(tokens.SPACE["l"], tokens.SPACE["m"], tokens.SPACE["l"],
                               tokens.SPACE["m"])
        lay.setSpacing(tokens.SPACE["m"])

        # 左轴：时刻 + 竖线 + 节点
        axis = QVBoxLayout()
        axis.setSpacing(2)
        t = CaptionLabel(entry["start"])
        t.setAlignment(Qt.AlignCenter)
        axis.addWidget(t)
        dot_color, dot_size = _dot(entry["state"], dark)
        dot = QFrame()
        dot.setFixedSize(dot_size, dot_size)
        dot.setStyleSheet(f"background: {dot_color}; border-radius: {dot_size // 2}px;")
        axis.addWidget(dot, 0, Qt.AlignHCenter)
        axis.addStretch(1)
        axis_w = QVBoxLayout()
        axis_w.addLayout(axis)
        lay.addLayout(axis_w)

        # 课程信息
        info = QVBoxLayout()
        info.setSpacing(2)
        name = StrongBodyLabel(entry["name"])
        name.setStyleSheet(f"color: {fg};")
        meta = CaptionLabel(f"{entry['start']}–{entry['end']} · {entry['sec']}节"
                            + (f" · {entry['room']}" if entry["room"] else ""))
        meta.setStyleSheet(f"color: {fg};")
        info.addWidget(name)
        info.addWidget(meta)
        lay.addLayout(info, 1)

        # 状态徽章
        badge_text = {"current": "进行中", "upcoming": "未开始", "done": "已结束"}[entry["state"]]
        badge = CaptionLabel(badge_text)
        if entry["state"] == "current":
            accent = tokens.ACCENT["dark" if dark else "light"]
            badge.setStyleSheet(
                f"color: {accent}; border: 1px solid {accent};"
                f" border-radius: 10px; padding: 2px 10px;")
        else:
            badge.setStyleSheet(f"color: {fg};")
        badge.setAlignment(Qt.AlignVCenter)
        lay.addWidget(badge, 0, Qt.AlignTop)
