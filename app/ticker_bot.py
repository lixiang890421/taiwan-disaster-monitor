import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

DATA_FILE = "/data/ticker.json"
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "180"))

TW_TZ = timezone(timedelta(hours=8))

CITIES = [
    "基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣",
    "苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣",
    "嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣",
    "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"
]

CWA_WARNING_PAGE = "https://www.cwa.gov.tw/V8/C/P/Warning/W26.html"
CWA_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0033-001"

SOURCES = [
    {
        "name": "人事行政總處",
        "type": "停班停課",
        "url": "https://www.dgpa.gov.tw/typh/daily/nds.html"
    },
    {
        "name": "中央氣象署",
        "type": "天氣警特報API",
        "url": CWA_API_URL
    },
    {
        "name": "中央氣象署",
        "type": "海嘯資訊",
        "url": "https://scweb.cwa.gov.tw/zh-tw/tsunami"
    },
    {
        "name": "臺南市政府",
        "type": "災害應變",
        "url": "https://disaster.tainan.gov.tw/"
    },
    {
        "name": "臺南市政府",
        "type": "市府新聞",
        "url": "https://www.tainan.gov.tw/News.aspx?n=13370&sms=9748"
    }
]

def now_tw():
    return datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")

def fetch_text(url):
    headers = {
        "User-Agent": "Mozilla/5.0 TaiwanDisasterTickerBot/0.2"
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    soup = BeautifulSoup(r.text, "html.parser")
    return soup.get_text(" ", strip=True)

def near_text(text, keyword, window=260):
    idx = text.find(keyword)
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(keyword) + window)
    return text[start:end]

def flatten_strings(obj):
    values = []
    if isinstance(obj, dict):
        for v in obj.values():
            values.extend(flatten_strings(v))
    elif isinstance(obj, list):
        for item in obj:
            values.extend(flatten_strings(item))
    elif isinstance(obj, str):
        values.append(obj)
    else:
        if obj is not None:
            values.append(str(obj))
    return values

def first_value(obj, keys):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and v:
                return str(v)
            found = first_value(v, keys)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = first_value(item, keys)
            if found:
                return found
    return ""

def weather_level(phenomena, significance, all_text):
    text = f"{phenomena} {significance} {all_text}"

    if "超大豪雨" in text:
        return "L4", "超大豪雨"
    if "大豪雨" in text:
        return "L3", "大豪雨"
    if "豪雨" in text:
        return "L2", "豪雨"
    if "大雨" in text:
        return "L1", "大雨"

    if "颱風" in text and "警報" in text:
        return "L4", "颱風警報"
    if "颱風" in text:
        return "L3", "颱風資訊"

    if "低溫" in text:
        return "L1", "低溫"
    if "高溫" in text:
        return "L1", "高溫"
    if "強風" in text:
        return "L1", "強風"
    if "濃霧" in text:
        return "L1", "濃霧"

    return "L1", phenomena or "天氣警特報"

def add_event(events, level, source, city, typ, title, url, extra=None):
    item = {
        "level": level,
        "source": source,
        "city": city,
        "type": typ,
        "title": title,
        "url": url,
        "updated_at": now_tw()
    }

    if extra:
        item.update(extra)

    key = f"{level}|{source}|{city}|{typ}|{title}|{url}"
    if key not in {e.get("_key") for e in events}:
        item["_key"] = key
        events.append(item)

def check_dgpa(text, source, events):
    if "無停班停課訊息" in text:
        return

    for city in CITIES:
        if city not in text:
            continue

        seg = near_text(text, city, 360)

        if "停止上班" in seg and "停止上課" in seg:
            add_event(
                events,
                "L4",
                source["name"],
                city,
                "停班停課",
                f"{city} 停止上班停止上課",
                source["url"]
            )
        elif "停止上班" in seg or "停止上課" in seg:
            add_event(
                events,
                "L3",
                source["name"],
                city,
                "停班停課",
                f"{city} 停班停課資訊有異動，請查證公告",
                source["url"]
            )

