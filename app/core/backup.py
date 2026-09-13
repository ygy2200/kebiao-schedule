# -*- coding: utf-8 -*-
"""M8 导入导出：ICS 导出 / JSON 全量备份恢复。"""
import datetime as dt
import json
import os

import db


def export_ics(path, events=None):
    """日程 → ICS（Windows 日历 / 手机日历可导入）。带时间的事件附提醒。"""
    if events is None:
        events = db.list_events()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//ScheduleDesk//kebiao-schedule//CN", "CALSCALE:GREGORIAN"]
    n = 0
    for e in events:
        if e["done"]:
            continue
        n += 1
        uid = f"kebiao-{e['id']}@schedule-desk"
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
        lines.append(f"DTSTAMP:{stamp}Z")
        if e["time"]:
            hh, mm = e["time"].split(":")
            start = e["date"].replace("-", "") + "T" + hh + mm + "00"
            end_min = int(hh) * 60 + int(mm) + 60
            end = e["date"].replace("-", "") + "T%02d%02d00" % (end_min // 60, end_min % 60)
            lines.append(f"DTSTART:{start}")
            lines.append(f"DTEND:{end}")
            if e["remind_minutes"]:
                lines.append("BEGIN:VALARM")
                lines.append("ACTION:DISPLAY")
                lines.append(f"DESCRIPTION:{e['title']}")
                lines.append(f"TRIGGER:-PT{e['remind_minutes']}M")
                lines.append("END:VALARM")
        else:
            d = dt.date.fromisoformat(e["date"])
            nxt = d + dt.timedelta(days=1)
            lines.append(f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}")
            lines.append(f"DTEND;VALUE=DATE:{nxt.strftime('%Y%m%d')}")
        lines.append(f"SUMMARY:{e['title']}")
        if e["note"]:
            lines.append(f"DESCRIPTION:{e['note']}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\r\n".join(lines))
    return n


BACKUP_KEEP = 5


def backup_all():
    """全量备份 → data/backups/backup_*.json，保留最近 BACKUP_KEEP 份。返回路径。"""
    backup_dir = os.path.join(db.DATA_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    payload = {
        "app": "kebiao-schedule",
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "courses": [dict(r) for r in db.list_courses()],
        "events": [dict(r) for r in db.list_events()],
        "markers": [dict(r) for r in db.list_markers()],
        "settings": _dump_settings(),
    }
    path = os.path.join(backup_dir, "backup_%s.json" %
                        dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    # 轮换：仅保留最近 N 份
    backups = sorted(f for f in os.listdir(backup_dir) if f.startswith("backup_"))
    for old in backups[:-BACKUP_KEEP]:
        os.remove(os.path.join(backup_dir, old))
    return path


def _dump_settings():
    with db.connect() as con:
        return {r["key"]: r["value"] for r in
                con.execute("SELECT key, value FROM settings")}


def restore_from(path):
    """从备份恢复（覆盖现有数据）。返回统计 dict。"""
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    db.backup_db()
    with db.connect() as con:
        con.execute("DELETE FROM courses")
        con.execute("DELETE FROM events")
        con.execute("DELETE FROM markers")
        for r in payload.get("courses", []):
            cols = ",".join(r.keys())
            marks = ",".join("?" for _ in r)
            con.execute(f"INSERT INTO courses({cols}) VALUES({marks})", tuple(r.values()))
        for r in payload.get("events", []):
            r = {k: v for k, v in r.items() if k != "priority"}
            cols = ",".join(r.keys())
            marks = ",".join("?" for _ in r)
            try:
                con.execute(f"INSERT INTO events({cols}) VALUES({marks})", tuple(r.values()))
            except Exception:
                pass
        for r in payload.get("markers", []):
            con.execute("INSERT INTO markers(title,weeks,note) VALUES(?,?,?)",
                        (r["title"], r["weeks"], r.get("note", "")))
        for k, v in payload.get("settings", {}).items():
            con.execute("INSERT INTO settings(key,value) VALUES(?,?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))
    return {"courses": len(db.list_courses()), "events": len(db.list_events())}
