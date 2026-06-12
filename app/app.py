from flask import Flask, abort
from html import escape
import json
from pathlib import Path

app = Flask(__name__)

CITIES = [
    {"id": "keelung", "name": "基隆市", "region": "北部"},
    {"id": "taipei", "name": "臺北市", "region": "北部"},
    {"id": "new-taipei", "name": "新北市", "region": "北部"},
    {"id": "taoyuan", "name": "桃園市", "region": "北部"},
    {"id": "hsinchu-city", "name": "新竹市", "region": "北部"},
    {"id": "hsinchu-county", "name": "新竹縣", "region": "北部"},
    {"id": "miaoli", "name": "苗栗縣", "region": "中部"},
    {"id": "taichung", "name": "臺中市", "region": "中部"},
    {"id": "changhua", "name": "彰化縣", "region": "中部"},
    {"id": "nantou", "name": "南投縣", "region": "中部"},
    {"id": "yunlin", "name": "雲林縣", "region": "中部"},
    {"id": "chiayi-city", "name": "嘉義市", "region": "南部"},
    {"id": "chiayi-county", "name": "嘉義縣", "region": "南部"},
    {"id": "tainan", "name": "臺南市", "region": "南部"},
    {"id": "kaohsiung", "name": "高雄市", "region": "南部"},
    {"id": "pingtung", "name": "屏東縣", "region": "南部"},
    {"id": "yilan", "name": "宜蘭縣", "region": "東部"},
    {"id": "hualien", "name": "花蓮縣", "region": "東部"},
    {"id": "taitung", "name": "臺東縣", "region": "東部"},
    {"id": "penghu", "name": "澎湖縣", "region": "離島"},
    {"id": "kinmen", "name": "金門縣", "region": "離島"},
    {"id": "lienchiang", "name": "連江縣", "region": "離島"},
]

CITY_MAP = {c["id"]: c for c in CITIES}

TICKER_FILE = Path("/data/ticker.json")

