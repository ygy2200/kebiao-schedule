# -*- coding: utf-8 -*-
"""课表 xlsx 导入：解析为课程条目 + 占周标记，供预览和写库。

源格式（微信小程序导出的《课表详情.xlsx》）：
- 第3行表头：节次 | 星期一..星期日（B3:H3）
- 第4-8行：节次一~五 × 7 天，单元格内 \r\n 分隔多条，每条形如
  "课程名  [9-12周] [1-2] 8A-414"
- 第9行："占周不占时间" + 占周课程列表
"""
import re

import openpyxl

DAY_RE = re.compile(r"^星期")


def _split_marks(text):
    """'工程计算方法  [1-6周] [1-2] 8A-414' -> (name, '1-6;7-8'式weeks或'', (sec_start,sec_end)或None, room)"""
    marks = re.findall(r"\[([^\]]+)\]", text)
    name = text.split("[")[0].strip()
    room = text.split("]")[-1].strip() if "]" in text else ""
    weeks, sections = "", None
    for m in marks:
        m = m.strip()
        if "周" in m:
            # "1-4,6-9周" / "9-12周" -> "1-4;6-9"
            weeks = ";".join(p.strip() for p in m.rstrip("周").replace("，", ",").split(",") if p.strip())
        else:
            nums = re.findall(r"\d+", m)
            if len(nums) >= 2:
                sections = (int(nums[0]), int(nums[1]))
            elif len(nums) == 1:
                sections = (int(nums[0]), int(nums[0]))
    return name, weeks, sections, room


def parse_schedule(path):
    """返回 {"courses": [course dict...], "markers": [{"title","weeks"}...], "title": str}"""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    title = str(ws.cell(1, 1).value or "课表").strip()

    # 找表头行（含"星期一"的行），其下 5 行为数据
    head_row = None
    for r in range(1, min(ws.max_row, 10) + 1):
        if ws.cell(r, 2).value and DAY_RE.match(str(ws.cell(r, 2).value).strip()):
            head_row = r
            break
    if head_row is None:
        raise ValueError("未找到星期表头，格式不支持")

    courses, markers = [], []
    color_map = {}

    def color_of(name):
        if name not in color_map:
            color_map[name] = len(color_map) % 12
        return color_map[name]

    for r in range(head_row + 1, head_row + 6):
        for c in range(2, 9):
            v = ws.cell(r, c).value
            if not v or not str(v).strip():
                continue
            for line in str(v).replace("\r\n", "\n").split("\n"):
                line = line.strip()
                if not line:
                    continue
                name, weeks, sections, room = _split_marks(line)
                if not name:
                    continue
                if sections is None:  # 无小节号的条目跳过提醒定位，仍按 1-2 兜底显示
                    sections = (1, 2)
                courses.append({
                    "name": name, "weekday": c - 1,
                    "sec_start": sections[0], "sec_end": sections[1],
                    "weeks": weeks, "room": room,
                    "note": "", "color_idx": color_of(name),
                })

    # 源表会把同一节课在多个节次行重复填（如 [1-8节] 填满 4 行），按键去重
    seen = set()
    unique = []
    for c in courses:
        key = (c["name"], c["weekday"], c["sec_start"], c["sec_end"], c["weeks"], c["room"])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    # 占周不占时间行：标签在 A 列，内容在 B 列
    for r in range(head_row + 6, min(ws.max_row, head_row + 12) + 1):
        label = str(ws.cell(r, 1).value or "")
        v = ws.cell(r, 2).value
        if "占周" in label and v and str(v).strip():
            for line in str(v).replace("\r\n", "\n").split("\n"):
                line = line.strip()
                if not line:
                    continue
                name, weeks, _sec, note = _split_marks(line)
                markers.append({"title": name or line, "weeks": weeks, "note": note})
    return {"title": title, "courses": unique, "markers": markers}


if __name__ == "__main__":
    import json
    import sys
    result = parse_schedule(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=1)[:3000])
    print("... courses:", len(result["courses"]), "markers:", len(result["markers"]))
