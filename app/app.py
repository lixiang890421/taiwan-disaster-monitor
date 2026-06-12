from flask import Flask, jsonify
from datetime import datetime, timezone, timedelta
from html import escape
import threading
import time
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

TW_TZ = timezone(timedelta(hours=8))
CHECK_INTERVAL = 180

CITIES = [
    "基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣",
    "苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣",
    "嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣",
    "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"
]

SOURCES = [
    {
        "name": "人事行政總處停班停課",
        "url": "https://www.dgpa.gov.tw/typh/daily/nds.html",
        "type": "closure",
        "scope": "all"
    },
    {
        "name": "中央氣象署海嘯資訊",
        "url": "https://scweb.cwa.gov.tw/zh-tw/tsunami",
        "type": "tsunami",
        "scope": "all"
    },
    {
        "name": "臺南市政府新聞",
        "url": "https://www.tainan.gov.tw/News.aspx?n=13370&sms=9748",
        "type": "local_gov",
        "scope": "臺南市"
    },
    {
        "name": "臺南災害應變告示網",
        "url": "https://disaster.tainan.gov.tw/News.aspx?n=45045&sms=27080",
        "type": "local_gov",
        "scope": "臺南市"
    }
]

state = {
    "updated_at": None,
    "ticker": [],
    "cities": {},
    "events": [],
    "sources": []
}

def now_tw():
    return datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")

