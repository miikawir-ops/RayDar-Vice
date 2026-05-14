import os, json, hashlib, re, requests, feedparser
from datetime import datetime, timezone, timedelta
from jinja2 import Template
from pathlib import Path
 
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
)
 
FEEDS = [
    "https://huggingface.co/blog/feed.xml",
    "https://bair.berkeley.edu/blog/feed.xml",
    "https://deepmind.google/blog/rss.xml",
    "https://openai.com/blog/rss.xml",
    "https://www.anthropic.com/rss.xml",
    "https://blogs.microsoft.com/ai/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://github.blog/category/ai-and-ml/feed/",
]
 
SEEN_FILE    = Path("seen_hashes.json")
HISTORY_FILE = Path("signal_history.json")
 
 
def load_seen():
    try:
        if SEEN_FILE.exists():
            data = SEEN_FILE.read_text().strip()
            if data:
                return set(json.loads(data))
    except Exception as e:
        print(f"seen_hashes load error: {e}")
    return set()
 
 
def save_seen(seen):
    try:
        SEEN_FILE.write_text(json.dumps(list(seen)[-600:]))
    except Exception as e:
        print(f"seen_hashes save error: {e}")
 
 
def load_history():
    try:
        if HISTORY_FILE.exists():
            data = HISTORY_FILE.read_text().strip()
            if data:
                return json.loads(data)
    except Exception as e:
        print(f"History load error: {e}")
    return []
 
 
def save_history(history):
    try:
        HISTORY_FILE.write_text(json.dumps(history[-14:], ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"History save error: {e}")
 
 
def fetch_feeds():
    items = []
    seen  = load_seen()
 
    # Reset seen hashes daily so fresh content always comes through
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    marker = f"__date__{today}"
    if marker not in seen:
        print("New day — resetting seen hashes for fresh fetch")
        seen = {marker}
 
    for url in FEEDS:
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "RayDarVice/2.0"})
            for entry in feed.entries[:10]:
                title   = entry.get("title", "").strip()
                link    = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", ""))[:800]
                if not title or not link:
                    continue
                h = hashlib.md5(link.encode()).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                items.append({
                    "title":   title,
                    "url":     link,
                    "summary": re.sub(r"<[^>]+>", "", summary).strip(),
                    "source":  feed.feed.get("title", url.split("/")[2])[:40],
                })
        except Exception as e:
            print(f"Feed error {url}: {e}")
 
    save_seen(seen)
    print(f"Fetched {len(items)} new items across {len(FEEDS)} feeds")
    return items
 
 
def check_paywall(url):
    try:
        r = requests.head(url, timeout=6, allow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0"})
        return r.status_code == 200
    except Exception:
        return True  # default to keeping if check fails
 
 
def call_gemini(prompt, max_tokens=2500):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": max_tokens},
    }
    r = requests.post(GEMINI_URL, json=payload, timeout=90)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
 
 
def safe_json(raw):
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"(\[.*\]|\{.*\})", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
    print(f"JSON parse failed. Raw:\n{raw[:500]}")
    return None
 
 
