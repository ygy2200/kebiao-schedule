# -*- coding: utf-8 -*-
"""公农历转换 + 节日名（纯本地，无依赖）。

农历数据表为公开常量表（1900-2100），锚点测试见 tests.py：
2024-02-10 / 2025-01-29 / 2026-02-17 春节、2026-09-25 中秋。
"""
import datetime as dt

# 每年一个十六进制数：低 4 位 = 闰月月份(0 无闰)；0x10000 位 = 闰月大小(1 大 30 天)；
# 位 0x8000..0x0010 依次是正月..（闰）腊月的大小(1 大 30 天)
LUNAR_INFO = [
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,  # 1900-1909
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,  # 1910-1919
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,  # 1920-1929
    0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,  # 1930-1939
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,  # 1940-1949
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0,  # 1950-1959
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,  # 1960-1969
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,  # 1970-1979
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,  # 1980-1989
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0,  # 1990-1999
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,  # 2000-2009
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,  # 2010-2019
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,  # 2020-2029
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,  # 2030-2039
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,  # 2040-2049
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0,  # 2050-2059
    0x0a2e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,  # 2060-2069
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,  # 2070-2079
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,  # 2080-2089
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,  # 2090-2099
    0x0d520,  # 2100
]

_BASE = dt.date(1900, 1, 31)  # 1900 年正月初一

MONTH_NAMES = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
DAY_TENS = ["初", "十", "廿", "三"]
DAY_NAMES = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]

LUNAR_FESTIVALS = {  # (月, 日, 是否闰月) -> 节日
    (1, 1): "春节", (1, 15): "元宵节", (5, 5): "端午节", (7, 7): "七夕",
    (8, 15): "中秋节", (9, 9): "重阳节", (12, 8): "腊八节",
}
SOLAR_FESTIVALS = {(1, 1): "元旦", (5, 1): "劳动节", (6, 1): "儿童节",
                   (10, 1): "国庆节"}


def _leap_month(year):
    return LUNAR_INFO[year - 1900] & 0xF


def _month_days(year, month, leap=False):
    """某月天数。month: 1..12；leap=True 表示查闰月。"""
    info = LUNAR_INFO[year - 1900]
    if leap:
        return 30 if info & 0x10000 else 29
    return 30 if info & (0x8000 >> (month - 1)) else 29


def _year_days(year):
    """农历年总天数。"""
    info = LUNAR_INFO[year - 1900]
    total = 0
    for m in range(1, 13):
        total += 30 if info & (0x8000 >> (m - 1)) else 29
    leap = info & 0xF
    if leap:
        total += 30 if info & 0x10000 else 29
    return total


def solar_to_lunar(date):
    """公历 -> (农历年, 月, 日, 是否闰月)。支持 1900-2100。"""
    if not (dt.date(1900, 1, 31) <= date <= dt.date(2100, 12, 31)):
        raise ValueError("仅支持 1900-2100")
    offset = (date - _BASE).days
    year = 1900
    while offset >= _year_days(year):
        offset -= _year_days(year)
        year += 1

    leap_m = _leap_month(year)
    month, leap_flag = 1, False
    while True:
        days = _month_days(year, month)
        if offset < days:
            break
        offset -= days
        if leap_m == month and not leap_flag:  # 闰X月排在X月之后
            days = 30 if LUNAR_INFO[year - 1900] & 0x10000 else 29
            if offset < days:
                leap_flag = True
                break
            offset -= days
        month += 1
        if month > 12:
            break
    return year, month, offset + 1, leap_flag


def lunar_month_str(month, leap):
    return ("闰" if leap else "") + MONTH_NAMES[month - 1] + "月"


def lunar_day_str(day):
    if day == 10:
        return "初十"
    if day == 20:
        return "二十"
    if day == 30:
        return "三十"
    return DAY_TENS[day // 10] + DAY_NAMES[day % 10 - 1]


def festival_name(date):
    """当天节日名，无则返回空串。除夕按腊月最后一天动态判定。"""
    solar = SOLAR_FESTIVALS.get((date.month, date.day))
    if solar:
        return solar
    _y, m, d, leap = solar_to_lunar(date)
    if not leap:
        if m == 12:
            # 除夕 = 腊月最后一天（下一天是正月初一）
            nxt = date + dt.timedelta(days=1)
            ny, nm, nd, nl = solar_to_lunar(nxt)
            if (nm, nd, nl) == (1, 1, False):
                return "除夕"
        name = LUNAR_FESTIVALS.get((m, d))
        if name:
            return name
    return ""


def date_line(date):
    """主页头部日期串：'9月7日 星期一 农历七月廿六 中秋节'式。"""
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    _y, m, d, leap = solar_to_lunar(date)
    parts = [f"{date.month}月{date.day}日", f"星期{weekdays[date.isoweekday() - 1]}",
             f"农历{lunar_month_str(m, leap)}{lunar_day_str(d)}"]
    fest = festival_name(date)
    if fest:
        parts.append(fest)
    return "  ".join(parts)
