# -*- coding: utf-8 -*-
"""今日课程查询（纯函数，可单测）：把 db 课程转为今日时间线数据。

一节按 45 分钟计；sec_end 结束时刻 = 该节开始 + 45min。
"""
import datetime as dt

import db
import reminder

LESSON_MINUTES = 45


def _end_hhmm(start_hhmm, sec_start, sec_end, mapping):
    """结束时刻 = 最后一节的开始 + 45 分钟。"""
    last = mapping.get(sec_end) or start_hhmm
    h, m = map(int, last.split(":"))
    total = h * 60 + m + LESSON_MINUTES
    return f"{total // 60 % 24:02d}:{total % 60:02d}"


def _state(now_hhmm, start, end):
    n = int(now_hhmm.replace(":", ""))
    s, e = int(start.replace(":", "")), int(end.replace(":", ""))
    if n < s:
        return "upcoming"
    if n >= e:
        return "done"
    return "current"


def today_courses(now, courses, first_monday=None, mapping=None):
    """today 的课程时间线。

    now: datetime；courses: sqlite Row 列表
    返回 [{"name","start","end","room","sec","state"}...] 按 start 排序。
    """
    first_monday = first_monday or db.get_setting(
        "first_monday", reminder.DEFAULT_FIRST_MONDAY)
    mapping = mapping or reminder.section_times()
    today = now.date()
    weekday = today.isoweekday()
    week = reminder.current_week(today, first_monday)
    now_hhmm = now.strftime("%H:%M")
    out = []
    if week < 1:
        return out
    for c in courses:
        if not c["enabled"] or c["weekday"] != weekday:
            continue
        weeks = db.weeks_to_set(c["weeks"])
        if weeks is not None and week not in weeks:
            continue
        start = reminder.section_start_hhmm(c["sec_start"], mapping)
        if start is None:
            continue
        end = _end_hhmm(start, c["sec_start"], c["sec_end"], mapping)
        out.append({
            "name": c["name"],
            "start": start,
            "end": end,
            "room": c["room"],
            "sec": f"{c['sec_start']}-{c['sec_end']}",
            "state": _state(now_hhmm, start, end),
        })
    out.sort(key=lambda x: x["start"])
    return out
