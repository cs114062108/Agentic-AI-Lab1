from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Map Chinese place names to English query strings to avoid inconsistencies in how geocoding services interpret different Chinese spellings.
CITY_ALIASES = {
    "新竹": "Hsinchu", "新竹市": "Hsinchu",
    "新北": "New Taipei",
    "台北": "Taipei", "臺北": "Taipei", "台北市": "Taipei",
    "台中": "Taichung", "臺中": "Taichung",
    "台南": "Tainan", "臺南": "Tainan",
    "高雄": "Kaohsiung", "桃園": "Taoyuan",
    "基隆": "Keelung", "嘉義": "Chiayi", "花蓮": "Hualien",
}

WEATHER_CODES = {
    0: "晴朗", 1: "大致晴朗", 2: "局部多雲", 3: "陰天",
    45: "有霧", 48: "霧凇",
    51: "小毛毛雨", 53: "毛毛雨", 55: "強毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "小陣雨", 81: "中陣雨", 82: "強陣雨",
    95: "雷雨", 96: "雷雨伴小冰雹", 99: "雷雨伴大冰雹",
}

def _get_json(url: str, params: dict) -> dict:
    """Send a GET request using the standard library; configure a timeout and validate the data type of the response."""
    full_url = url + "?" + urlencode(params)
    request = Request(full_url, headers={"User-Agent": "BIIC-Classroom-API-Tutorial/1.0"})
    with urlopen(request, timeout=12) as response:
        data = json.load(response)
    if not isinstance(data, dict):
        raise ValueError("Unexpected JSON format")
    return data

def get_city_current_weather(city: str) -> str:
    """Retrieve current weather data from Open-Meteo (not hard-coded sample data)."""
    city = city.strip()
    if not city or len(city) > 80:
        return "Weather API error: invalid city name"

    search_name = CITY_ALIASES.get(city, city)
    try:
        geo = _get_json(
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": search_name, "count": 5, "language": "en", "format": "json"},
        )
        candidates = geo.get("results") or []
        if not candidates:
            return f"Weather API: 找不到城市「{city} ({search_name})」"

        # For Taiwanese city names, prioritize matches from Taiwan to avoid selecting cities with the same name in other countries.
        place = next(
            (p for p in candidates if p.get("country_code") == "TW"),
            candidates[0],
        ) if city in CITY_ALIASES else candidates[0]

        weather = _get_json(
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
        )
        current = weather.get("current") or {}
        if not current or "temperature_2m" not in current:
            return "Weather API error: missing current weather values"

        report = {
            "source": "Open-Meteo (real weather API)",
            "location": ", ".join(
                str(x) for x in [place.get("name"), place.get("country")] if x
            ),
            "time": current.get("time"),
            "timezone": weather.get("timezone"),
            "temperature_c": current.get("temperature_2m"),
            "relative_humidity_percent": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "condition": WEATHER_CODES.get(current.get("weather_code"), "未知天氣狀況"),
        }
        return json.dumps(report, ensure_ascii=False)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, OSError) as exc:
        return f"Weather API unavailable: {type(exc).__name__}: {str(exc)[:120]}"


if __name__ == "__main__":
    cities = ["新竹", "台北", "新北"]
    for city in cities:
        weather_result = get_city_current_weather(city)
        print(city, "天氣 API 結果：")
        print(weather_result)
        print()

