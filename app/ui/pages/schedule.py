# -*- coding: utf-8 -*-
"""课表页（M3）：周视图 + 时刻线 + 右键菜单 + Fluent 编辑对话框。"""
import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout,
                               QHeaderView, QLabel, QMenu, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from qfluentwidgets import (CaptionLabel, InfoBar, PrimaryPushButton, PushButton,
                            RoundMenu, isDarkTheme)

import db
import importer
import reminder
from app.core import schedule_query
from app.ui import tokens
from app.ui.dialogs.course_dialog import CourseDialog

WEEKDAY_NAMES = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
ROW_SECTIONS = [(1, 2), (3, 5), (6, 7), (8, 9), (10, 12)]


def _in_cell(sec_start, row):
    lo, hi = ROW_SECTIONS[row]
    return lo <= sec_start <= hi  # 起始节落行，每课只渲染一次


class SchedulePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("page_schedule")
        self.icon_ = __import__("qfluentwidgets", fromlist=["FluentIcon"]).FluentIcon.CALENDAR
        self.title = "课表"
        self.week_offset = 0
        self._cur_week = 1
        self._show_week = 1
        self._dark = False
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(tokens.SPACE["xl"], tokens.SPACE["l"],
                                tokens.SPACE["xl"], tokens.SPACE["m"])
        root.setSpacing(tokens.SPACE["m"])

        bar = QHBoxLayout()
        bar.setSpacing(tokens.SPACE["s"])
        self.btn_import = PrimaryPushButton("导入课表 xlsx")
        self.btn_import.clicked.connect(self.import_xlsx)
        self.btn_add = PushButton("添加课程")
        self.btn_add.clicked.connect(self._add_course)
        self.btn_prev = PushButton("←")
        self.btn_prev.setFixedWidth(44)
        self.btn_prev.clicked.connect(lambda: self._shift(-1))
        self.btn_next = PushButton("→")
        self.btn_next.setFixedWidth(44)
        self.btn_next.clicked.connect(lambda: self._shift(1))
        self.btn_today = PushButton("本周")
        self.btn_today.clicked.connect(self._shift_back)
        self.week_label = CaptionLabel("")
        bar.addWidget(self.btn_import)
        bar.addWidget(self.btn_add)
        bar.addStretch(1)
        bar.addWidget(self.btn_prev)
        bar.addWidget(self.week_label)
        bar.addWidget(self.btn_next)
        bar.addWidget(self.btn_today)
        root.addLayout(bar)

        self.table = QTableWidget(6, 8)
        self.table.setObjectName("timetable")
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 54)
        for c in range(1, 8):
            self.table.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setRowHeight(0, 46)
        for r in range(1, 6):
            self.table.setRowHeight(r, 100)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        root.addWidget(self.table, 1)

        self.markers_label = CaptionLabel("")
        self.markers_label.setWordWrap(True)
        root.addWidget(self.markers_label)

    # ---------- 渲染 ----------

    def refresh(self):
        self._dark = isDarkTheme()
        self.courses = db.list_courses()
        first_monday = db.get_setting("first_monday", reminder.DEFAULT_FIRST_MONDAY)
        today = dt.date.today()
        self._cur_week = reminder.current_week(today, first_monday)
        self._show_week = max(self._cur_week + self.week_offset, 0)

        today_col = -1
        if self._show_week >= 1:
            fm = dt.date.fromisoformat(str(first_monday))
            ws = fm + dt.timedelta(weeks=self._show_week - 1)
            we = ws + dt.timedelta(days=6)
            self.week_label.setText(
                f"第 {self._show_week} 周   {ws.month}.{ws.day} - {we.month}.{we.day}")
            headers = [f"{n}\n{(ws + dt.timedelta(days=i)).strftime('%m/%d')}"
                       for i, n in enumerate(WEEKDAY_NAMES)]
            today_col = today.isoweekday() if self._show_week == self._cur_week else -1
        else:
            self.week_label.setText("假期中")
            headers = list(WEEKDAY_NAMES)
        self._today_col = today_col

        accent = QColor("#4CC2FF") if self._dark else QColor("#0067C0")
        for c, text in enumerate(["节次"] + headers):
            it = QTableWidgetItem(text)
            it.setTextAlignment(Qt.AlignCenter)
            if c == today_col:
                it.setForeground(accent)
                f = it.font()
                f.setBold(True)
                it.setFont(f)
            self.table.setHorizontalHeaderItem(c, it)

        for r, name in enumerate("一二三四五"):
            lab = QLabel(f"<div align='center'><b>{name}</b><br>"
                         f"<span style='font-size:7pt'>{ROW_SECTIONS[r][0]}-{ROW_SECTIONS[r][1]}节</span></div>")
            lab.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(r + 1, 0, lab)

        cols = {wd: [] for wd in range(1, 8)}
        for c in self.courses:
            cols[c["weekday"]].append(c)

        mode = "dark" if self._dark else "light"
        line = tokens.NEUTRAL[mode]["stroke"]

        for wd in range(1, 8):
            for row in range(5):
                cell = QWidget()
                style = "background: transparent;"
                if wd == self._today_col:
                    style = f"background: {tokens.NEUTRAL[mode]['layer2']};"
                cell.setStyleSheet(style)
                lay = QVBoxLayout(cell)
                lay.setContentsMargins(2, 2, 2, 2)
                lay.setSpacing(3)
                for c in cols[wd]:
                    if _in_cell(c["sec_start"], row):
                        lay.addWidget(self._course_card(c))
                lay.addStretch(1)
                self.table.setCellWidget(row + 1, wd, cell)

        # 行高自适应（沿用估算，防裁切）
        from PySide6.QtGui import QFont, QFontMetrics
        fm_name = QFontMetrics(QFont("Microsoft YaHei UI", 10, 600))
        fm_meta = QFontMetrics(QFont("Microsoft YaHei UI", 8))
        col_text_w = max((self.table.viewport().width() - 54) // 7 - 30, 60)
        for row in range(5):
            need = 100
            for wd in range(1, 8):
                entries = [c for c in cols[wd] if _in_cell(c["sec_start"], row)]
                if not entries:
                    continue
                h = 10
                for c in entries:
                    sub = f"{c['weeks']}周 · {c['room']}" if c["room"] else f"{c['weeks']}周"
                    n_lines = max(1, -(-fm_name.horizontalAdvance(c["name"]) // col_text_w))
                    m_lines = max(1, -(-fm_meta.horizontalAdvance(sub) // col_text_w))
                    h += 9 + n_lines * 17 + 2 + m_lines * 12 + 7
                h += (len(entries) - 1) * 5
                need = max(need, min(h, 220))
            self.table.setRowHeight(row + 1, need)

        markers = db.list_markers()
        tip = "提示：双击课程卡编辑，右键更多操作。"
        if markers:
            parts = [f"{m['title']} [{m['weeks']}周]" if m["weeks"] else m["title"]
                     for m in markers]
            self.markers_label.setText(tip + "占周不占时间：" + "；".join(parts))
        else:
            self.markers_label.setText(tip)

    def _course_card(self, c):
        bg, fg, bar = tokens.course_color(c["name"], "dark" if self._dark else "light")
        weeks = db.weeks_to_set(c["weeks"])
        in_week = weeks is None or self._show_week in weeks
        if not in_week or not c["enabled"]:
            bg, fg, bar = tokens.dim_course((bg, fg, bar), "dark" if self._dark else "light")
        sub = f"{c['weeks']}周" if c["weeks"] else "每周"
        if c["room"]:
            sub += f" · {c['room']}"
        card = QFrame()
        card.setObjectName("ccard")
        card.setStyleSheet(
            f"QFrame#ccard {{ background: {bg}; border-left: 3px solid {bar};"
            f" border-radius: 8px; }}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 5, 5, 5)
        lay.setSpacing(1)
        from qfluentwidgets import CaptionLabel, StrongBodyLabel
        name = StrongBodyLabel(c["name"])
        name.setStyleSheet(f"color: {fg};")
        name.setWordWrap(True)
        meta = CaptionLabel(sub)
        meta.setStyleSheet(f"color: {fg};")
        meta.setWordWrap(True)
        lay.addWidget(name)
        lay.addWidget(meta)
        if not c["enabled"]:
            card.setToolTip("已停用，不参与提醒")
        card.setCursor(Qt.PointingHandCursor)
        card.mouseDoubleClickEvent = lambda ev, cid=c["id"]: self._edit_course(cid)
        return card

    # ---------- 动作 ----------

    def _shift(self, delta):
        self.week_offset += delta
        self.refresh()

    def _shift_back(self):
        self.week_offset = 0
        self.refresh()

    def _course_at(self, pos):
        """右键位置 -> (cid, menu_x, menu_y)。"""
        item = self.table.indexAt(pos)
        if not item.isValid():
            return None
        cell_widget = self.table.cellWidget(item.row(), item.column())
        if cell_widget is None or item.column() == 0:
            return None
        # 该格第一条课程（简化：编辑该格全部课程的菜单项列出）
        entries = [c for c in self.courses
                   if c["weekday"] == item.column() and _in_cell(c["sec_start"], item.row() - 1)]
        return entries

    def _context_menu(self, pos):
        entries = self._course_at(pos)
        if not entries:
            return
        menu = RoundMenu(parent=self)
        for c in entries:
            menu.addAction(f"编辑：{c['name'][:10]}", lambda cid=c["id"]: self._edit_course(cid))
        if entries:
            menu.addSeparator()
            menu.addAction("添加课程", self._add_course)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _add_course(self):
        dlg = CourseDialog(self.window())
        if dlg.exec() and not dlg.deleted:
            d = dlg.result_data()
            color = max((c["color_idx"] for c in self.courses), default=-1) + 1
            db.add_course(d["name"], d["weekday"], d["sec_start"], d["sec_end"],
                          d["weeks"], d["room"], "", color % 12, d["enabled"])
            self.refresh()

    def _edit_course(self, cid):
        course = next((c for c in self.courses if c["id"] == cid), None)
        if not course:
            return
        dlg = CourseDialog(self.window(), course)
        if not dlg.exec():
            return
        if dlg.deleted:
            db.delete_course(cid)
        else:
            db.update_course(cid, **dlg.result_data())
        self.refresh()

    def import_xlsx(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(self, "选择课表文件", "", "Excel 课表 (*.xlsx)")
        if not path:
            return
        try:
            result = importer.parse_schedule(path)
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"无法解析该文件：{e}")
            return
        if not result["courses"]:
            InfoBar.warning("导入失败", "未解析到课程", parent=self)
            return
        box = QMessageBox(self)
        box.setWindowTitle("确认导入")
        box.setText(f"解析到 {len(result['courses'])} 条课程安排"
                    f"（{len(result['markers'])} 条占周标记）。\n\n"
                    "导入会替换当前全部课程（原数据自动备份），确定？")
        box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        if box.exec() != QMessageBox.Ok:
            return
        rows = [dict(name=c["name"], weekday=c["weekday"], sec_start=c["sec_start"],
                     sec_end=c["sec_end"], weeks=c["weeks"], room=c["room"],
                     note=c["note"], color_idx=c["color_idx"])
                for c in result["courses"]]
        db.replace_all_courses(rows)
        db.replace_markers(result["markers"])
        self.week_offset = 0
        self.refresh()

    def ensure_built(self):
        pass
