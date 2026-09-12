# -*- coding: utf-8 -*-
"""法定节假日数据：内置兜底 + 联网自动更新（holiday-cn 开源库）+ 本地缓存。

数据源：NateScarlet/holiday-cn（紧跟国务院通知，MIT）
策略：data/holidays_cache.json（30 天过期）→ jsdelivr 直连 → 系统代理 → 7890 显式
     全部失败时用内置数据（离线可用）。
查询：status(date) -> "off"（法定放假）/ "work"（调休上班）/ None（普通日）
"""
import datetime as dt
import json
import os
import urllib.request

import db

CACHE_TTL = 30 * 24 * 3600

# 内置兜底：国务院办公厅《关于2026年部分节假日安排的通知》（国办发明电〔2025〕）
BUILTIN = {
    "2026": {
        "off": [
            "2026-01-01", "2026-01-02", "2026-01-03",
            "2026-02-15", "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19",
            "2026-02-20", "2026-02-21", "2026-02-22", "2026-02-23",
            "2026-04-04", "2026-04-05", "2026-04-06",
            "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05",
            "2026-06-19", "2026-06-20", "2026-06-21",
            "2026-09-25", "2026-09-26", "2026-09-27",
            "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
            "2026-10-05", "2026-10-06", "2026-10-07",
        ],
        "work": ["2026-01-04", "2026-02-14", "2026-02-28",
                 "2026-05-09", "2026-09-20", "2026-10-10"],
    }
}


def _cache_path():
    return os.path.join(db.DATA_DIR, "holidays_cache.json")


def load() -> dict:
    """{年份字符串: {"off": [...], "work": [...]}}。缓存优先，缺失年份用内置补。"""
    data = {}
    try:
        with open(_cache_path(), encoding="utf-8") as f:
            cache = json.load(f)
        data = cache.get("years", {})
    except Exception:
        pass
    merged = {str(y): dict(v) for y, v in BUILTIN.items()}
    merged.update(data)
    return merged


def cache_info():
    """(存在?, fetched_at 字符串或空)"""
    try:
        with open(_cache_path(), encoding="utf-8") as f:
            cache = json.load(f)
        return True, cache.get("fetched_at", "")
    except Exception:
        return False, ""


def _fetch_year_online(year):
    """多轮尝试：默认 opener（含系统代理）→ 显式 7890 → 各轮 8 秒超时。"""
    import time
    proxy = "http://127.0.0.1:7890"
    url = "https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/%d.json" % year
    attempts = [("direct", None), ("proxy7890", proxy)]
    last_err = None
    for name, p in attempts:
        try:
            handlers = []
            if p:
                handlers.append(urllib.request.ProxyHandler(
                    {"http": p, "https": p}))
            opener = urllib.request.build_opener(*handlers)
            req = urllib.request.Request(
                url, headers={"User-Agent": "schedule-desk/2.0"})
            t0 = time.time()
            with opener.open(req, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            if data.get("year") != year or not data.get("days"):
                raise ValueError("数据结构异常")
            return data, f"{name} ({time.time() - t0:.1f}s)"
        except Exception as e:
            last_err = f"{name}: {type(e).__name__}"
    raise ConnectionError(last_err or "全部数据源失败")


def refresh(years=None, force=False):
    """联网更新。返回 (更新了哪些年, 失败描述或空)。"""
    now = dt.datetime.now()
    years = years or [now.year, now.year + 1]
    cache = {"fetched_at": "", "years": {}}
    try:
        with open(_cache_path(), encoding="utf-8") as f:
            cache = json.load(f)
    except Exception:
        pass

    need = []
    for y in years:
        ys = str(y)
        if ys not in cache.get("years", {}):
            need.append(y)
    if not force and not need:
        fetched_at = cache.get("fetched_at", "")
        try:
            age = now.timestamp() - dt.datetime.fromisoformat(fetched_at).timestamp()
            if age < CACHE_TTL:
                return [], f"缓存仍新鲜（{fetched_at[:10]} 拉取）"
        except Exception:
            pass
        need = list(years)

    got, errs = [], []
    for y in need:
        try:
            data, src = _fetch_year_online(y)
            off = [d["date"] for d in data["days"] if d["isOffDay"]]
            work = [d["date"] for d in data["days"] if not d["isOffDay"]]
            cache.setdefault("years", {})[str(y)] = {"off": off, "work": work}
            got.append(y)
        except Exception as e:
            errs.append(f"{y}: {e}")

    if got:
        cache["fetched_at"] = now.isoformat(timespec="seconds")
        cache["source"] = "holiday-cn"
        os.makedirs(db.DATA_DIR, exist_ok=True)
        with open(_cache_path(), "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1)
    return got, "；".join(errs)


def status(date):
    """date: datetime.date 或 ISO 字符串 -> 'off' / 'work' / None。"""
    if isinstance(date, dt.date):
        iso = date.isoformat()
    else:
        iso = str(date)
    years = load()
    y = iso[:4]
    ydata = years.get(y)
    if not ydata:
        return None
    if iso in ydata.get("off", []):
        return "off"
    if iso in ydata.get("work", []):
        return "work"
    return None