def check_cwa_weather_api(events):
    key = os.getenv("CWA_API_KEY")

    if not key:
        add_event(
            events,
            "L1",
            "系統",
            "全台",
            "資料源異常",
            "中央氣象署 API 授權碼未設定，無法更新天氣警特報",
            CWA_WARNING_PAGE
        )
        return

    r = requests.get(
        CWA_API_URL,
        params={
            "Authorization": key,
            "format": "JSON"
        },
        timeout=20
    )
    r.raise_for_status()
    data = r.json()

    locations = data.get("records", {}).get("location", [])

    for loc in locations:
        city = loc.get("locationName", "")
        if city not in CITIES:
            continue

        hazards = (
            loc.get("hazardConditions", {})
               .get("hazards", [])
        )

        if not hazards:
            continue

        for hazard in hazards:
            all_text = " ".join(flatten_strings(hazard))

            phenomena = first_value(hazard, ["phenomena"]) or ""
            significance = first_value(hazard, ["significance"]) or ""
            start_time = first_value(hazard, ["startTime"]) or ""
            end_time = first_value(hazard, ["endTime"]) or ""

            level, event_type = weather_level(phenomena, significance, all_text)

            display_name = ""
            if phenomena and significance:
                display_name = f"{phenomena}{significance}"
            elif phenomena:
                display_name = phenomena
            else:
                display_name = event_type

            title = f"{city} 目前發布{display_name}"

            add_event(
                events,
                level,
                "中央氣象署",
                city,
                event_type,
                title,
                CWA_WARNING_PAGE,
                {
                    "start_time": start_time,
                    "end_time": end_time
                }
            )

def check_cwa_tsunami(text, source, events):
    strong_words = [
        "海嘯警報發布",
        "發布海嘯警報",
        "海嘯警戒區",
        "紅色海嘯警報",
        "橙色海嘯警報"
    ]

    if any(w in text for w in strong_words):
        add_event(
            events,
            "L4",
            source["name"],
            "全台",
            "海嘯資訊",
            "中央氣象署海嘯資訊頁面命中海嘯警報相關文字，請立即查證警戒區",
            source["url"]
        )

def check_tainan(text, source, events):
    city = "臺南市"
    head = text[:5000]

    if "一級開設" in head or "提升為一級" in head:
        add_event(events, "L4", source["name"], city, "應變中心", "臺南市災害應變中心命中一級開設相關文字", source["url"])

    if "二級開設" in head or "二級一階" in head or "二級第一階段" in head:
        add_event(events, "L3", source["name"], city, "應變中心", "臺南市災害應變中心命中二級開設相關文字", source["url"])

    if "水利局" in head and "三級開設" in head:
        add_event(events, "L2", source["name"], city, "水情應變", "臺南市水利局命中三級開設相關文字", source["url"])

    if "停班停課" in head or ("停止上班" in head and "停止上課" in head):
        add_event(events, "L4", source["name"], city, "停班停課", "臺南市命中停班停課相關文字，請查證公告", source["url"])

    if "預防性撤離" in head:
        add_event(events, "L3", source["name"], city, "撤離收容", "臺南市命中預防性撤離相關文字", source["url"])

    if "收容所" in head or "收容安置" in head:
        add_event(events, "L3", source["name"], city, "撤離收容", "臺南市命中收容安置相關文字", source["url"])

def build_events():
    events = []

    for source in SOURCES:
        try:
            if source["type"] == "天氣警特報API":
                check_cwa_weather_api(events)
                continue

            text = fetch_text(source["url"])

            if source["type"] == "停班停課":
                check_dgpa(text, source, events)

            elif source["type"] == "海嘯資訊":
                check_cwa_tsunami(text, source, events)

            elif source["name"] == "臺南市政府":
                check_tainan(text, source, events)

        except Exception as e:
            add_event(
                events,
                "L1",
                source["name"],
                "系統",
                "資料源異常",
                f"{source['name']}｜{source['type']} 抓取失敗：{e}",
                source.get("url", "#")
            )

    rank = {"L4": 4, "L3": 3, "L2": 2, "L1": 1}
    cleaned = []

    for e in events:
        e.pop("_key", None)
        cleaned.append(e)

    cleaned.sort(key=lambda x: rank.get(x.get("level", "L1"), 0), reverse=True)
    return cleaned[:30]

def write_events(events):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def main():
    while True:
        events = build_events()
        write_events(events)

        print(f"[{now_tw()}] wrote {len(events)} ticker events", flush=True)
        for e in events[:10]:
            print(f" - {e.get('level')} {e.get('source')} {e.get('city')} {e.get('type')} {e.get('title')}", flush=True)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
