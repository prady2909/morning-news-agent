"""
build_page.py — Builds the daily morning-news webpage from the RSS feeds.

Pipeline:
  1. Reuse fetch.py's health logic: call fetch_one() on every feed in FEEDS and
     keep only the OK ones (same "is this feed healthy?" gate the CLI report uses).
  2. For each healthy feed, pull its latest entries (title, link, teaser, date).
  3. Merge all items and sort newest-first.
  4. Render a static, dependency-free HTML page:
       - each item shows title + source + topic flair + RSS teaser + link
       - topics are click-to-filter, Reddit-flair style (feed-level topic)
       - responsive layout (phone + laptop), light/dark aware
  5. Archive: write today's snapshot as docs/<YYYY-MM-DD>.html and (over)write
     docs/index.html with today's items plus a list of clickable past dates.

This is v1: NO AI summarization. It is deliberately title + teaser + link only.

Note on reuse: like summarize.py, we call fetch_one() for the health verdict and
then feedparser.parse() once more on healthy feeds to read their entries. That's
two fetches per feed, but it keeps fetch.py as the single source of "healthy".
"""

import html
import re
import sys
from datetime import datetime
from pathlib import Path

import feedparser

# Reuse the feed list + health logic already written in fetch.py.
from fetch import FEEDS, fetch_one, OK


# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).parent / "docs"   # dated pages + index.html live here
MAX_ITEMS_PER_FEED = 15                        # cap so one chatty feed can't dominate
TEASER_CHARS = 280                             # blurb length before we trim + ellipsis

# Topic → accent color for the flair pills. Anything not listed falls back to grey.
TOPIC_COLORS = {
    "PM":       "#2563eb",   # blue
    "GTM":      "#059669",   # green
    "AI":       "#7c3aed",   # purple
    "Startups": "#ea580c",   # orange
}
DEFAULT_COLOR = "#475569"

# Preferred left-to-right order for the filter chips; unknown topics get appended.
TOPIC_ORDER = ["PM", "GTM", "AI", "Startups"]


# ── Text helpers ────────────────────────────────────────────────────────────────

def strip_html(text: str) -> str:
    """Drop tags and collapse whitespace so feed HTML becomes clean prose."""
    no_tags = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", no_tags).strip()


def make_teaser(text: str, limit: int = TEASER_CHARS) -> str:
    """Clean + trim a blurb to `limit` chars, cutting on a word boundary."""
    text = strip_html(text)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip() + "…"


def entry_teaser(entry) -> str:
    """Best available blurb for an entry: summary, else first content block."""
    if entry.get("summary"):
        return make_teaser(entry["summary"])
    if entry.get("content"):
        return make_teaser(entry["content"][0].get("value", ""))
    return ""


def entry_datetime(entry):
    """Return a datetime for sorting/display, or None if the feed gave no date."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6])   # treat feed time as naive UTC — fine for sort
            except (TypeError, ValueError):
                pass
    return None


def human_date(d: datetime) -> str:
    """Format like '4 Jul' (no leading zero, cross-platform)."""
    return f"{d.day} {d.strftime('%b')}"


# ── Collection ──────────────────────────────────────────────────────────────────

def collect_items() -> list:
    """
    Walk FEEDS, keep only feeds fetch_one() calls OK, and gather their entries.
    Returns a list of item dicts sorted newest-first.
    """
    items = []
    total = len(FEEDS)

    for i, feed_info in enumerate(FEEDS, start=1):
        name = feed_info["name"]
        health = fetch_one(feed_info)

        if health["status"] != OK:
            print(f"[{i:>2}/{total}] skip  {name}  ({health['status']})")
            continue

        parsed = feedparser.parse(feed_info["url"])
        count = 0
        for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
            items.append({
                "title":   entry.get("title", "(no title)"),
                "link":    entry.get("link", ""),
                "teaser":  entry_teaser(entry),
                "source":  name,
                "topic":   feed_info["topic"],
                "dt":      entry_datetime(entry),
            })
            count += 1
        print(f"[{i:>2}/{total}] OK    {name}  ({count} items)")

    # Newest first; undated items sink to the bottom.
    items.sort(key=lambda it: it["dt"] or datetime.min, reverse=True)
    return items


def topics_present(items: list) -> list:
    """Ordered list of the topics that actually appear in today's items."""
    seen = {it["topic"] for it in items}
    ordered = [t for t in TOPIC_ORDER if t in seen]
    ordered += sorted(t for t in seen if t not in TOPIC_ORDER)
    return ordered


