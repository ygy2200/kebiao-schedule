# -*- coding: utf-8 -*-
"""设置页（M9）：SettingCardGroup 化（Win11 设置同构）+ 强调色 + 节次时间子对话框。"""
import datetime as dt
import json
import os
import subprocess

from PySide6.QtCore import QTime, Qt
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QScrollArea,
                               QVBoxLayout, QWidget)

from qfluentwidgets import (BodyLabel, CaptionLabel, ComboBox, DatePicker,
                            isDarkTheme, StrongBodyLabel,
                            InfoBar, LineEdit, OptionsSettingCard,
                            PrimaryPushSettingCard, PushSettingCard,
                            RangeSettingCard, ScrollArea, SettingCardGroup,
                            SwitchButton, TimePicker, TitleLabel)
from qfluentwidgets import FluentIcon as FIF

import autostart
import db
import reminder
import weather
from app.ui import tokens

from qfluentwidgets import MessageBoxBase

from PySide6.QtCore import QObject, Signal as _QSignal


class _HolidayRefreshBridge(QObject):
    done = _QSignal(bool, str)  # (成功?, 消息)


ACCENT_PRESETS = [
    ("Windows 蓝", "#0067C0"), ("紫", "#7C5CBF"), ("青", "#00818B"), ("绿", "#0F7B0F"),
    ("琥珀", "#9D5D00"), ("橙", "#CA5010"), ("玫红", "#C239B3"), ("石板灰", "#5D6D7E"),
]


