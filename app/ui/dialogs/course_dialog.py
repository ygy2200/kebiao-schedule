# -*- coding: utf-8 -*-
"""课程编辑对话框（qfluentwidgets MessageBoxBase）。"""
from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QWidget

from qfluentwidgets import (ComboBox, LineEdit, MessageBoxBase, PillPushButton,
                            SpinBox, SwitchButton)

WEEKDAY_NAMES = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


class CourseDialog(MessageBoxBase):
    """新增/编辑课程。用法：dlg = CourseDialog(parent); if dlg.exec(): 用 dlg.result_data()"""

    def __init__(self, parent=None, course=None, weeks_hint=""):
        super().__init__(parent)
        self.deleted = False
        self._course = course

        self.widget = QWidget(self)
        form = QFormLayout(self.widget)
        form.setLabelAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignRight)
        form.setSpacing(12)
        form.setContentsMargins(4, 4, 4, 0)

        self.name_edit = LineEdit(self.widget)
        self.name_edit.setPlaceholderText("课程名")
        self.name_edit.setClearButtonEnabled(True)
        self.name_edit.setMinimumWidth(280)

        self.weekday_box = ComboBox(self.widget)
        self.weekday_box.addItems(WEEKDAY_NAMES)

        self.sec_start = SpinBox(self.widget)
        self.sec_start.setRange(1, 12)
        self.sec_end = SpinBox(self.widget)
        self.sec_end.setRange(1, 12)
        secs = QHBoxLayout()
        secs.addWidget(self.sec_start)
        secs.addWidget(self.sec_end)

        self.weeks_edit = LineEdit(self.widget)
        self.weeks_edit.setPlaceholderText("周次如 9-12;13-14，留空=每周")
        self.room_edit = LineEdit(self.widget)
        self.room_edit.setPlaceholderText("教室（可选）")
        self.switch = SwitchButton("启用（参与提醒与显示）", self.widget)

        if course:
            self.name_edit.setText(course["name"])
            self.weekday_box.setCurrentIndex(course["weekday"] - 1)
            self.sec_start.setValue(course["sec_start"])
            self.sec_end.setValue(course["sec_end"])
            self.weeks_edit.setText(course["weeks"])
            self.room_edit.setText(course["room"])
            self.switch.setChecked(bool(course["enabled"]))
        else:
            self.sec_start.setValue(1)
            self.sec_end.setValue(2)
            self.switch.setChecked(True)

        form.addRow("课程名", self.name_edit)
        form.addRow("星期", self.weekday_box)
        form.addRow("小节", secs)
        form.addRow("周次", self.weeks_edit)
        form.addRow("教室", self.room_edit)
        form.addRow("", self.switch)

        if course:
            del_btn = PillPushButton("删除课程", self.widget)
            del_btn.setObjectName("danger")
            del_btn.clicked.connect(self._delete)
            form.addRow("", del_btn)

        self.viewLayout.addWidget(self.widget)

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")

    def _delete(self):
        self.deleted = True
        self.accept()

    def validate(self) -> bool:
        if not self.name_edit.text().strip():
            self.name_edit.setError(True)
            return False
        if self.sec_start.value() > self.sec_end.value():
            self.sec_start.setError(True)
            return False
        return True

    def result_data(self):
        return dict(
            name=self.name_edit.text().strip(),
            weekday=self.weekday_box.currentIndex() + 1,
            sec_start=self.sec_start.value(),
            sec_end=self.sec_end.value(),
            weeks=self.weeks_edit.text().strip(),
            room=self.room_edit.text().strip(),
            enabled=1 if self.switch.isChecked() else 0,
        )
