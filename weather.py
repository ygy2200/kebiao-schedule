# -*- coding: utf-8 -*-
"""天气：高德开放平台 REST（境内直连快；Open-Meteo 等境外源在校园网实测超时不可用）。

- key 需用户在高德开放平台注册获取（Web服务类型），存 settings.amap_key
- 城市名 -> adcode 用高德地理编码 API（同一个 key），结果内存缓存
- 无 key / key 失效 / 网络失败一律静默返回 None，UI 显示 --，不影响其他功能
"""
import json
import time
import urllib.parse
import urllib.request

GEO_URL = "https://restapi.amap.com/v3/geocode/geo"
WX_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
TIMEOUT = 5
CACHE_TTL = 20 * 60

_cache = {"adcode": {}, "wx": None, "wx_ts": 0.0}


def _get(url, params):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{q}", headers={"User-Agent": "kebiao-reminder/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def geocode(city, key):
    """城市名 -> adcode 字符串，失败返回 None（带内存缓存）。"""
    city = (city or "").strip()
    if not city:
        return None
    if city in _cache["adcode"]:
        return _cache["adcode"][city]
    try:
        data = _get(GEO_URL, {"address": city, "key": key})
        geos = data.get("geocodes") or []
        if data.get("status") == "1" and geos:
            adcode = geos[0].get("adcode")
            if adcode:
                _cache["adcode"][city] = adcode
                return adcode
    except Exception:
        pass
    return None


def fetch(key, adcode):
    """实况天气 {"temp","text","wind"}，失败返回 None（缓存 20 分钟）。"""
    now = time.time()
    if _cache["wx"] and now - _cache["wx_ts"] < CACHE_TTL:
        return _cache["wx"]
    try:
        data = _get(WX_URL, {"city": adcode, "key": key, "extensions": "base"})
        lives = data.get("lives") or []
        if data.get("status") == "1" and lives:
            w = lives[0]
            out = {
                "temp": f"{w.get('temperature', '--')}°C",
                "text": w.get("weather", "--"),
                "wind": f"{w.get('winddirection', '')}{w.get('windpower', '')}级",
            }
            _cache["wx"], _cache["wx_ts"] = out, now
            return out
    except Exception:
        pass
    return None


def fetch_forecast(key, adcode, days=3):
    """3 日预报 [{"date","dayweather","daytemp","nighttemp"}...]，失败 None（缓存 30 分钟）。"""
    now = time.time()
    if _cache.get("fc") and now - _cache.get("fc_ts", 0) < CACHE_TTL * 1.5:
        return _cache["fc"]
    try:
        data = _get(WX_URL, {"city": adcode, "key": key, "extensions": "all"})
        fc = data.get("forecasts") or []
        casts = fc[0].get("casts") if fc else []
        out = [{"date": c.get("date", ""), "dayweather": c.get("dayweather", "--"),
                "daytemp": c.get("daytemp", "--"), "nighttemp": c.get("nighttemp", "--")}
               for c in casts[:days]]
        if out:
            _cache["fc"], _cache["fc_ts"] = out, now
        return out or None
    except Exception:
        return None