class SectionTimesDialog(__import__("qfluentwidgets", fromlist=["MessageBoxBase"]).MessageBoxBase):
    """12 节开始时间网格子对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.widget = QWidget(self)
        grid = QGridLayout(self.widget)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        self.time_edits = {}
        for i in range(12):
            r, col = divmod(i, 4)
            lab = BodyLabel(f"第{i + 1}节")
            ed = TimePicker(self.widget)
            times = reminder.section_times()
            h, m = map(int, times.get(i + 1, "08:00").split(":"))
            ed.setTime(QTime(h, m))
            grid.addWidget(lab, r, col * 2)
            grid.addWidget(ed, r, col * 2 + 1)
            self.time_edits[i + 1] = ed
        self.viewLayout.addWidget(self.widget)
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")

    def accept(self):
        data = {sec: ed.time().toString("HH:mm") for sec, ed in self.time_edits.items()}
        db.set_setting("section_times", json.dumps(data))
        super().accept()


class SettingsPage(ScrollArea):
    def __init__(self):
        super().__init__()
        self.setObjectName("page_settings")
        self.icon_ = FIF.SETTING
        self.title = "设置"
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._content = QWidget()
        self.setWidget(self._content)
        lay = QVBoxLayout(self._content)
        lay.setContentsMargins(tokens.SPACE["xl"], tokens.SPACE["xl"],
                               tokens.SPACE["xl"], tokens.SPACE["xl"])
        lay.setSpacing(tokens.SPACE["l"])
        lay.addWidget(TitleLabel("设置"))
        lay.addSpacing(tokens.SPACE["m"])

        # —— 学期与提醒 ——
        g1 = SettingCardGroup("学期与提醒", self._content)
        self.date_card = PushSettingCard(
            "修改", FIF.CALENDAR, "学期第一周周一",
            "周次与课前提醒的基础，务必准确", self._content)
        self.date_card.clicked.connect(self._edit_first_monday)
        g1.addSettingCard(self.date_card)
        self.ahead_card = _RangeCard(0, 60, 10, "课前提醒提前量", "提前多少分钟弹窗", self._content)
        self.ahead_card.valueChanged.connect(self._save_ahead)
        g1.addSettingCard(self.ahead_card)
        lay.addWidget(g1)

        # —— 节次时间 ——
        g2 = SettingCardGroup("节次开始时间（决定提醒时刻）", self._content)
        self.times_card = PushSettingCard(
            "设置", FIF.DATE_TIME, "12 个小节的开始时间", "与课表导入的小节对应", self._content)
        self.times_card.clicked.connect(self._edit_times)
        g2.addSettingCard(self.times_card)
        lay.addWidget(g2)

        # —— 外观 ——
        g3 = SettingCardGroup("外观", self._content)
        from qfluentwidgets import qconfig
        self.theme_card = OptionsSettingCard(
            qconfig.themeMode, FIF.BRUSH, "应用主题", "浅色 / 深色 / 跟随系统",
            texts=["浅色", "深色", "跟随系统"], parent=self._content)
        g3.addSettingCard(self.theme_card)
        self.accent_card = PushSettingCard(
            "更换", FIF.PALETTE, "强调色", "主按钮与选中态的颜色", self._content)
        self.accent_card.clicked.connect(self._cycle_accent)
        g3.addSettingCard(self.accent_card)
        lay.addWidget(g3)

        # —— 天气 ——
        g4 = SettingCardGroup("天气（高德开放平台）", self._content)
        city_card = QFrame(self._content)
        cl = QHBoxLayout(city_card)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.addWidget(BodyLabel("城市"))
        self.city_edit = LineEdit(city_card)
        self.city_edit.setPlaceholderText("如：钦州市")
        self.city_edit.setFixedWidth(180)
        cl.addWidget(self.city_edit)
        cl.addSpacing(24)
        cl.addWidget(BodyLabel("Key"))
        self.key_edit = LineEdit(city_card)
        self.key_edit.setPlaceholderText("Web服务 Key（console.amap.com 注册获取）")
        self.key_edit.setMinimumWidth(280)
        cl.addWidget(self.key_edit)
        cl.addStretch(1)
        g4.addSettingCard(_wrap_card("天气数据源", "填写城市与高德 Web服务 Key", city_card))
        self.wx_test_card = PushSettingCard(
            "保存并测试", FIF.CLOUD, "保存天气配置",
            "保存后测试拉取，成功即主页显示", self._content)
        self.wx_test_card.clicked.connect(self._save_weather)
        g4.addSettingCard(self.wx_test_card)
        lay.addWidget(g4)

        # —— 节假日数据 ——
        g45 = SettingCardGroup("法定节假日数据", self._content)
        from app.core import holidays as _hol
        _exists, _at = _hol.cache_info()
        _years = "、".join(sorted(_hol.load().keys())) or "2026（内置）"
        self.holiday_card = PushSettingCard(
            "立即更新", FIF.SYNC, "联网更新法定节假日（休 / 班）",
            f"数据源：holiday-cn 开源库 · 覆盖：{_years} 年 · "
            + (f"上次更新：{_at[:10]}" if _at else "使用内置数据"), self._content)
        self.holiday_card.clicked.connect(self._refresh_holidays)
        g45.addSettingCard(self.holiday_card)
        lay.addWidget(g45)

        # —— 启动与数据 ——
        g5 = SettingCardGroup("启动与数据", self._content)
        self.autostart_card = _SwitchCard("开机自动启动", "写注册表 HKCU Run 键，可随时关闭",
                                          autostart.enabled(), self._content)
        self.autostart_card.checkedChanged.connect(self._toggle_autostart)
        g5.addSettingCard(self.autostart_card)
        self.backup_card = PushSettingCard(
            "立即备份", FIF.SAVE, "全量备份（JSON）",
            "启动时自动备份，保留最近 5 份（data/backups/）", self._content)
        self.backup_card.clicked.connect(self._do_backup)
        g5.addSettingCard(self.backup_card)
        self.restore_card = PushSettingCard(
            "恢复", FIF.UPDATE, "从备份恢复",
            "选择 backup_*.json 覆盖当前数据（恢复前自动备份）", self._content)
        self.restore_card.clicked.connect(self._do_restore)
        g5.addSettingCard(self.restore_card)
        self.data_card = PushSettingCard(
            "打开", FIF.FOLDER, "数据文件夹",
            f"{db.DB_PATH}（导入覆盖前自动备份）", self._content)
        self.data_card.clicked.connect(self._open_data)
        g5.addSettingCard(self.data_card)
        lay.addWidget(g5)

        lay.addStretch(1)
        self._load()

    # ---------- 数据加载/保存 ----------

    def _load(self):
        fm = db.get_setting("first_monday", reminder.DEFAULT_FIRST_MONDAY)
        try:
            self._fm_date = dt.date.fromisoformat(str(fm))
        except ValueError:
            self._fm_date = dt.date.today()
        self.date_card.setContent(f"学期第一周周一：{self._fm_date.isoformat()}")
        self.ahead_card.setValue(int(db.get_setting("remind_ahead", 10) or 10))
        self.city_edit.setText(db.get_setting("city", "") or "")
        self.key_edit.setText(db.get_setting("amap_key", "") or "")

    def _edit_times(self):
        dlg = SectionTimesDialog(self.window())
        if dlg.exec():
            InfoBar.success("已保存", "节次时间已更新", duration=2500, parent=self)

    def _edit_first_monday(self):
        dlg = _DatePickerDialog(self._fm_date, self.window())
        if dlg.exec():
            self._fm_date = dlg.selected_date
            db.set_setting("first_monday", self._fm_date.isoformat())
            self.date_card.setContent(f"学期第一周周一：{self._fm_date.isoformat()}")
            InfoBar.success("已保存", f"学期第一周：{self._fm_date.isoformat()}", parent=self)

    def _save_ahead(self, v):
        db.set_setting("remind_ahead", int(v))

    def _cycle_accent(self):
        current = db.get_setting("accent", "") or ""
        names = [n for n, _c in ACCENT_PRESETS]
        idx = (names.index(current) + 1) % len(names) if current in names else 0
        name, color = ACCENT_PRESETS[idx]
        db.set_setting("accent", name)
        from qfluentwidgets import setThemeColor
        setThemeColor(color)
        self.accent_card.setContent(f"当前：{name}")

    def _save_weather(self):
        key = self.key_edit.text().strip()
        city = self.city_edit.text().strip()
        db.set_setting("amap_key", key)
        db.set_setting("city", city)
        if not (key and city):
            InfoBar.warning("已保存", "未完整配置，主页不显示天气", parent=self)
            return
        adcode = weather.geocode(city, key)
        wx = weather.fetch(key, adcode) if adcode else None
        if wx:
            InfoBar.success("测试成功", f"{city} {wx['text']} {wx['temp']}", parent=self)
        else:
            InfoBar.error("拉取失败", "请检查城市名与 Key（需开通 Web服务）", parent=self)

    def _toggle_autostart(self, on):
        autostart.set_enabled(bool(on))
        if on:
            InfoBar.success("已开启", "写入注册表 HKCU Run 键，取消勾选即回滚", parent=self)

    def _refresh_holidays(self):
        """后台线程联网更新（此前同步跑在主线程，全断时冻结界面 60s+）。"""
        import threading
        from app.core import holidays as _hol
        if getattr(self, "_hol_updating", False):
            return
        self._hol_updating = True
        self.holiday_card.setEnabled(False)
        self.holiday_card.setContent("正在联网更新…（最多约半分钟，可继续用其他页面）")
        bridge = _HolidayRefreshBridge(self)
        year = dt.date.today().year

        def worker():
            got, err = _hol.refresh(force=True, years=[year])
            bridge.done.emit(bool(got), err or "、".join(str(g) for g in got))

        def on_done(ok, msg):
            self._hol_updating = False
            self.holiday_card.setEnabled(True)
            _exists, _at = _hol.cache_info()
            if ok:
                self.holiday_card.setContent(f"已更新 · 上次：{_at[:10]}")
                InfoBar.success("节假日数据已更新", msg, duration=4000, parent=self)
            else:
                self.holiday_card.setContent("更新失败 · 使用内置 / 缓存数据")
                InfoBar.warning("更新失败", "已降级内置数据（" + msg[:50] + "）",
                                duration=5000, parent=self)

        bridge.done.connect(on_done)
        threading.Thread(target=worker, daemon=True).start()

    def _do_backup(self):
        from app.core import backup
        path = backup.backup_all()
        InfoBar.success("备份完成", os.path.basename(path), duration=3500, parent=self)

    def _do_restore(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        start = os.path.join(db.DATA_DIR, "backups")
        path, _ = QFileDialog.getOpenFileName(
            self, "选择备份文件", start, "备份 JSON (*.json)")
        if not path:
            return
        if QMessageBox.question(self, "确认恢复",
                                "恢复将覆盖当前全部课程/日程/设置（恢复前自动备份）。继续？"
                                ) != QMessageBox.Yes:
            return
        from app.core import backup
        stat = backup.restore_from(path)
        QMessageBox.information(self, "已恢复",
                                f"课程 {stat['courses']} 条、日程 {stat['events']} 条已恢复。"
                                "重启应用后界面刷新。")

    def _open_data(self):
        subprocess.Popen(["explorer", "/select,", db.DB_PATH])

    def showEvent(self, ev):
        super().showEvent(ev)
        self._load()

    def ensure_built(self):
        pass

    def refresh(self):
        self._load()


# ---------- 小工具卡片（qfw 无现成的包装） ----------

def _wrap_card(title, content, widget):
    """自绘行卡（SettingCard 塞外部控件有挂起/段错误，绕开）。"""
    from qfluentwidgets import SettingCard  # noqa 仅借高度常量
    card = QFrame(widget.parentWidget() or widget)
    card.setObjectName("wrapCard")
    dark = isDarkTheme()
    mode = "dark" if dark else "light"
    card.setStyleSheet(
        f"QFrame#wrapCard {{ background: {tokens.NEUTRAL[mode]['layer1']};"
        f" border: 1px solid {tokens.NEUTRAL[mode]['stroke']}; border-radius: 8px; }}")
    lay = QHBoxLayout(card)
    lay.setContentsMargins(16, 12, 16, 12)
    lay.setSpacing(12)
    left = QVBoxLayout()
    t = StrongBodyLabel(title)
    c = CaptionLabel(content)
    left.addWidget(t)
    left.addWidget(c)
    lay.addLayout(left)
    lay.addStretch(1)
    lay.addWidget(widget, 0, Qt.AlignVCenter)
    card.setFixedHeight(max(70, widget.sizeHint().height() + 24))
    return card


class _RangeCard(__import__("qfluentwidgets", fromlist=["SettingCard"]).SettingCard):
    """滑条卡片（不接 qconfig，即时回调）。"""
    from PySide6.QtCore import Signal
    valueChanged = Signal(int)

    def __init__(self, lo, hi, default, title, content, parent):
        super().__init__(FIF.RINGER, title, content, parent)
        from qfluentwidgets import Slider
        self.slider = Slider(Qt.Horizontal, self)
        self.slider.setRange(lo, hi)
        self.slider.setValue(default)
        self.slider.setFixedWidth(170)
        self._value_label = BodyLabel(str(default), self)
        self.slider.valueChanged.connect(self._on_change)
        self.hBoxLayout.addWidget(self._value_label, 0, Qt.AlignVCenter)
        self.hBoxLayout.addWidget(self.slider, 0, Qt.AlignVCenter)

    def _on_change(self, v):
        self._value_label.setText(str(v))
        self.valueChanged.emit(int(v))

    def setValue(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(int(v))
        self._value_label.setText(str(int(v)))
        self.slider.blockSignals(False)


class _SwitchCard(__import__("qfluentwidgets", fromlist=["SettingCard"]).SettingCard):
    from PySide6.QtCore import Signal
    checkedChanged = Signal(bool)

    def __init__(self, title, content, checked, parent):
        super().__init__(FIF.POWER_BUTTON, title, content, parent)
        self.switchButton = SwitchButton(parent)
        self.switchButton.setChecked(checked)
        self.switchButton.checkedChanged.connect(self.checkedChanged.emit)
        self.hBoxLayout.addWidget(self.switchButton, 0, Qt.AlignVCenter)


class _DatePickerDialog(MessageBoxBase):
    from PySide6.QtCore import Signal

    def __init__(self, initial_date, parent=None):
        super().__init__(parent)
        self.selected_date = initial_date
        self.widget = QWidget(self)
        lay = QVBoxLayout(self.widget)
        self.picker = DatePicker(self.widget)
        self.picker.setDate(initial_date)
        lay.addWidget(self.picker)
        self.viewLayout.addWidget(self.widget)
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")

    def accept(self):
        d = self.picker.getDate()
        try:
            y, m, dd = d
            self.selected_date = dt.date(int(y), int(m), int(dd))
        except Exception:
            pass
        super().accept()
