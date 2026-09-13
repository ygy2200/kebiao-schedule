# -*- coding: utf-8 -*-
"""功能自测：python tests.py  （纯 assert，无第三方测试框架）"""
import db
import importer

XLSX = r"F:\xwechat_files\wxid_9tjpr6bkzz9q22_0b87\msg\file\2026-09\课表详情.xlsx"


def test_importer():
    r = importer.parse_schedule(XLSX)
    assert len(r["courses"]) == 25, f"课程条目数 {len(r['courses'])} != 25（源表重复填充应去重）"
    assert len(r["markers"]) == 2, f"占周标记 {len(r['markers'])} != 2"

    # 周六有限元 [1-8节] 源表填了 4 行，去重后只有 1 条
    sat_fea = [c for c in r["courses"] if c["weekday"] == 6 and c["name"] == "有限元分析与实践"]
    assert len(sat_fea) == 1 and sat_fea[0]["sec_start"] == 1 and sat_fea[0]["sec_end"] == 8, sat_fea

    # 星期四第1节三条（E4）
    thu1 = [c for c in r["courses"] if c["weekday"] == 4 and c["sec_start"] <= 2]
    assert len(thu1) == 3, thu1
    got = {(c["name"], c["weeks"]) for c in thu1}
    assert ("工程计算方法", "1-6") in got and ("C语言与单片机技术及应用", "9-12") in got \
        and ("工程计算方法", "7-8") in got, got

    # 星期日第5行人工智能与教育创新 [12] 智慧树
    sun = [c for c in r["courses"] if c["weekday"] == 7 and c["name"] == "人工智能与教育创新"]
    assert len(sun) == 1 and sun[0]["sec_start"] == 12 and sun[0]["sec_end"] == 12, sun

    # ● 标记保留 + 每条都有小节定位
    assert any(c["name"].startswith("●") for c in r["courses"])
    assert all(c["weekday"] and c["sec_start"] for c in r["courses"])

    # 占周标记
    titles = {m["title"] for m in r["markers"]}
    assert any("机械设计课程设计" in t for t in titles), titles
    assert any("工程训练" in t for t in titles), titles
    print("test_importer OK")


def test_weeks_utils():
    f = db.weeks_to_set
    assert f("1-4;6-9") == {1, 2, 3, 4, 6, 7, 8, 9}
    assert f("9-12") == {9, 10, 11, 12}
    assert f("12") == {12}
    assert f("") is None and f(None) is None
    assert f("abc") is None
    print("test_weeks_utils OK")


def test_db():
    import os
    import tempfile
    # 测试用独立临时库，不污染正式 data/app.db（教训：污染过一次导致验收截图带测试数据）
    db.DATA_DIR = tempfile.mkdtemp(prefix="kebiao_test_")
    db.DB_PATH = os.path.join(db.DATA_DIR, "test.db")
    db.init_db()

    cid = db.add_course("测试课", 1, 1, 2, "1-8", "8A-414")
    rows = db.list_courses()
    assert len(rows) == 1 and rows[0]["name"] == "测试课"
    db.update_course(cid, room="999")
    assert db.list_courses()[0]["room"] == "999"

    eid = db.add_event("测试日程", "2026-09-10", "14:00", 10)
    db.update_event(eid, done=1)
    assert db.list_events()[0]["done"] == 1

    db.replace_markers([{"title": "占周A", "weeks": "13-14", "note": ""}])
    assert len(db.list_markers()) == 1

    db.set_setting("first_monday", "2026-09-07")
    assert db.get_setting("first_monday") == "2026-09-07"
    assert db.get_setting("不存在", "def") == "def"

    db.replace_all_courses([{"name": "批量", "weekday": 2, "sec_start": 3, "sec_end": 5,
                             "weeks": "", "room": "", "note": "", "color_idx": 0}])
    assert len(db.list_courses()) == 1 and db.list_courses()[0]["name"] == "批量"
    import os
    assert os.path.exists(os.path.join(db.DATA_DIR, "app.backup.db")), "导入前应产生备份"
    print("test_db OK")