def fetch_text(url):
    headers = {
        "User-Agent": "Mozilla/5.0 TaiwanDisasterMonitor/0.1"
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    soup = BeautifulSoup(r.text, "html.parser")
    return soup.get_text(" ", strip=True)

def new_event(level, event_type, city, title, message, source, url):
    return {
        "id": f"{level}-{event_type}-{city}-{title}-{source}",
        "time": now_tw(),
        "level": level,
        "type": event_type,
        "city": city,
        "title": title,
        "message": message,
        "source": source,
        "url": url
    }

def analyze_closure(text, source):
    events = []

    for city in CITIES:
        if city in text and "停止上班" in text and "停止上課" in text:
            events.append(new_event(
                4,
                "停班停課",
                city,
                f"{city} 停止上班停止上課",
                f"{city} 命中停班停課關鍵字。",
                source["name"],
                source["url"]
            ))

    return events

def analyze_tsunami(text, source):
    events = []

    # 這裡先保守處理，避免氣象署頁面上的「警戒分級說明」被誤判成真的海嘯警報。
    # 下一階段會改接中央氣象署 OpenData 海嘯資料，精準判斷警戒區。
    strong_words = ["海嘯警報發布", "發布海嘯警報", "海嘯警戒區"]
    if any(word in text for word in strong_words):
        events.append(new_event(
            4,
            "海嘯",
            "全台",
            "海嘯警報可能發布",
            "中央氣象署海嘯頁面命中警報關鍵字，需人工確認警戒區。",
            source["name"],
            source["url"]
        ))

    return events

def analyze_local_gov(text, source):
    events = []
    city = source["scope"]

    if "一級開設" in text or "提升為一級" in text:
        events.append(new_event(
            4,
            "應變中心",
            city,
            f"{city} 災害應變中心一級開設",
            "命中一級開設關鍵字。",
            source["name"],
            source["url"]
        ))

    if "二級開設" in text or "二級一階" in text or "二級第一階段" in text:
        events.append(new_event(
            3,
            "應變中心",
            city,
            f"{city} 災害應變中心二級開設",
            "命中二級開設關鍵字。",
            source["name"],
            source["url"]
        ))

    if "水利局" in text and "三級開設" in text:
        events.append(new_event(
            2,
            "應變中心",
            city,
            f"{city} 水利局三級開設",
            "命中水利局三級開設關鍵字。",
            source["name"],
            source["url"]
        ))

    if "預防性撤離" in text:
        events.append(new_event(
            3,
            "撤離收容",
            city,
            f"{city} 預防性撤離訊息",
            "命中預防性撤離關鍵字。",
            source["name"],
            source["url"]
        ))

    if "收容所" in text or "收容安置" in text:
        events.append(new_event(
            3,
            "撤離收容",
            city,
            f"{city} 收容安置訊息",
            "命中收容所或收容安置關鍵字。",
            source["name"],
            source["url"]
        ))

    if "大豪雨" in text or "超大豪雨" in text:
        events.append(new_event(
            3,
            "豪雨",
            city,
            f"{city} 大豪雨相關訊息",
            "命中大豪雨或超大豪雨關鍵字。",
            source["name"],
            source["url"]
        ))
    elif "豪雨" in text:
        events.append(new_event(
            2,
            "豪雨",
            city,
            f"{city} 豪雨相關訊息",
            "命中豪雨關鍵字。",
            source["name"],
            source["url"]
        ))

    return events

def analyze_source(text, source):
    if source["type"] == "closure":
        return analyze_closure(text, source)
    if source["type"] == "tsunami":
        return analyze_tsunami(text, source)
    if source["type"] == "local_gov":
        return analyze_local_gov(text, source)
    return []

def empty_city_status(city):
    return {
        "city": city,
        "level": 0,
        "summary": "正常",
        "closure": "無",
        "weather": "無",
        "earthquake": "無",
        "tsunami": "無",
        "response_center": "無",
        "last_event": ""
    }

def apply_event_to_city(city_status, event):
    city_status["level"] = max(city_status["level"], event["level"])
    city_status["last_event"] = event["title"]

    if event["type"] == "停班停課":
        city_status["closure"] = "停止上班停止上課"
    elif event["type"] == "豪雨":
        city_status["weather"] = event["title"]
    elif event["type"] == "海嘯":
        city_status["tsunami"] = event["title"]
    elif event["type"] == "地震":
        city_status["earthquake"] = event["title"]
    elif event["type"] == "應變中心":
        city_status["response_center"] = event["title"]
    elif event["type"] == "撤離收容":
        city_status["response_center"] = event["title"]

    level = city_status["level"]
    if level >= 4:
        city_status["summary"] = "L4 強制警報"
    elif level == 3:
        city_status["summary"] = "L3 應變注意"
    elif level == 2:
        city_status["summary"] = "L2 資訊提醒"
    elif level == 1:
        city_status["summary"] = "L1 一般資訊"
    else:
        city_status["summary"] = "正常"

def build_city_status(events):
    cities = {city: empty_city_status(city) for city in CITIES}

    for event in events:
        if event["city"] == "全台":
            for city in CITIES:
                apply_event_to_city(cities[city], event)
        elif event["city"] in cities:
            apply_event_to_city(cities[event["city"]], event)

    return cities

def monitor_loop():
    global state

    while True:
        events = []
        source_status = []

        for source in SOURCES:
            try:
                text = fetch_text(source["url"])
                hits = analyze_source(text, source)
                events.extend(hits)

                source_status.append({
                    "name": source["name"],
                    "url": source["url"],
                    "ok": True,
                    "last_check": now_tw(),
                    "hits": len(hits),
                    "error": ""
                })

            except Exception as e:
                source_status.append({
                    "name": source["name"],
                    "url": source["url"],
                    "ok": False,
                    "last_check": now_tw(),
                    "hits": 0,
                    "error": str(e)
                })

        # 去重
        unique = {}
        for event in events:
            unique[event["id"]] = event
        events = sorted(unique.values(), key=lambda x: x["level"], reverse=True)

        ticker = [e for e in events if e["level"] >= 3]
        cities = build_city_status(events)

        state = {
            "updated_at": now_tw(),
            "ticker": ticker,
            "cities": cities,
            "events": events,
            "sources": source_status
        }

        time.sleep(CHECK_INTERVAL)

@app.route("/api/status")
def api_status():
    return jsonify(state)

@app.route("/")
def index():
    city_options = '<option value="全台">全台</option>'
    for city in CITIES:
        city_options += f'<option value="{escape(city)}">{escape(city)}</option>'

    return f"""
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>臺灣災害監控系統</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
    body {{
        margin: 0;
        background: #0b0f14;
        color: #e8f0ff;
        font-family: Arial, "Microsoft JhengHei", sans-serif;
    }}
    header {{
        padding: 28px 36px 16px;
        background: linear-gradient(135deg, #111827, #0f172a);
        border-bottom: 1px solid #263244;
    }}
    h1 {{
        margin: 0 0 8px;
        font-size: 32px;
    }}
    .subtitle {{
        color: #a7b3c7;
    }}
    .ticker-wrap {{
        background: #111827;
        border-top: 1px solid #263244;
        border-bottom: 1px solid #263244;
        overflow: hidden;
        white-space: nowrap;
    }}
    .ticker {{
        display: inline-block;
        padding: 14px 0;
        animation: marquee 35s linear infinite;
    }}
    .ticker span {{
        margin-right: 48px;
        font-weight: bold;
    }}
    @keyframes marquee {{
        0% {{ transform: translateX(100vw); }}
        100% {{ transform: translateX(-100%); }}
    }}
    .layout {{
        padding: 28px 36px;
        max-width: 1280px;
        margin: auto;
    }}
    .toolbar {{
        display: flex;
        gap: 12px;
        align-items: center;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }}
    select {{
        background: #151c26;
        color: #e8f0ff;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 16px;
    }}
    .updated {{
        color: #9ca3af;
    }}
    .cards {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
        gap: 16px;
    }}
    .card {{
        background: #151c26;
        border: 1px solid #263244;
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 0 18px rgba(0,0,0,.25);
    }}
    .city-title {{
        font-size: 22px;
        font-weight: bold;
        margin-bottom: 8px;
    }}
    .level {{
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-weight: bold;
        margin-bottom: 12px;
    }}
    .l0 {{ background: #1f2937; color: #d1d5db; }}
    .l1 {{ background: #334155; color: #e5e7eb; }}
    .l2 {{ background: #1e3a8a; color: #bfdbfe; }}
    .l3 {{ background: #78350f; color: #fde68a; }}
    .l4 {{ background: #7f1d1d; color: #fecaca; }}
    .row {{
        color: #cbd5e1;
        margin: 6px 0;
        font-size: 14px;
        line-height: 1.5;
    }}
    .section {{
        margin-top: 28px;
    }}
    .event {{
        background: #151c26;
        border: 1px solid #263244;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 10px;
        line-height: 1.7;
    }}
    .event a {{
        color: #93c5fd;
        text-decoration: none;
    }}
    .source-table {{
        width: 100%;
        border-collapse: collapse;
        background: #151c26;
        border-radius: 14px;
        overflow: hidden;
    }}
    .source-table th, .source-table td {{
        border-bottom: 1px solid #263244;
        padding: 10px;
        text-align: left;
        font-size: 14px;
    }}
    .muted {{
        color: #9ca3af;
    }}
    .error {{
        color: #fb7185;
    }}
</style>
</head>
<body>
<header>
    <h1>臺灣災害監控系統</h1>
    <div class="subtitle">全台重大災害總覽｜停班停課｜豪雨｜地震｜海嘯｜應變中心</div>
</header>

<div class="ticker-wrap">
    <div class="ticker" id="ticker">系統載入中...</div>
</div>

<div class="layout">
    <div class="toolbar">
        <label>縣市：</label>
        <select id="citySelect">
            {city_options}
        </select>
        <span class="updated" id="updatedAt">最後更新：讀取中...</span>
    </div>

    <div class="cards" id="cards"></div>

    <div class="section">
        <h2>最新事件</h2>
        <div id="events"></div>
    </div>

    <div class="section">
        <h2>資料源狀態</h2>
        <table class="source-table" id="sources"></table>
    </div>
</div>

<script>
let currentData = null;

function levelClass(level) {{
    if (level >= 4) return "l4";
    if (level === 3) return "l3";
    if (level === 2) return "l2";
    if (level === 1) return "l1";
    return "l0";
}}

function renderTicker(data, selectedCity) {{
    const ticker = document.getElementById("ticker");
    let items = data.ticker || [];

    if (selectedCity !== "全台") {{
        items = items.filter(e => e.city === selectedCity || e.city === "全台");
    }}

    if (!items.length) {{
        ticker.innerHTML = "<span>✅ 目前未偵測到 L3 以上重大警示</span>";
        return;
    }}

    ticker.innerHTML = items.map(e => 
        `<span>🚨 [L${{e.level}} ${{e.type}}] ${{e.city}}｜${{e.title}}</span>`
    ).join("");
}}

function renderCards(data, selectedCity) {{
    const cards = document.getElementById("cards");
    const cities = data.cities || {{}};

    let entries = Object.entries(cities);
    if (selectedCity !== "全台") {{
        entries = entries.filter(([city]) => city === selectedCity);
    }}

    cards.innerHTML = entries.map(([city, s]) => `
        <div class="card">
            <div class="city-title">${{city}}</div>
            <div class="level ${{levelClass(s.level)}}">${{s.summary}}</div>
            <div class="row">停班停課：${{s.closure}}</div>
            <div class="row">豪雨：${{s.weather}}</div>
            <div class="row">地震：${{s.earthquake}}</div>
            <div class="row">海嘯：${{s.tsunami}}</div>
            <div class="row">應變中心：${{s.response_center}}</div>
            <div class="row muted">最近事件：${{s.last_event || "無"}}</div>
        </div>
    `).join("");
}}

function renderEvents(data, selectedCity) {{
    const box = document.getElementById("events");
    let events = data.events || [];

    if (selectedCity !== "全台") {{
        events = events.filter(e => e.city === selectedCity || e.city === "全台");
    }}

    if (!events.length) {{
        box.innerHTML = `<div class="muted">目前沒有事件。</div>`;
        return;
    }}

    box.innerHTML = events.map(e => `
        <div class="event">
            <b class="${{levelClass(e.level)}}">L${{e.level}}｜${{e.type}}｜${{e.city}}</b><br>
            ${{e.title}}<br>
            <span class="muted">${{e.time}}｜${{e.source}}</span><br>
            <a href="${{e.url}}" target="_blank">查看來源</a>
        </div>
    `).join("");
}}

function renderSources(data) {{
    const table = document.getElementById("sources");
    const sources = data.sources || [];

    table.innerHTML = `
        <tr>
            <th>狀態</th>
            <th>來源</th>
            <th>最後檢查</th>
            <th>命中數</th>
            <th>錯誤</th>
        </tr>
        ${{sources.map(s => `
            <tr>
                <td>${{s.ok ? "✅" : "❌"}}</td>
                <td>${{s.name}}</td>
                <td>${{s.last_check}}</td>
                <td>${{s.hits}}</td>
                <td class="error">${{s.error || ""}}</td>
            </tr>
        `).join("")}}
    `;
}}

function render() {{
    if (!currentData) return;
    const selectedCity = document.getElementById("citySelect").value;

    document.getElementById("updatedAt").innerText =
        "最後更新：" + (currentData.updated_at || "尚未完成第一次檢查");

    renderTicker(currentData, selectedCity);
    renderCards(currentData, selectedCity);
    renderEvents(currentData, selectedCity);
    renderSources(currentData);
}}

async function loadStatus() {{
    try {{
        const res = await fetch("/api/status");
        currentData = await res.json();
        render();
    }} catch (e) {{
        document.getElementById("ticker").innerHTML = "<span>❌ 無法讀取後端狀態</span>";
    }}
}}

document.getElementById("citySelect").addEventListener("change", render);

loadStatus();
setInterval(loadStatus, 60000);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    threading.Thread(target=monitor_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
