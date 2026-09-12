# -*- coding: utf-8 -*-
"""数据层：SQLite 单文件，函数式接口。"""
import contextlib
import os
import sqlite3
import sys


def _base_dir():
    if getattr(sys, "frozen", False):  # PyInstaller 打包后数据放 exe 旁边
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DATA_DIR = os.path.join(_base_dir(), "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    weekday INTEGER NOT NULL,          -- 1=周一 .. 7=周日
    sec_start INTEGER NOT NULL,        -- 小节号
    sec_end   INTEGER NOT NULL,
    weeks TEXT NOT NULL DEFAULT '',    -- "9-12;13-14"
    room TEXT DEFAULT '',
    note TEXT DEFAULT '',
    color_idx INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL,                -- YYYY-MM-DD
    time TEXT DEFAULT '',              -- HH:MM，空=全天
    remind_minutes INTEGER DEFAULT 10, -- 提前量，0=不提醒
    note TEXT DEFAULT '',
    done INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS markers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    weeks TEXT NOT NULL DEFAULT '',
    note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,               -- course / event
    title TEXT NOT NULL,
    detail TEXT DEFAULT '',
    fired_at TEXT NOT NULL,           -- ISO 时间
    snooze_until TEXT DEFAULT '',     -- 稍后提醒时刻（空=已处理）
    read INTEGER DEFAULT 0
);
"""


@contextlib.contextmanager
def connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        with con:  # 事务提交/回滚
            yield con
    finally:
        con.close()  # Windows 上必须显式关，否则文件被锁


def init_db():
    with connect() as con:
        con.executescript(SCHEMA)
        # migration：events 加 priority 列（向后兼容，加列不删列）
        cols = {r["name"] for r in con.execute("PRAGMA table_info(events)")}
        if "priority" not in cols:
            con.execute("ALTER TABLE events ADD COLUMN priority INTEGER DEFAULT 1")
        con.execute("PRAGMA user_version = 2")


# ---------- settings ----------

def get_setting(key, default=None):
    with connect() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key, value):
    with connect() as con:
        con.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


# ---------- courses ----------

def add_course(name, weekday, sec_start, sec_end, weeks="", room="",
               note="", color_idx=0, enabled=1):
    with connect() as con:
        cur = con.execute(
            "INSERT INTO courses(name,weekday,sec_start,sec_end,weeks,room,note,color_idx,enabled) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (name, weekday, sec_start, sec_end, weeks, room, note, color_idx, enabled))
        return cur.lastrowid


def list_courses():
    with connect() as con:
        return con.execute("SELECT * FROM courses ORDER BY weekday, sec_start").fetchall()


def update_course(cid, **fields):
    keys = ",".join(f"{k}=?" for k in fields)
    with connect() as con:
        con.execute(f"UPDATE courses SET {keys} WHERE id=?", (*fields.values(), cid))


def delete_course(cid):
    with connect() as con:
        con.execute("DELETE FROM courses WHERE id=?", (cid,))


def backup_db():
    """覆盖导入前调用：app.db -> app.backup.db"""
    import shutil
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, os.path.join(DATA_DIR, "app.backup.db"))


def replace_all_courses(rows):
    """整表替换（导入用）。rows = add_course 的字段 dict 列表。"""
    backup_db()
    with connect() as con:
        con.execute("DELETE FROM courses")
        for r in rows:
            con.execute(
                "INSERT INTO courses(name,weekday,sec_start,sec_end,weeks,room,note,color_idx,enabled) "
                "VALUES(:name,:weekday,:sec_start,:sec_end,:weeks,:room,:note,:color_idx,1)", r)


# ---------- events ----------

def add_event(title, date, time="", remind_minutes=10, note="", priority=1):
    with connect() as con:
        cur = con.execute(
            "INSERT INTO events(title,date,time,remind_minutes,note,priority) "
            "VALUES(?,?,?,?,?,?)",
            (title, date, time, remind_minutes, note, priority))
        return cur.lastrowid


# ---------- reminders 留痕 ----------

def add_reminder(kind, title, detail, fired_at, snooze_until=""):
    with connect() as con:
        cur = con.execute(
            "INSERT INTO reminders(kind,title,detail,fired_at,snooze_until) VALUES(?,?,?,?,?)",
            (kind, title, detail, fired_at, snooze_until))
        return cur.lastrowid


def list_reminders(only_unread=False):
    q = "SELECT * FROM reminders"
    if only_unread:
        q += " WHERE read=0"
    with connect() as con:
        return con.execute(q + " ORDER BY fired_at DESC LIMIT 200").fetchall()


def update_reminder(rid, **fields):
    keys = ",".join(f"{k}=?" for k in fields)
    with connect() as con:
        con.execute(f"UPDATE reminders SET {keys} WHERE id=?", (*fields.values(), rid))


def list_events():
    with connect() as con:
        return con.execute("SELECT * FROM events ORDER BY date, time").fetchall()


def update_event(eid, **fields):
    keys = ",".join(f"{k}=?" for k in fields)
    with connect() as con:
        con.execute(f"UPDATE events SET {keys} WHERE id=?", (*fields.values(), eid))


def delete_event(eid):
    with connect() as con:
        con.execute("DELETE FROM events WHERE id=?", (eid,))


# ---------- markers ----------

def replace_markers(rows):
    with connect() as con:
        con.execute("DELETE FROM markers")
        for r in rows:
            con.execute("INSERT INTO markers(title,weeks,note) VALUES(:title,:weeks,:note)", r)


def list_markers():
    with connect() as con:
        return con.execute("SELECT * FROM markers ORDER BY id").fetchall()


# ---------- 周次工具 ----------

def weeks_to_set(s):
    """"1-4;6-9" -> {1,2,3,4,6,7,8,9}；空串/解析失败 -> None（表示每周）"""
    if not s or not s.strip():
        return None
    out = set()
    for part in s.replace("，", ",").split(";"):
        part = part.strip().rstrip("周")
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                out.update(range(int(a), int(b) + 1))
            except ValueError:
                return None
        else:
            try:
                out.add(int(part))
            except ValueError:
                return None
    return out or None