def test_reminder():
    import datetime as dt
    import reminder

    # 周次计算：2026-09-07 是第一周周一
    assert reminder.current_week(dt.date(2026, 9, 7), "2026-09-07") == 1
    assert reminder.current_week(dt.date(2026, 9, 13), "2026-09-07") == 1
    assert reminder.current_week(dt.date(2026, 9, 14), "2026-09-07") == 2
    assert reminder.current_week(dt.date(2026, 12, 21), "2026-09-07") == 16
    assert reminder.current_week(dt.date(2026, 9, 6), "2026-09-07") == 0

    mk = lambda **kw: dict(dict(id=1, name="测试课", weekday=1, sec_start=8, sec_end=9,
                                weeks="1-10", room="11-309", note="", enabled=1), **kw)
    # 2026-09-07 周一 第1周；第8节默认 16:00，提前10分 → 15:50 触发
    now = dt.datetime(2026, 9, 7, 15, 50)
    r = reminder.candidates(now, [mk()], [], "2026-09-07")
    assert len(r) == 1 and r[0]["title"] == "测试课" and "11-309" in r[0]["detail"], r
    # 提前量窗口边缘：15:49 不触发、15:51 仍触发（容忍2分钟）
    assert reminder.candidates(now.replace(minute=49), [mk()], [], "2026-09-07") == []
    assert len(reminder.candidates(now.replace(minute=51), [mk()], [], "2026-09-07")) == 1

    # 周次过滤：第 11 周该课不在 1-10 周，不触发
    now11 = dt.datetime(2026, 11, 16, 15, 50)  # 第11周周一
    assert reminder.candidates(now11, [mk()], [], "2026-09-07") == []

    # 禁用课程不触发
    assert reminder.candidates(now, [mk(enabled=0)], [], "2026-09-07") == []

    # 日程提醒：14:00 日程提前10分 → 13:50 触发
    ev = dict(id=7, title="交作业", date="2026-09-07", time="14:00",
              remind_minutes=10, note="高数", done=0)
    now_ev = dt.datetime(2026, 9, 7, 13, 50)
    r = reminder.candidates(now_ev, [], [ev], "2026-09-07")
    assert len(r) == 1 and r[0]["kind"] == "event", r
    # 已完成 / 全天 / remind=0 不触发
    assert reminder.candidates(now_ev, [], [dict(ev, done=1)], "2026-09-07") == []
    assert reminder.candidates(now_ev, [], [dict(ev, time="")], "2026-09-07") == []
    assert reminder.candidates(now_ev, [], [dict(ev, remind_minutes=0)], "2026-09-07") == []
    # 日期不符不触发
    assert reminder.candidates(now_ev, [], [dict(ev, date="2026-09-08")], "2026-09-07") == []
    print("test_reminder OK")


def test_lunar():
    import datetime as dt
    import lunar

    def l(d):
        return lunar.solar_to_lunar(dt.date(*d))

    # 春节锚点（正月初一）与中秋锚点（八月十五）
    assert l((2024, 2, 10))[1:] == (1, 1, False), l((2024, 2, 10))
    assert l((2025, 1, 29))[1:] == (1, 1, False), l((2025, 1, 29))
    assert l((2026, 2, 17))[1:] == (1, 1, False), l((2026, 2, 17))
    assert l((2026, 9, 25))[1:] == (8, 15, False), l((2026, 9, 25))
    # 闰年锚点：2023 闰二月，2023-03-22 是闰二月初一
    assert l((2023, 3, 22))[1:] == (2, 1, True), l((2023, 3, 22))
    # 节日名
    assert lunar.festival_name(dt.date(2026, 2, 17)) == "春节"
    assert lunar.festival_name(dt.date(2026, 9, 25)) == "中秋节"
    assert lunar.festival_name(dt.date(2026, 10, 1)) == "国庆节"
    # 除夕：2026-02-16 是腊月廿九（2026 春节前一天）
    assert lunar.festival_name(dt.date(2026, 2, 16)) == "除夕"
    # 日期串不抛异常且含"农历"
    s = lunar.date_line(dt.date(2026, 9, 7))
    assert "农历" in s and "星期" in s, s
    print("test_lunar OK", "| 2026-09-07 =", s)


