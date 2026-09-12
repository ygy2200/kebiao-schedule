# -*- coding: utf-8 -*-
"""提醒引擎：纯函数部分可脱离 Qt 单测；QTimer 轮询在 main 里接。

触发判定（分钟粒度）：trigger <= now < trigger+2 分钟，配合调用方去重。
"""
import datetime as dt
import json

import db

DEFAULT_FIRST_MONDAY = "2026-09-07"

# 小节 -> 开始时刻（默认表，设置里可覆盖）
DEFAULT_SECTION_TIMES = {
    1: "08:00", 2: "08:55", 3: "10:00", 4: "10:55", 5: "11:50",
    6: "14:00", 7: "14:55", 8: "16:00", 9: "16:55",
    10: "19:00", 11: "19:55", 12: "20:50",
}

DEFAULT_AHEAD = 10  # 课表默认提前分钟数


def current_week(today, first_monday):
    """first_monday: "YYYY-MM-DD"（第一周周一）。返回第几周，至少 1。"""
    first = dt.date.fromisoformat(str(first_monday))
    delta = (today - first).days
    if delta < 0:
        return 0  # 学期未开始
    return delta // 7 + 1


def section_times():
    """默认表与设置合并后的完整映射 {int: "HH:MM"}"""
    raw = db.get_setting("section_times")
    mapping = dict(DEFAULT_SECTION_TIMES)
    if raw:
        try:
            for k, v in json.loads(raw).items():
                mapping[int(k)] = v
        except (ValueError, json.JSONDecodeError):
            pass
    return mapping


def section_start_hhmm(sec, mapping=None):
    m = mapping or section_times()
    return m.get(sec) or m.get(min(m))  # 无映射的小节退化为最早节，避免崩溃


def _in_window(now_hhmm, trigger_hhmm):
    """trigger <= now < trigger+2 分钟"""
    t = list(map(int, trigger_hhmm.split(":")))
    n = list(map(int, now_hhmm.split(":")))
    n_abs, t_abs = n[0] * 60 + n[1], t[0] * 60 + t[1]
    return t_abs <= n_abs < t_abs + 2


def candidates(now, courses, events, first_monday=None, ahead=None):
    """当前时刻应触发的提醒列表（不去重）。

    now: datetime；courses/events: sqlite3.Row 列表
    返回 [{"kind","key","title","detail"}]，key 用于去重（当日唯一）。
    """
    first_monday = first_monday or DEFAULT_FIRST_MONDAY
    ahead = DEFAULT_AHEAD if ahead is None else ahead
    today = now.date()
    weekday = today.isoweekday()  # 1=周一..7=周日
    week = current_week(today, first_monday)
    now_hhmm = now.strftime("%H:%M")
    out = []

    if week >= 1:
        mapping = section_times()
        for c in courses:
            if not c["enabled"]:
                continue
            if c["weekday"] != weekday:
                continue
            weeks = db.weeks_to_set(c["weeks"])
            if weeks is not None and week not in weeks:
                continue
            start_hhmm = section_start_hhmm(c["sec_start"], mapping)
            if start_hhmm is None:
                continue
            trigger = _minus_minutes(start_hhmm, ahead)
            if _in_window(now_hhmm, trigger):
                out.append({
                    "kind": "course",
                    "key": f"c{c['id']}-{today}",
                    "title": c["name"],
                    "detail": f"{start_hhmm} 第{c['sec_start']}-{c['sec_end']}节"
                              + (f" · {c['room']}" if c["room"] else ""),
                })

    for e in events:
        if e["done"] or e["date"] != today.isoformat():
            continue
        if not e["time"]:
            continue  # 全天日程不弹窗，列表内可见
        ahead_e = e["remind_minutes"] if e["remind_minutes"] is not None else ahead
        if ahead_e <= 0:
            continue
        trigger = _minus_minutes(e["time"], ahead_e)
        if _in_window(now_hhmm, trigger):
            out.append({
                "kind": "event",
                "key": f"e{e['id']}-{today}",
                "title": e["title"],
                "detail": f"{e['time']}" + (f" · {e['note']}" if e["note"] else ""),
            })
    return out


def _minus_minutes(hhmm, minutes):
    h, m = map(int, hhmm.split(":"))
    total = h * 60 + m - minutes
    if total < 0:
        total += 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"