# ── Rendering ───────────────────────────────────────────────────────────────────

def esc(text: str) -> str:
    return html.escape(text or "")


def color_for(topic: str) -> str:
    return TOPIC_COLORS.get(topic, DEFAULT_COLOR)


def render_chip(topic: str) -> str:
    return (f'<button class="chip" data-filter="{esc(topic)}" '
            f'style="--c:{color_for(topic)}">{esc(topic)}</button>')


def render_item(item: dict) -> str:
    topic = item["topic"]
    date_str = human_date(item["dt"]) if item["dt"] else ""
    date_html = f'<span class="date">{esc(date_str)}</span>' if date_str else ""
    teaser_html = f'<p class="teaser">{esc(item["teaser"])}</p>' if item["teaser"] else ""
    link = esc(item["link"])
    title = esc(item["title"])

    return f"""      <article class="item" data-topic="{esc(topic)}">
        <div class="meta">
          <button class="flair" data-filter="{esc(topic)}" style="--c:{color_for(topic)}">{esc(topic)}</button>
          <span class="source">{esc(item["source"])}</span>
          {date_html}
        </div>
        <h2 class="title"><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h2>
        {teaser_html}
      </article>"""


def render_archive(archive_dates: list) -> str:
    """archive_dates: list of 'YYYY-MM-DD' strings, newest first."""
    if not archive_dates:
        return '<p class="dates muted">No past editions yet.</p>'
    links = []
    for ds in archive_dates:
        d = datetime.strptime(ds, "%Y-%m-%d")
        links.append(f'<a href="{ds}.html">{esc(human_date(d))}</a>')
    return '<p class="dates">' + ", ".join(links) + "</p>"


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Morning News — {date_label}</title>
  <style>
    :root {{
      --bg:#f8fafc; --card:#ffffff; --text:#0f172a; --muted:#64748b;
      --border:#e2e8f0; --chip-bg:#ffffff;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg:#0f172a; --card:#1e293b; --text:#e2e8f0; --muted:#94a3b8;
        --border:#334155; --chip-bg:#1e293b;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin:0; background:var(--bg); color:var(--text); line-height:1.55;
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
      -webkit-text-size-adjust:100%;
    }}
    .wrap {{ max-width:760px; margin:0 auto; padding:24px 16px 72px; }}
    header {{ margin-bottom:16px; }}
    header .top {{ display:flex; align-items:baseline; justify-content:space-between; gap:12px; flex-wrap:wrap; }}
    h1 {{ font-size:1.7rem; margin:0; letter-spacing:-0.02em; }}
    .subtitle {{ color:var(--muted); font-size:.95rem; margin:4px 0 0; }}
    #count {{ color:var(--muted); font-size:.85rem; white-space:nowrap; }}
    .backlink {{ display:inline-block; margin-bottom:12px; color:var(--muted); text-decoration:none; font-size:.9rem; }}
    .backlink:hover {{ color:var(--text); }}

    .filters {{
      position:sticky; top:0; z-index:10; display:flex; flex-wrap:wrap; gap:8px;
      padding:12px 0; margin-bottom:8px; background:var(--bg);
      border-bottom:1px solid var(--border);
    }}
    .chip {{
      font:inherit; font-size:.85rem; font-weight:600; cursor:pointer;
      padding:5px 12px; border-radius:999px; background:var(--chip-bg);
      border:1.5px solid var(--border); color:var(--text); transition:all .12s ease;
    }}
    .chip[data-filter="all"] {{ --c:var(--text); }}
    .chip:hover {{ border-color:var(--c); }}
    .chip.active {{ background:var(--c); border-color:var(--c); color:#fff; }}

    .item {{
      background:var(--card); border:1px solid var(--border); border-radius:12px;
      padding:16px 18px; margin-bottom:14px;
    }}
    .meta {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:8px; }}
    .flair {{
      font:inherit; font-size:.72rem; font-weight:700; letter-spacing:.03em;
      text-transform:uppercase; cursor:pointer; padding:2px 9px; border-radius:999px;
      background:transparent; color:var(--c); border:1.5px solid var(--c);
    }}
    .flair:hover {{ background:var(--c); color:#fff; }}
    .source {{ font-size:.85rem; font-weight:600; color:var(--muted); }}
    .date {{ font-size:.8rem; color:var(--muted); margin-left:auto; }}
    .title {{ font-size:1.1rem; margin:0 0 6px; line-height:1.35; }}
    .title a {{ color:var(--text); text-decoration:none; }}
    .title a:hover {{ text-decoration:underline; }}
    .teaser {{ margin:0; color:var(--muted); font-size:.95rem; }}

    footer.archive {{ margin-top:36px; padding-top:20px; border-top:1px solid var(--border); }}
    footer.archive h2 {{ font-size:1rem; margin:0 0 8px; }}
    .dates a {{ color:var(--muted); text-decoration:none; }}
    .dates a:hover {{ color:var(--text); text-decoration:underline; }}
    .muted {{ color:var(--muted); }}

    @media (max-width:480px) {{
      h1 {{ font-size:1.4rem; }}
      .wrap {{ padding:16px 12px 56px; }}
      .item {{ padding:14px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
{backlink}    <header>
      <div class="top">
        <h1>Morning News</h1>
        <span id="count"></span>
      </div>
      <p class="subtitle">{date_label} · {item_count} items from {source_count} sources</p>
    </header>

    <nav class="filters" aria-label="Filter by topic">
      <button class="chip active" data-filter="all">All</button>
{chips}
    </nav>

    <main id="items">
{items}
    </main>

    <footer class="archive">
      <h2>Archive</h2>
{archive}
    </footer>
  </div>

  <script>
    (function () {{
      var countEl = document.getElementById('count');
      function apply(topic) {{
        document.querySelectorAll('.item').forEach(function (el) {{
          el.hidden = !(topic === 'all' || el.dataset.topic === topic);
        }});
        document.querySelectorAll('.chip').forEach(function (c) {{
          c.classList.toggle('active', c.dataset.filter === topic);
        }});
        var n = document.querySelectorAll('.item:not([hidden])').length;
        if (countEl) countEl.textContent = n + (n === 1 ? ' item' : ' items');
      }}
      document.querySelectorAll('[data-filter]').forEach(function (btn) {{
        btn.addEventListener('click', function () {{ apply(btn.dataset.filter); }});
      }});
      apply('all');
    }})();
  </script>
</body>
</html>
"""


def render_page(items: list, date_label: str, archive_dates: list, is_index: bool) -> str:
    chips = "\n".join("      " + render_chip(t) for t in topics_present(items))
    items_html = "\n".join(render_item(it) for it in items)
    source_count = len({it["source"] for it in items})
    backlink = "" if is_index else '    <a class="backlink" href="index.html">← Latest</a>\n'

    return PAGE_TEMPLATE.format(
        date_label=esc(date_label),
        item_count=len(items),
        source_count=source_count,
        chips=chips,
        items=items_html,
        archive=render_archive(archive_dates),
        backlink=backlink,
    )


# ── Archive discovery ───────────────────────────────────────────────────────────

DATE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")


def find_archive_dates(exclude: str) -> list:
    """Return existing dated pages (YYYY-MM-DD strings), newest first, minus `exclude`."""
    dates = []
    for path in OUTPUT_DIR.glob("*.html"):
        m = DATE_FILE_RE.match(path.name)
        if m and m.group(1) != exclude:
            dates.append(m.group(1))
    return sorted(dates, reverse=True)


# ── Entry point ─────────────────────────────────────────────────────────────────

def main() -> None:
    # Feed titles/teasers can carry emoji & non-Latin text; Windows' cp1252 console
    # would crash on them. Force UTF-8 output (same guard summarize.py uses).
    sys.stdout.reconfigure(encoding="utf-8")

    OUTPUT_DIR.mkdir(exist_ok=True)

    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    date_label = today.strftime("%A, ") + human_date(today) + today.strftime(" %Y")

    print(f"Building page for {today_str} — collecting items from healthy feeds...\n")
    items = collect_items()
    if not items:
        sys.exit("No items collected — every feed was empty or dead.")

    print(f"\nCollected {len(items)} items from {len({it['source'] for it in items})} sources.")

    # Past editions (everything already on disk except today's snapshot).
    archive_dates = find_archive_dates(exclude=today_str)

    dated_path = OUTPUT_DIR / f"{today_str}.html"
    index_path = OUTPUT_DIR / "index.html"

    dated_path.write_text(
        render_page(items, date_label, archive_dates, is_index=False), encoding="utf-8"
    )
    index_path.write_text(
        render_page(items, date_label, archive_dates, is_index=True), encoding="utf-8"
    )

    print(f"\nWrote:\n  {index_path}\n  {dated_path}")
    if archive_dates:
        print(f"Archive now lists {len(archive_dates)} past edition(s).")


if __name__ == "__main__":
    main()