def classify_items(items):
    if not items:
        print("No items to classify — check RSS feeds")
        return []
 
    batch = json.dumps(
        [{"index": i, "title": it["title"], "snippet": it["summary"][:400]}
         for i, it in enumerate(items)],
        ensure_ascii=False,
    )
 
    prompt = f"""You are Raymond "Red" Vice — a sharp AI intelligence operator filing
from Nick's Pizza, Espoo. You brief a Finnish business executive every morning on the
AI valuechain. Write with calm confidence — you already knew this was going to happen.
 
The AI valuechain has five layers:
- CHIPS:  semiconductor hardware, GPU/TPU design, HBM memory, fab capacity, NVIDIA/AMD/Intel
- CLOUD:  hyperscaler infrastructure, data centres, compute pricing, AWS/Azure/GCP AI
- MODELS: foundation model releases, benchmark breakthroughs, training efficiency, safety
- TOOLS:  developer frameworks, APIs, MLOps, fine-tuning platforms, open-source tooling
- APPS:   enterprise deployments, vertical AI applications, notable product launches
 
TASK: From the items below, select the TOP 5 by combined novelty x business impact (1-10).
Score above 6 only if the item genuinely shifts competitive dynamics at some chain layer.
If fewer than 5 items qualify, return however many do — never pad with weak items.
 
For each selected item return EXACTLY this JSON structure:
{{"chain_layer":"CHIPS|CLOUD|MODELS|TOOLS|APPS","chain_tag":"chips|cloud|models|tools|apps","score":7,"title":"Sharp headline max 90 chars","summary":"What happened. Two sharp sentences.","so_what":"Chain impact for a business reader. Two confident sentences.","url":"original url from input","source":"publication name"}}
 
Respond ONLY with a valid JSON array. No markdown fences, no preamble, no explanation.
 
ITEMS:
{batch}
"""
 
    try:
        raw        = call_gemini(prompt)
        classified = safe_json(raw)
        if not classified or not isinstance(classified, list):
            print("Gemini returned invalid structure")
            return []
 
        for c in classified:
            original = next(
                (it for it in items
                 if it["title"][:35].lower() in c.get("title","").lower()
                 or c.get("title","")[:35].lower() in it["title"].lower()),
                None,
            )
            if original:
                c["url"]    = original["url"]
                c["source"] = original["source"]
            c["score"]     = max(1, min(10, int(c.get("score", 7))))
            c["chain_tag"] = c.get("chain_tag", "models").lower()
            if c["chain_tag"] not in ("chips","cloud","models","tools","apps"):
                c["chain_tag"] = "models"
 
        clean = [c for c in classified if check_paywall(c.get("url",""))]
        print(f"Classified: {len(classified)} items, {len(clean)} paywall-free")
        return clean[:5]
 
    except Exception as e:
        print(f"Classification error: {e}")
        return []
 
 
def build_also_watching(today_items, history):
    if not history:
        return []
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    yesterday_record = None
    for record in reversed(history):
        if record.get("date") != today_str:
            yesterday_record = record
            break
    if not yesterday_record:
        return []
    today_titles = {it.get("title","")[:40].lower() for it in today_items}
    watching = [
        it for it in yesterday_record.get("items",[])
        if it.get("score",0) >= 7
        and it.get("title","")[:40].lower() not in today_titles
    ]
    return watching[:3]
 
 
def build_weekly_synthesis(history):
    now = datetime.now(timezone.utc)
    if now.weekday() != 0:
        return None
    week_items = []
    for record in history[-7:]:
        week_items.extend(record.get("items",[]))
    if len(week_items) < 5:
        return None
    titles_and_layers = "\n".join(
        f"- [{it.get('chain_layer','?')}] {it.get('title','')}"
        for it in week_items
    )
    prompt = f"""You are Raymond "Red" Vice. It is Monday morning. Synthesise the past
week of AI valuechain signals into ONE sharp paragraph (4-6 sentences) for a Finnish
business executive. Identify the dominant theme, which chain layer saw the most
movement, and what it means going into the new week. Write with Reddington's calm
authority — no bullet points, no headers, just one powerful paragraph.
 
Last week's signals:
{titles_and_layers}
 
Respond with the paragraph only. No preamble."""
    try:
        synthesis = call_gemini(prompt, max_tokens=400).strip()
        print("Weekly synthesis generated")
        return synthesis
    except Exception as e:
        print(f"Weekly synthesis error: {e}")
        return None
 
 
def render_html(items, also_watching, weekly_synthesis):
    template_path = Path("templates/report.html")
    template_str  = template_path.read_text()
    tmpl = Template(template_str)
    now         = datetime.now(timezone.utc)
    report_date = now.strftime("%A, %B %d %Y · %H:%M UTC")
    html = tmpl.render(
        items            = items,
        also_watching    = also_watching,
        weekly_synthesis = weekly_synthesis,
        report_date      = report_date,
        item_count       = len(items),
        is_monday        = now.weekday() == 0,
    )
    out = Path("raydar_vice.html")
    out.write_text(html)
    print(f"Report written -> {out}  ({len(items)} signals, {len(also_watching)} watching)")
 
 
if __name__ == "__main__":
    history          = load_history()
    raw_items        = fetch_feeds()
    final_items      = classify_items(raw_items)
    also_watching    = build_also_watching(final_items, history)
    weekly_synthesis = build_weekly_synthesis(history)
 
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    history   = [r for r in history if r.get("date") != today_str]
    history.append({"date": today_str, "items": final_items})
    save_history(history)
 
    render_html(final_items, also_watching, weekly_synthesis)