import os, json, hashlib, re, requests, feedparser
from datetime import datetime, timezone
from jinja2 import Template
from pathlib import Path
 
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
)
 
# ── RSS SOURCES ──────────────────────────────────────────────────────────────
FEEDS = [
    # Research / breakthroughs
    "https://huggingface.co/blog/feed.xml",
    "https://bair.berkeley.edu/blog/feed.xml",
    "https://deepmind.google/blog/rss.xml",
    # Company news
    "https://openai.com/blog/rss.xml",
    "https://www.anthropic.com/rss.xml",
    "https://blogs.microsoft.com/ai/feed/",
    # Business-focused AI media
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    # Developer / tools
    "https://github.blog/category/ai-and-ml/feed/",
]
 
CHAIN_LAYERS = {
    "chips":  "CHIPS",
    "cloud":  "CLOUD",
    "models": "MODELS",
    "tools":  "TOOLS",
    "apps":   "APPS",
}
 
SEEN_FILE = Path("seen_hashes.json")
 
 
def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()
 
 
def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(list(seen)[-500:]))
 
 
def fetch_feeds():
    items = []
    seen = load_seen()
    for url in FEEDS:
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "MiamiAIVice/1.0"})
            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()
                link  = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", ""))[:600]
                if not title or not link:
                    continue
                h = hashlib.md5(link.encode()).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                items.append({
                    "title": title,
                    "url": link,
                    "summary": re.sub(r"<[^>]+>", "", summary).strip(),
                    "source": feed.feed.get("title", url.split("/")[2])[:40],
                })
        except Exception as e:
            print(f"Feed error {url}: {e}")
    save_seen(seen)
    print(f"Fetched {len(items)} new items")
    return items
 
 
def check_paywall(url: str) -> bool:
    try:
        r = requests.head(url, timeout=5, allow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0"})
        return r.status_code == 200
    except Exception:
        return False
 
 
def classify_items(items: list) -> list:
    if not items:
        return []
 
    batch = json.dumps([
        {"index": i, "title": it["title"], "snippet": it["summary"][:300]}
        for i, it in enumerate(items)
    ], ensure_ascii=False)
 
    prompt = f"""You are Raymond "Red" Vice — a sharp AI intelligence analyst operating out of Nick's Pizza, Espoo, briefing a Finnish business executive
every morning. Your job: identify the 5 most important AI valuechain stories from this batch.
 
The AI valuechain has five layers:
- CHIPS: semiconductor hardware, GPU/TPU design, HBM memory, fab capacity
- CLOUD: hyperscaler infrastructure, data centres, compute pricing, AWS/Azure/GCP AI
- MODELS: foundation model releases, benchmark breakthroughs, training efficiency, safety
- TOOLS: developer frameworks, APIs, MLOps, fine-tuning platforms, open-source tooling
- APPS: enterprise deployments, vertical AI applications, notable product launches
 
SCORING: Rate each item 1-10 on combined novelty × business impact. Only items that
genuinely shift competitive dynamics at some layer of the chain score above 6.
Discard hype, funding rounds under $50M, opinion pieces, and recycled summaries.
 
For each of the TOP 5 items write:
- chain_layer: one of CHIPS / CLOUD / MODELS / TOOLS / APPS
- chain_tag: lowercase version (chips/cloud/models/tools/apps)
- score: integer 1-10
- title: punchy headline (keep original or sharpen it, max 90 chars)
- summary: what happened, 2 sharp sentences, no filler
- so_what: chain impact for a business/strategy reader, 2 sentences, confident tone
- url: original link
- source: publication name
 
Respond ONLY with a valid JSON array of exactly 5 objects. No markdown, no preamble.
 
ITEMS:
{batch}
"""
 
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000},
    }
 
    try:
        r = requests.post(GEMINI_URL, json=payload, timeout=60)
        r.raise_for_status()
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        raw = re.sub(r"```json|```", "", raw).strip()
        classified = json.loads(raw)
 
        # Merge original URLs back in
        for c in classified:
            idx = next(
                (i for i, it in enumerate(items)
                 if it["title"][:40] in c.get("title", "") or
                    c.get("title", "")[:40] in it["title"]),
                None,
            )
            if idx is not None and not c.get("url"):
                c["url"] = items[idx]["url"]
            if not c.get("source"):
                c["source"] = items[idx]["source"] if idx is not None else "—"
            c["score"] = int(c.get("score", 7))
            c["chain_tag"] = c.get("chain_tag", "models").lower()
 
        # Filter paywall items
        clean = [c for c in classified if check_paywall(c.get("url", ""))]
        print(f"Classified {len(clean)} items (paywall-free)")
        return clean[:5]
 
    except Exception as e:
        print(f"Gemini error: {e}")
        return []
 
 
def render_html(items: list):
    template_path = Path("templates/report.html")
    template_str = template_path.read_text()
    tmpl = Template(template_str)
 
    now = datetime.now(timezone.utc)
    report_date = now.strftime("%A, %B %d %Y · %H:%M UTC")
 
    html = tmpl.render(
        items=items,
        report_date=report_date,
        item_count=len(items),
    )
 
    out = Path("raydar_vice.html")
    out.write_text(html)
    print(f"Report written → {out}")
 
 
if __name__ == "__main__":
    raw_items   = fetch_feeds()
    final_items = classify_items(raw_items)
    render_html(final_items)
