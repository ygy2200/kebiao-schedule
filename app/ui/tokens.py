# -*- coding: utf-8 -*-
"""设计 tokens（v2.1 规范单一来源）。禁止在组件里写裸 hex。

色彩纪律：
- 中性色阶占 95% 面积；accent 只出现在 7 处（主按钮/导航选中/时刻线/进行中呼吸点/今日表头/focus/周徽章）
- 课程色用 course_color() HSL 受控生成，S/L 全局锁死只转 hue
"""
import hashlib

# ---------- 中性色阶 ----------
NEUTRAL = {
    "light": {
        "layer0": "#f9f9fb",   # 页面底
        "layer1": "#ffffff",   # 卡片
        "layer2": "#f5f5f7",   # 卡片内嵌区 / hover
        "stroke": "rgba(0,0,0,0.06)",
        "text1": "#1b1b1f",
        "text2": "#61616b",
        "text3": "#9c9ca6",
    },
    "dark": {
        "layer0": "#161616",
        "layer1": "#242424",
        "layer2": "#2c2c2c",
        "stroke": "rgba(255,255,255,0.07)",
        "text1": "#f3f3f3",
        "text2": "#a4a4ac",
        "text3": "#6a6a72",
    },
}

# ---------- 强调色 ----------
ACCENT = {"light": "#0067C0", "dark": "#4CC2FF"}
ACCENT_PRESETS = {  # 设置页可换（名称 -> (浅, 深)）
    "Windows 蓝": ("#0067C0", "#4CC2FF"),
    "紫": ("#7C5CBF", "#B39DDB"),
    "青": ("#00818B", "#4DD0D9"),
    "绿": ("#0F7B0F", "#6BCB77"),
    "琥珀": ("#9D5D00", "#FFB74D"),
    "橙": ("#CA5010", "#FF8A65"),
    "玫红": ("#C239B3", "#F48FB1"),
    "石板灰": ("#5D6D7E", "#95A5A6"),
}

# ---------- 语义色 ----------
SEMANTIC = {
    "light": {"success": "#0F7B0F", "warning": "#9D5D00", "danger": "#C50F1F"},
    "dark": {"success": "#6BCB77", "warning": "#FFB74D", "danger": "#FF6B6B"},
}

# ---------- 字阶 ----------
TYPE_SCALE = {
    "display": (28, 36, 600),
    "title": (20, 28, 600),
    "subtitle": (16, 22, 600),
    "body": (14, 20, 400),
    "caption": (12, 16, 400),
    "micro": (10, 14, 500),
}

# ---------- 间距（4px 网格） ----------
SPACE = {"xs": 4, "s": 8, "m": 12, "l": 16, "xl": 24, "xxl": 32, "xxxl": 48}

# ---------- 圆角 ----------
RADIUS = {"s": 4, "m": 8, "l": 12, "xl": 16}

# ---------- 尺寸 ----------
SIZE = {
    "nav_expanded": 260,
    "nav_collapsed": 48,
    "timeline_row": 72,
    "cell_min_h": 88,
}

# ---------- 浮层投影（仅命令面板/对话框/快捷添加窗） ----------
OVERLAY_SHADOW = {"blur": 32, "dy": 8, "alpha_light": 36, "alpha_dark": 128}


def course_color(name, mode):
    """课程 -> (底色, 文字色, 边条色)。hash 转 hue，S/L 锁死。

    浅色: 底 hsl(h,42%,91%) / 文字 hsl(h,38%,36%) / 条 hsl(h,38%,48%)
    深色: 底 hsl(h,24%,22%) / 文字 hsl(h,45%,74%) / 条 hsl(h,40%,58%)
    """
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    hue = int(digest[:4], 16) % 360
    if mode == "dark":
        bg = f"hsl({hue}, 24%, 22%)"
        fg = f"hsl({hue}, 45%, 74%)"
        bar = f"hsl({hue}, 40%, 58%)"
    else:
        bg = f"hsl({hue}, 42%, 91%)"
        fg = f"hsl({hue}, 38%, 36%)"
        bar = f"hsl({hue}, 38%, 48%)"
    return bg, fg, bar


def dim_course(color_tuple, mode):
    """非本周/停用：去饱和处理，返回同结构 (底, 文字, 条)。"""
    bg, fg, bar = color_tuple
    if mode == "dark":
        return ("#242428", NEUTRAL["dark"]["text3"], "#3a3a40")
    return ("#f2f2f4", NEUTRAL["light"]["text3"], "#d8d8dc")