def test_schedule_query():
    """今日时间线三态（app/core/schedule_query.today_courses，显式传参不碰正式库）"""
    import datetime as dt
    import reminder
    from app.core.schedule_query import today_courses

    c = {"name": "三态课", "weekday": 1, "sec_start": 8, "sec_end": 8,
         "weeks": "1-16", "room": "T101", "note": "", "enabled": 1}
    fm, mapping = "2026-09-07", reminder.DEFAULT_SECTION_TIMES  # 8节=16:00，45min → 16:00-16:45

    def state(hhmm):
        h, m = map(int, hhmm.split(":"))
        r = today_courses(dt.datetime(2026, 9, 7, h, m), [c], fm, mapping)
        return r[0]["state"]

    assert state("15:59") == "upcoming"
    assert state("16:00") == "current"   # 整点开始边界 = current
    assert state("16:20") == "current"
    assert state("16:45") == "done"      # 结束边界 = done
    assert state("17:50") == "done"
    # 周次过滤：2026-12-28 为第 17 周，不在 1-16
    r = today_courses(dt.datetime(2026, 12, 28, 16, 20), [c], fm, mapping)
    assert r == []
    print("test_schedule_query OK")


def test_holidays():
    """法定节假日三态（内置 2026 兜底；tempdir 隔离缓存只走 BUILTIN）"""
    import datetime as dt
    import tempfile
    from app.core import holidays

    db.DATA_DIR = tempfile.mkdtemp(prefix="kebiao_test_holidays_")
    assert holidays.status(dt.date(2026, 9, 25)) == "off"   # 中秋假期
    assert holidays.status(dt.date(2026, 9, 20)) == "work"  # 国庆调休
    assert holidays.status(dt.date(2026, 9, 15)) is None    # 普通日
    assert holidays.status("2026-10-01") == "off"           # ISO 字符串入参
    assert holidays.status(dt.date(2025, 5, 1)) is None     # 无数据年份
    print("test_holidays OK")


def test_ganzhi():
    """节气/丰收节/干支（月历详情行用；干支经 2000-01-01=戊午 独立锚点验证）"""
    import datetime as dt
    import lunar

    assert lunar.solar_term(dt.date(2026, 9, 7)) == "白露"
    assert lunar.festival_name(dt.date(2026, 9, 23)) == "丰收节"  # 秋分
    # 2026-09-25=壬寅（与系统日历一致）；9-12 为 13 天前 = 己丑
    assert lunar.ganzhi_day(dt.date(2026, 9, 25)) == "壬寅"
    assert lunar.ganzhi_day(dt.date(2026, 9, 12)) == "己丑"
    assert lunar.ganzhi_year(2026) == ("丙午", "马")
    assert lunar.ganzhi_month(2026, 8) == "丁酉"
    assert lunar.day_detail_line(dt.date(2026, 9, 25), days_after=13) == \
        "13天后 八月十五 丙午年 [马] 丁酉月 壬寅日"
    assert lunar.day_detail_line(dt.date(2026, 9, 12), days_after=0) == \
        "今天 八月初二 丙午年 [马] 丁酉月 己丑日"
    print("test_ganzhi OK")


if __name__ == "__main__":
    test_importer()
    test_weeks_utils()
    test_db()
    test_reminder()
    test_lunar()
    test_schedule_query()
    test_holidays()
    test_ganzhi()
    print("ALL TESTS PASSED")
