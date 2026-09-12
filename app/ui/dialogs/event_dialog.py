# -*- coding: utf-8 -*-
"""日程编辑对话框（qfluentwidgets）：DatePicker/TimePicker/优先级。"""
import datetime as dt

from PySide6.QtCore import QTime
from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QWidget

from qfluentwidgets import (ComboBox, DatePicker, LineEdit, MessageBoxBase,
                            SpinBox, SwitchButton, TimePicker)

PRIORITIES = [("低", 0), ("中", 1), ("高", 2)]


class EventDialog(MessageBoxBase):
    def __init__(self, parent=None, ev=None, default_date=None):
        super().__init__(parent)
        self.deleted = False
        self._ev = ev

        self.widget = QWidget(self)
        form = QFormLayout(self.widget)
        form.setLabelAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignRight)
        form.setSpacing(12)
        form.setContentsMargins(4, 4, 4, 0)

        self.title_edit = LineEdit(self.widget)
        self.title_edit.setPlaceholderText("要做什么")
        self.title_edit.setMinimumWidth(280)
        self.title_edit.setClearButtonEnabled(True)

        self.date_picker = DatePicker(self.widget)
        self.all_day = SwitchButton("全天（不弹窗提醒）", self.widget)
        self.time_picker = TimePicker(self.widget)
        self.time_picker.setEnabled(False)
        self.all_day.checkedChanged.connect(self.time_picker.setEnabled)

        self.remind_spin = SpinBox(self.widget)
        self.remind_spin.setRange(0, 720)
        self.remind_spin.setValue(10)

        self.pri_box = ComboBox(self.widget)
        for name, _v in PRIORITIES:
            self.pri_box.addItem(name)

        self.note_edit = LineEdit(self.widget)
        self.note_edit.setPlaceholderText("备注（可选）")

        if ev:
            self.title_edit.setText(ev["title"])
            d = dt.date.fromisoformat(ev["date"])
            self.date_picker.setDate(d)
            if ev["time"]:
                h, m = map(int, ev["time"].split(":"))
                self.time_picker.setTime(QTime(h, m))
            else:
                self.all_day.setChecked(True)
            self.remind_spin.setValue(ev["remind_minutes"] or 0)
            self.note_edit.setText(ev["note"])
            for i, (_n, v) in enumerate(PRIORITIES):
                if v == (ev["priority"] if "priority" in ev.keys() else 1):
                    self.pri_box.setCurrentIndex(i)
        else:
            self.date_picker.setDate(default_date or dt.date.today())
            self.time_picker.setTime(QTime(9, 0))
            self.remind_spin.setValue(10)
            self.pri_box.setCurrentIndex(1)

        form.addRow("标题", self.title_edit)
        form.addRow("日期", self.date_picker)
        form.addRow("", self.all_day)
        form.addRow("时间", self.time_picker)
        form.addRow("提前提醒", self.remind_spin)
        form.addRow("优先级", self.pri_box)
        form.addRow("备注", self.note_edit)

        self.viewLayout.addWidget(self.widget)
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")

    def validate(self) -> bool:
        return bool(self.title_edit.text().strip())

    def result_data(self):
        d = self.date_picker.getDate()
        if isinstance(d, tuple):
            date = f"{d[0]:04d}-{d[1]:02d}-{d[2]:02d}"
        else:
            date = d.toString("yyyy-MM-dd") if hasattr(d, "toString") else str(d)
        t = self.time_picker.getTime()
        return dict(
            title=self.title_edit.text().strip(),
            date=date,
            time="" if self.all_day.isChecked() else t.toString("HH:mm"),
            remind_minutes=self.remind_spin.value(),
            note=self.note_edit.text().strip(),
            priority=PRIORITIES[self.pri_box.currentIndex()][1],
        )
