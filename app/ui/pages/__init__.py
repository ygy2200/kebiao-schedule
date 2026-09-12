# -*- coding: utf-8 -*-
"""六页骨架（M1 空壳，M2-M9 填充）。"""
from PySide6.QtWidgets import QVBoxLayout, QWidget

from qfluentwidgets import BodyLabel, FluentIcon, TitleLabel

from app.ui import tokens


class BasePage(QWidget):
    """页面基类：objectName 必需（qfluentwidgets 导航要求）。"""

    def __init__(self, object_name, title, hint, icon):
        super().__init__()
        self.setObjectName(object_name)
        self.title = title
        self.icon_ = icon
        self.hint = hint
        self._build_placeholder()
        self._built = False

    def _build_placeholder(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(tokens.SPACE["xl"], tokens.SPACE["xl"],
                               tokens.SPACE["xl"], tokens.SPACE["xl"])
        lay.setSpacing(tokens.SPACE["m"])
        lay.addWidget(TitleLabel(self.title))
        tip = BodyLabel(self.hint)
        lay.addWidget(tip)
        lay.addStretch(1)

    def ensure_built(self):
        """首次显示前调用一次真实构建（M2+ 各页覆盖）。"""

    def refresh(self):
        pass


from app.ui.pages.today import TodayPage  # M2 真实实现


from app.ui.pages.schedule import SchedulePage  # M3 真实实现


from app.ui.pages.calendar_page import CalendarPage  # M5 真实实现


from app.ui.pages.events import EventsPage  # M4 真实实现


from app.ui.pages.alerts import AlertsPage  # M6 真实实现


from app.ui.pages.settings import SettingsPage  # M9 真实实现