def load_ticker_events():
    try:
        if not TICKER_FILE.exists():
            return []
        data = json.loads(TICKER_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return data
    except Exception:
        return []

def render_ticker(city_name=None):
    events = load_ticker_events()

    if city_name:
        events = [
            e for e in events
            if e.get("city") in (city_name, "全台", "全國")
        ]

    if not events:
        return '<span>✅ 目前尚無人工新增災害狀態公告</span>'

    items = []
    for e in events:
        raw_level = str(e.get("level", "INFO"))
        level_map = {
            "L4": "緊急警報",
            "L3": "應變警戒",
            "L2": "注意提醒",
            "L1": "一般資訊",
            "INFO": "一般資訊"
        }
        level = escape(level_map.get(raw_level, raw_level))
        source = escape(str(e.get("source", "未知單位")))
        city = escape(str(e.get("city", "全台")))
        typ = escape(str(e.get("type", "災害資訊")))
        title = escape(str(e.get("title", "未命名公告")))
        url = escape(str(e.get("url", "#")))

        text = f"🚨【{source}｜{city}｜{typ}｜{level}】{title}｜點我查證"
        items.append(
            f'<a class="ticker-item" href="{url}" target="_blank" rel="noopener">{text}</a>'
        )

    return "".join(items)

GENERAL_LINKS = [
    {
        "title": "人事行政總處｜停班停課",
        "desc": "查詢各縣市停止上班、停止上課公告。",
        "url": "https://www.dgpa.gov.tw/typh/daily/nds.html"
    },
    {
        "title": "中央氣象署｜天氣警特報",
        "desc": "豪雨、大雨、颱風、低溫、高溫等警特報。",
        "url": "https://www.cwa.gov.tw/V8/C/P/Warning/W26.html"
    },
    {
        "title": "中央氣象署｜地震資訊",
        "desc": "地震報告、震度、震央與相關資訊。",
        "url": "https://scweb.cwa.gov.tw/"
    },
    {
        "title": "中央氣象署｜海嘯資訊",
        "desc": "海嘯消息、海嘯警報與解除資訊。",
        "url": "https://scweb.cwa.gov.tw/zh-tw/tsunami"
    },
    {
        "title": "消防署｜災害情報站",
        "desc": "全國災害應變與相關資訊入口。",
        "url": "https://www.emic.gov.tw/"
    },
]

CITY_LINKS = {
    "tainan": [
        {
            "title": "臺南市政府｜市府新聞",
            "desc": "臺南市政府最新新聞與災害應變公告。",
            "url": "https://www.tainan.gov.tw/News.aspx?n=13370&sms=9748"
        },
        {
            "title": "臺南市災害應變告示網",
            "desc": "臺南災害專區、警戒公告、停班停課、收容與工作會報。",
            "url": "https://disaster.tainan.gov.tw/"
        },
        {
            "title": "臺南水情即時通",
            "desc": "臺南市水情、雨量、抽水站與淹水資訊。",
            "url": "https://flood.tainan.gov.tw/"
        },
    ],
    "kaohsiung": [
        {
            "title": "高雄市政府全球資訊網",
            "desc": "高雄市政府最新公告與新聞。",
            "url": "https://www.kcg.gov.tw/"
        },
        {
            "title": "高雄市防災資訊網",
            "desc": "高雄市防災、災情與應變資訊。",
            "url": "https://dpr.kcg.gov.tw/"
        },
    ],
    "pingtung": [
        {
            "title": "屏東縣政府",
            "desc": "屏東縣政府最新公告與新聞。",
            "url": "https://www.pthg.gov.tw/"
        },
    ],
    "hualien": [
        {
            "title": "花蓮縣政府",
            "desc": "花蓮縣政府最新公告與新聞。",
            "url": "https://www.hl.gov.tw/"
        },
    ],
    "taitung": [
        {
            "title": "臺東縣政府",
            "desc": "臺東縣政府最新公告與新聞。",
            "url": "https://www.taitung.gov.tw/"
        },
    ],
}

def css():
    return """
<style>
    :root {
        --bg: #0b0f14;
        --panel: #151c26;
        --panel2: #101722;
        --text: #e8f0ff;
        --muted: #a7b3c7;
        --line: #263244;
        --accent: #60a5fa;
        --warn: #fbbf24;
        --danger: #fb7185;
        --ok: #6ee7b7;
    }
    * { box-sizing: border-box; }
    body {
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font-family: Arial, "Microsoft JhengHei", sans-serif;
    }
    header {
        padding: 30px 36px 18px;
        background: linear-gradient(135deg, #111827, #0f172a);
        border-bottom: 1px solid var(--line);
    }
    h1 { margin: 0 0 10px; font-size: 34px; }
    h2 { margin-top: 34px; }
    .subtitle { color: var(--muted); line-height: 1.7; }
    .ticker-wrap {
        overflow: hidden;
        white-space: nowrap;
        background: #111827;
        border-bottom: 1px solid var(--line);
    }
    .ticker {
        display: inline-block;
        padding: 13px 0;
        animation: marquee 35s linear infinite;
        font-weight: bold;
    }
    .ticker span {
        margin-right: 56px;
    }
    .ticker a.ticker-item {
        color: #e8f0ff;
        text-decoration: none;
        margin-right: 56px;
    }
    .ticker a.ticker-item:hover {
        color: #93c5fd;
        text-decoration: underline;
    }
    @keyframes marquee {
        0% { transform: translateX(100vw); }
        100% { transform: translateX(-100%); }
    }
    main {
        max-width: 1280px;
        margin: auto;
        padding: 28px 36px 60px;
    }
    .quick {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 14px;
        margin-top: 22px;
    }
    .card, .link-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 0 18px rgba(0,0,0,.2);
    }
    .link-card {
        display: block;
        color: var(--text);
        text-decoration: none;
        transition: transform .12s ease, border-color .12s ease;
    }
    .link-card:hover {
        transform: translateY(-2px);
        border-color: var(--accent);
    }
    .link-title {
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .desc {
        color: var(--muted);
        line-height: 1.6;
        font-size: 14px;
    }
    .cities {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
        gap: 14px;
    }
    .city {
        display: block;
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 16px;
        color: var(--text);
        text-decoration: none;
        transition: transform .12s ease, border-color .12s ease;
    }
    .city:hover {
        transform: translateY(-2px);
        border-color: var(--ok);
    }
    .city-name {
        font-size: 21px;
        font-weight: bold;
        margin-bottom: 6px;
    }
    .tag {
        display: inline-block;
        color: #cbd5e1;
        background: #1f2937;
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 13px;
    }
    .back {
        display: inline-block;
        margin-bottom: 20px;
        color: #93c5fd;
        text-decoration: none;
    }
    .notice {
        border-left: 6px solid var(--warn);
        background: var(--panel2);
        padding: 16px;
        border-radius: 14px;
        color: #fde68a;
        line-height: 1.7;
    }
    footer {
        color: var(--muted);
        border-top: 1px solid var(--line);
        padding: 20px 36px 36px;
        font-size: 13px;
        line-height: 1.7;
    }
</style>
"""

def page_shell(title, body):
    return f"""
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{css()}
</head>
<body>
{body}
<footer>
    本站為個人災害資訊入口站，主要功能是彙整官方連結與快速入口；實際災害判斷與停班停課仍以政府機關正式公告為準。
</footer>
</body>
</html>
"""

@app.route("/")
def index():
    general_html = ""
    for item in GENERAL_LINKS:
        general_html += f"""
        <a class="link-card" href="{escape(item["url"])}" target="_blank" rel="noopener">
            <div class="link-title">{escape(item["title"])}</div>
            <div class="desc">{escape(item["desc"])}</div>
        </a>
        """

    city_html = ""
    for city in CITIES:
        city_html += f"""
        <a class="city" href="/city/{escape(city["id"])}">
            <div class="city-name">{escape(city["name"])}</div>
            <span class="tag">{escape(city["region"])}</span>
        </a>
        """

    body = f"""
<header>
    <h1>臺灣災害資訊入口站</h1>
    <div class="subtitle">
        全台停班停課、豪雨、地震、海嘯、災害應變資訊快速入口。<br>
        目前版本：入口站模式，先提供官方資訊快速連結，後續再逐步加入自動監控與推播。
    </div>
</header>

<div class="ticker-wrap">
    <div class="ticker">
        {render_ticker()}
    </div>
</div>

<main>
    <div class="notice">
        這一版先做成「全台災害入口首頁」。點選縣市後，可快速進入該縣市相關災害資訊入口。
    </div>

    <h2>全國通用災害入口</h2>
    <div class="quick">
        {general_html}
    </div>

    <h2>縣市入口</h2>
    <div class="cities">
        {city_html}
    </div>
</main>
"""
    return page_shell("臺灣災害資訊入口站", body)

@app.route("/city/<city_id>")
def city_page(city_id):
    city = CITY_MAP.get(city_id)
    if not city:
        abort(404)

    links = []
    links.extend(CITY_LINKS.get(city_id, []))
    links.extend(GENERAL_LINKS)

    links_html = ""
    for item in links:
        links_html += f"""
        <a class="link-card" href="{escape(item["url"])}" target="_blank" rel="noopener">
            <div class="link-title">{escape(item["title"])}</div>
            <div class="desc">{escape(item["desc"])}</div>
        </a>
        """

    body = f"""
<header>
    <h1>{escape(city["name"])}災害資訊入口</h1>
    <div class="subtitle">
        區域：{escape(city["region"])}｜地方資訊＋全國通用災害入口
    </div>
</header>

<div class="ticker-wrap">
    <div class="ticker">
        {render_ticker(city["name"])}
    </div>
</div>

<main>
    <a class="back" href="/">← 回全台首頁</a>

    <div class="notice">
        這裡先提供 {escape(city["name"])} 常用災害資訊入口。若該縣市尚未建立專屬資料源，會先顯示全國通用官方入口。
    </div>

    <h2>{escape(city["name"])}相關連結</h2>
    <div class="quick">
        {links_html}
    </div>
</main>
"""
    return page_shell(f"{city['name']}災害資訊入口", body)

@app.route("/health")
def health():
    return {"status": "ok", "service": "taiwan-disaster-portal"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
