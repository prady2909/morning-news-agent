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
     docs/index.html with today's items plus a right-rail calendar whose past
     days link to their snapshots.

This is v1: NO AI summarization. It is deliberately title + teaser + link only.

Note on reuse: like summarize.py, we call fetch_one() for the health verdict and
then feedparser.parse() once more on healthy feeds to read their entries. That's
two fetches per feed, but it keeps fetch.py as the single source of "healthy".
"""

import calendar
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import feedparser

# Reuse the feed list + health logic already written in fetch.py.
from fetch import FEEDS, fetch_one, OK

# v3 Phase 1: AI summaries. Low-level Gemini pieces (prompt, client, model, the
# call itself) are lifted verbatim from summarize.py into summaries.py; the
# orchestration + graceful fallback below lives here.
import summaries

# v3 Phase 2: versioned summary cache. A hit reuses a prior successful summary and
# skips the Gemini call entirely. Only CI writes the cache file (see main()).
from cache import load_cache, get_cached, set_cached, save_cache


# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).parent / "docs"   # dated pages + index.html live here
MAX_ITEMS_PER_FEED = 15                        # DEFAULT cap; a feed may override via its "max_items" key
TEASER_CHARS = 280                             # blurb length before we trim + ellipsis
MIN_TEASER_CHARS = 40                          # drop teasers shorter than this after promo strip
RECENCY_DAYS = 15                              # LIVE front page only: hide items older than this many days
SUMMARIES_PER_SECTION = 4                      # v3 Phase 1: top N most-recent ARTICLE items per topic get an AI summary (LIVE only)

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
    """Drop tags, decode HTML entities, then collapse whitespace so feed HTML
    becomes clean prose. Entities (&amp;, &#127897;) are decoded HERE so the
    single html.escape() at render time encodes them once instead of doubling
    them into visible '&amp;' / '&#127897;' junk."""
    no_tags = re.sub(r"<[^>]+>", " ", text or "")
    decoded = html.unescape(no_tags)
    return re.sub(r"\s+", " ", decoded).strip()


def strip_promo_tail(text: str) -> str:
    """Cut YouTube-style promo junk (newsletter/course plugs, channel links) that
    trails the real description. Truncate at the earliest of 'http', 👉, or 🔗 —
    the real content always comes first — and tidy the cut point. No marker → text
    unchanged."""
    positions = [text.find(m) for m in ("http", "👉", "🔗")]
    positions = [p for p in positions if p != -1]
    if not positions:
        return text
    return text[:min(positions)].rstrip().rstrip(".,;:-–—•|/ ")


def make_teaser(text: str, limit: int = TEASER_CHARS) -> str:
    """Clean + trim a blurb to `limit` chars, cutting on a word boundary.
    Strip promo tails first; if what's left is too short to be useful, drop it."""
    text = strip_promo_tail(strip_html(text))
    if len(text) < MIN_TEASER_CHARS:
        return ""
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
        cap = feed_info.get("max_items", MAX_ITEMS_PER_FEED)   # per-feed override, else default
        count = 0
        for entry in parsed.entries[:cap]:
            items.append({
                "title":   entry.get("title", "(no title)"),
                "link":    entry.get("link", ""),
                "teaser":  entry_teaser(entry),
                "source":  name,
                "topic":   feed_info["topic"],
                "type":    feed_info["type"],   # "article" | "video" — drives the format filter
                "dt":      entry_datetime(entry),
                # Raw body kept ONLY for articles — feeds the summarizer later.
                # Videos never get summarized, so they don't need it.
                "source_text": (summaries.entry_source_text(entry)
                                if feed_info["type"] == "article" else ""),
                "summary": "",   # filled in by add_summaries() for LIVE index only
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


def filter_recent(items: list, today: datetime) -> list:
    """Keep only items published within RECENCY_DAYS of `today`. Items with NO
    parseable date are KEPT — we drop only what we can positively confirm is
    stale. This is for the LIVE front page (docs/index.html) exclusively; dated
    snapshots stay unfiltered so those frozen historical records keep their
    original, legitimately-old items. If this empties a topic, that's intended —
    we never backfill with older items to avoid an empty section."""
    cutoff = today - timedelta(days=RECENCY_DAYS)
    return [it for it in items if it["dt"] is None or it["dt"] >= cutoff]


# ── AI summaries (v3 Phase 1) ─────────────────────────────────────────────────────

def add_summaries(items: list, client, cache: dict) -> None:
    """Attach a Gemini summary (item["summary"]) to the top SUMMARIES_PER_SECTION
    most-recent ARTICLE items in each topic section — in place.

    Callers pass the LIVE, recency-filtered list; snapshots are rendered with
    is_index=False so the summary text never reaches them. `items` is assumed
    newest-first (collect_items sorts it), so section[:N] is the most-recent N.

    `cache` is the versioned summary cache loaded once per build. Before calling
    Gemini for an item we check the cache (keyed on the normalized URL + current
    MODEL + PROMPT_VERSION); a hit reuses that summary with NO API call and NO
    rate-limit sleep. Only a genuinely successful fresh summary is written back to
    the cache — throttled/thin/errored items stay uncached so they retry next build.

    Every failure mode degrades to today's teaser-only card and can NEVER break
    the build or make a card worse:
      - no client (missing GEMINI_API_KEY)  -> skip all
      - body thinner than MIN_SOURCE_CHARS  -> skip-too-thin (no API call)
      - empty model response                -> skip-too-thin
      - any API / quota / network error     -> skip-error
    One line is logged per attempted item so the outcome is visible in the build.
    """
    if client is None:
        print("\n[summaries] no GEMINI_API_KEY / client unavailable — "
              "skipping all summaries; cards fall back to teasers.")
        return

    print(f"\nSummarizing top {SUMMARIES_PER_SECTION} recent article(s) per section "
          f"with {summaries.MODEL} (LIVE index only)...")

    start = datetime.now()
    done = thin = errored = calls = hits = 0

    for topic in TOPIC_ORDER:
        section = [it for it in items
                   if it["topic"] == topic and it["type"] == "article"]

        for it in section[:SUMMARIES_PER_SECTION]:
            title = it["title"]
            label = title if len(title) <= 60 else title[:59] + "…"
            src = it.get("source_text", "")
            url = it.get("link", "")

            # Cache first: a hit reuses a prior successful summary — no API call,
            # no rate-limit sleep. Keyed on normalized URL + this MODEL + PROMPT_VERSION,
            # so a model or prompt change turns hits into misses automatically.
            cached = get_cached(cache, url, summaries.MODEL, summaries.PROMPT_VERSION)
            if cached is not None:
                it["summary"] = cached
                hits += 1
                print(f"  [{topic:>8}] cache HIT         : {label}")
                print(f"[cache] HIT {url}")
                continue

            # Too thin to be worth summarizing — keep the teaser, skip the call.
            if len(src) < summaries.MIN_SOURCE_CHARS:
                thin += 1
                print(f"  [{topic:>8}] skipped-too-thin : {label}")
                continue

            # Space calls out to stay under free-tier RPM (no leading wait).
            if calls > 0:
                time.sleep(summaries.SLEEP_SECONDS)
            calls += 1

            try:
                summary = summaries.summarize_item(client, title, src)
            except Exception as e:   # never let one call crash the build
                errored += 1
                print(f"  [{topic:>8}] skipped-error    : {label}  ({e})")
                continue

            if not summary:
                thin += 1
                print(f"  [{topic:>8}] skipped-too-thin : {label}  (empty response)")
                continue

            it["summary"] = summary
            # Cache ONLY this success — never the thin/error/empty fallback paths
            # above — so a throttled or failed item stays uncached and retries.
            set_cached(cache, url, summary, summaries.MODEL, summaries.PROMPT_VERSION)
            done += 1
            print(f"  [{topic:>8}] summarized       : {label}")
            print(f"[cache] MISS->stored {url}")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n[summaries] {done} summarized · {hits} cache-hit · {thin} skipped-too-thin · "
          f"{errored} skipped-error · {calls} API call(s) · {elapsed:.1f}s")


# ── Rendering ───────────────────────────────────────────────────────────────────

def esc(text: str) -> str:
    return html.escape(text or "")


def color_for(topic: str) -> str:
    return TOPIC_COLORS.get(topic, DEFAULT_COLOR)


def render_chip(topic: str) -> str:
    return (f'<button class="chip" data-filter="{esc(topic)}" '
            f'style="--c:{color_for(topic)}">{esc(topic)}</button>')


def render_item(item: dict, is_index: bool = False) -> str:
    topic = item["topic"]
    item_type = item["type"]
    date_str = human_date(item["dt"]) if item["dt"] else ""
    date_html = f'<span class="date">{esc(date_str)}</span>' if date_str else ""
    link = esc(item["link"])
    title = esc(item["title"])

    # Body blurb: on the LIVE index an AI summary (when we got one) REPLACES the
    # teaser — one blurb per card, no redundant double-summary. Everywhere else,
    # and whenever summarizing was skipped/failed, the card is exactly today's:
    # the RSS teaser. Snapshots (is_index=False) never show summaries even though
    # the item dict may carry one, so they stay raw v1.
    summary = item.get("summary") if is_index else ""
    if summary:
        body_html = (f'<p class="summary"><span class="summary-tag">Summary</span>'
                     f'{esc(summary)}</p>')
    elif item["teaser"]:
        body_html = f'<p class="teaser">{esc(item["teaser"])}</p>'
    else:
        body_html = ""

    return f"""      <article class="item" data-topic="{esc(topic)}" data-type="{esc(item_type)}">
        <div class="meta">
          <button class="flair" data-filter="{esc(topic)}" style="--c:{color_for(topic)}">{esc(topic)}</button>
          <span class="source">{esc(item["source"])}</span>
          {date_html}
        </div>
        <h2 class="title"><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h2>
        {body_html}
      </article>"""


# Sunday-first weekday headers for the archive calendar.
CAL_WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"]


def render_month_grid(year: int, month: int, today: datetime, snapshot_dates: set) -> str:
    """Inner HTML for one month's `.cal-grid` (weekday header + day cells). A day
    links to its snapshot ONLY if docs/<date>.html exists AND the date is strictly
    before today; every other day — missing snapshot, today, or future — is dimmed
    and inert. Clickability is derived purely from `snapshot_dates`, so
    deleting/adding a snapshot flips a day automatically on the next build. The
    same logic renders every month, so navigating months stays consistent."""
    cal = calendar.Calendar(firstweekday=6)   # 6 = Sunday, so weeks start on Sunday
    today_tuple = (today.year, today.month, today.day)

    head = "".join(f'<span class="cal-dow">{d}</span>' for d in CAL_WEEKDAYS)
    cells = []
    for week in cal.monthdayscalendar(year, month):
        for day in week:
            if day == 0:                                  # padding for days in adjacent months
                cells.append('<span class="cal-day cal-empty"></span>')
                continue
            ds = f"{year:04d}-{month:02d}-{day:02d}"
            this_tuple = (year, month, day)
            is_today = this_tuple == today_tuple
            is_future = this_tuple > today_tuple
            # Today/future are never clickable: today's content is on the front page
            # and only joins the archive tomorrow, once its snapshot is frozen.
            clickable = ds in snapshot_dates and not is_today and not is_future
            if clickable:
                cells.append(f'<a class="cal-day cal-on" href="{ds}.html">{day}</a>')
            else:
                extra = " cal-today" if is_today else ""
                cells.append(f'<span class="cal-day cal-off{extra}">{day}</span>')

    return head + "".join(cells)


def earliest_month(snapshot_dates: set, today: datetime) -> tuple:
    """Month (year, month) of the oldest snapshot on disk — the back-arrow floor.
    Falls back to `today`'s month when there are no snapshots yet."""
    if not snapshot_dates:
        return today.year, today.month
    y, m, _ = min(snapshot_dates).split("-")   # 'YYYY-MM-DD' sorts chronologically
    return int(y), int(m)


def render_calendar(today: datetime, snapshot_dates: set) -> str:
    """Archive calendar for the rail: the current month on load, with a back arrow
    that pages to earlier months entirely client-side. Every month from the
    earliest-data month through the current month is pre-rendered here (same grid
    logic as the initial view) and emitted as JSON, so the arrow can swap months
    without a rebuild. There is NO forward arrow — the current month is the newest
    viewable — and the back arrow is disabled once the earliest-data month shows."""
    cy, cm = today.year, today.month
    ey, em = earliest_month(snapshot_dates, today)

    # Build every month from earliest → current (chronological), pre-rendering each grid.
    months, order = {}, []
    y, m = ey, em
    while (y, m) <= (cy, cm):
        key = f"{y:04d}-{m:02d}"
        order.append(key)
        months[key] = {
            "title": datetime(y, m, 1).strftime("%B %Y"),
            "grid": render_month_grid(y, m, today, snapshot_dates),
        }
        m += 1
        if m > 12:
            m, y = 1, y + 1

    current_key = f"{cy:04d}-{cm:02d}"
    earliest_key = f"{ey:04d}-{em:02d}"
    at_floor = current_key == earliest_key
    disabled_attr = " disabled" if at_floor else ""

    return (
        '          <div class="cal-nav">\n'
        f'            <button type="button" class="cal-back" id="cal-back"'
        f' aria-label="Previous month"{disabled_attr}>&lsaquo;</button>\n'
        f'            <div class="cal-title" id="cal-title">{esc(months[current_key]["title"])}</div>\n'
        '          </div>\n'
        f'          <div class="cal-grid" id="cal-grid">{months[current_key]["grid"]}</div>\n'
        '          <script>\n'
        '            (function () {\n'
        f'              var MONTHS = {json.dumps(months)};\n'
        f'              var ORDER = {json.dumps(order)};\n'
        f'              var EARLIEST = {json.dumps(earliest_key)};\n'
        f'              var current = {json.dumps(current_key)};\n'
        '              var backEl = document.getElementById("cal-back");\n'
        '              var titleEl = document.getElementById("cal-title");\n'
        '              var gridEl = document.getElementById("cal-grid");\n'
        '              function render() {\n'
        '                var data = MONTHS[current];\n'
        '                titleEl.textContent = data.title;\n'
        '                gridEl.innerHTML = data.grid;\n'
        '                backEl.disabled = (current === EARLIEST);\n'
        '              }\n'
        '              backEl.addEventListener("click", function () {\n'
        '                var i = ORDER.indexOf(current);\n'
        '                if (i > 0) { current = ORDER[i - 1]; render(); }\n'
        '              });\n'
        '              render();\n'
        '            })();\n'
        '          </script>'
    )


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
    .wrap {{ max-width:1400px; margin:0 auto; padding:24px 32px 72px; }}
    header {{ margin-bottom:16px; }}
    header .top {{ display:flex; align-items:baseline; justify-content:space-between; gap:12px; flex-wrap:wrap; }}
    h1 {{ font-size:1.7rem; margin:0; letter-spacing:-0.02em; }}
    .subtitle {{ color:var(--muted); font-size:.95rem; margin:4px 0 0; }}
    #count {{ color:var(--muted); font-size:.85rem; white-space:nowrap; }}
    .backlink {{ display:inline-block; margin-bottom:12px; color:var(--muted); text-decoration:none; font-size:.9rem; }}
    .backlink:hover {{ color:var(--text); }}

    .filters {{
      position:sticky; top:0; z-index:10; display:flex; flex-direction:column; gap:8px;
      padding:12px 0; margin-bottom:8px; background:var(--bg);
      border-bottom:1px solid var(--border);
    }}
    .filter-row {{ display:flex; flex-wrap:wrap; gap:8px; }}
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
    /* AI summary (LIVE only): slightly more prominent than a teaser (full text
       colour), prefixed by a small tag so it reads as our summary, not the feed's. */
    .summary {{ margin:0; color:var(--text); font-size:.95rem; }}
    .summary-tag {{
      display:inline-block; font-size:.62rem; font-weight:700; letter-spacing:.05em;
      text-transform:uppercase; color:var(--muted);
      border:1px solid var(--border); border-radius:4px;
      padding:1px 6px; margin-right:8px; vertical-align:middle;
    }}

    /* Two-column layout: article content on the left, archive rail on the right. */
    .layout {{ display:grid; grid-template-columns:minmax(0,700px) 300px; gap:32px; justify-content:space-between; align-items:start; }}
    .content {{ min-width:0; }}   /* let the left column shrink instead of overflowing the grid */
    .rail-box {{
      background:var(--card); border:1px solid var(--border); border-radius:12px;
      padding:16px 18px; position:sticky; top:12px;
    }}
    .rail-box h2 {{ font-size:1rem; margin:0 0 8px; }}

    /* Archive calendar: month grid inside the rail, with client-side month paging. */
    .cal-nav {{ display:flex; align-items:center; gap:8px; margin:0 0 8px; }}
    .cal-title {{ font-size:.9rem; font-weight:600; margin:0; }}
    .cal-back {{
      font:inherit; font-size:1rem; line-height:1; cursor:pointer;
      background:var(--chip-bg); color:var(--text); border:1px solid var(--border);
      border-radius:6px; padding:1px 9px;
    }}
    .cal-back:hover:not(:disabled) {{ border-color:var(--text); }}
    .cal-back:disabled {{ opacity:.35; cursor:default; }}
    .cal-grid {{ display:grid; grid-template-columns:repeat(7,1fr); gap:2px; text-align:center; }}
    .cal-dow {{ font-size:.7rem; font-weight:700; color:var(--muted); padding:4px 0; }}
    .cal-day {{
      display:flex; align-items:center; justify-content:center;
      aspect-ratio:1; font-size:.8rem; border-radius:6px;
    }}
    .cal-off {{ color:var(--muted); opacity:.45; }}            /* no snapshot / future / today: inert */
    .cal-today {{ outline:1.5px solid var(--border); outline-offset:-1.5px; opacity:.7; }}
    .cal-on {{                                                 /* has a snapshot: clickable */
      color:var(--text); font-weight:600; text-decoration:none;
      background:var(--chip-bg); border:1px solid var(--border); cursor:pointer;
    }}
    .cal-on:hover {{ border-color:var(--text); }}

    /* Narrow screens: drop the rail below the content instead of beside it. */
    @media (max-width:860px) {{
      .layout {{ grid-template-columns:1fr; }}
      .rail-box {{ position:static; }}
    }}

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

    <div class="layout">
      <div class="content">
        <nav class="filters" aria-label="Filter items">
          <div class="filter-row" aria-label="Filter by topic">
            <button class="chip active" data-filter="all">All</button>
{chips}
          </div>
          <div class="filter-row" aria-label="Filter by format">
            <button class="chip active" data-format="all">All</button>
            <button class="chip" data-format="article" style="--c:var(--text)">Articles</button>
            <button class="chip" data-format="video" style="--c:var(--text)">Videos</button>
          </div>
        </nav>

        <main id="items">
{items}
        </main>
      </div>

      <aside class="rail" aria-label="Archive">
        <div class="rail-box">
          <h2>Archive</h2>
{calendar}
        </div>
      </aside>
    </div>
  </div>

  <script>
    (function () {{
      var countEl = document.getElementById('count');
      var activeTopic = 'all';    // topic-chip / flair selection
      var activeFormat = 'all';   // format-chip selection (article | video)
      function apply() {{
        document.querySelectorAll('.item').forEach(function (el) {{
          var topicOk = activeTopic === 'all' || el.dataset.topic === activeTopic;
          var formatOk = activeFormat === 'all' || el.dataset.type === activeFormat;
          el.hidden = !(topicOk && formatOk);   // visible only if it matches BOTH axes
        }});
        document.querySelectorAll('.chip[data-filter]').forEach(function (c) {{
          c.classList.toggle('active', c.dataset.filter === activeTopic);
        }});
        document.querySelectorAll('.chip[data-format]').forEach(function (c) {{
          c.classList.toggle('active', c.dataset.format === activeFormat);
        }});
        var n = document.querySelectorAll('.item:not([hidden])').length;
        if (countEl) countEl.textContent = n + (n === 1 ? ' item' : ' items');
      }}
      document.querySelectorAll('[data-filter]').forEach(function (btn) {{
        btn.addEventListener('click', function () {{ activeTopic = btn.dataset.filter; apply(); }});
      }});
      document.querySelectorAll('[data-format]').forEach(function (btn) {{
        btn.addEventListener('click', function () {{ activeFormat = btn.dataset.format; apply(); }});
      }});
      apply();
    }})();
  </script>
</body>
</html>
"""


def render_page(items: list, date_label: str, is_index: bool,
                today: datetime, snapshot_dates: set) -> str:
    chips = "\n".join("      " + render_chip(t) for t in topics_present(items))
    items_html = "\n".join(render_item(it, is_index) for it in items)
    source_count = len({it["source"] for it in items})
    backlink = "" if is_index else '    <a class="backlink" href="index.html">← Latest</a>\n'

    return PAGE_TEMPLATE.format(
        date_label=esc(date_label),
        item_count=len(items),
        source_count=source_count,
        chips=chips,
        items=items_html,
        calendar=render_calendar(today, snapshot_dates),
        backlink=backlink,
    )


# ── Archive discovery ───────────────────────────────────────────────────────────

DATE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")


def find_snapshot_dates() -> set:
    """Every dated snapshot present in docs/ as a set of 'YYYY-MM-DD' strings.
    The calendar uses this to decide which days are clickable — no exclusions,
    since today is gated out in render_calendar itself."""
    return {
        m.group(1)
        for path in OUTPUT_DIR.glob("*.html")
        if (m := DATE_FILE_RE.match(path.name))
    }


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

    # Full snapshot set for the calendar's clickability check (today gated out later).
    snapshot_dates = find_snapshot_dates()

    dated_path = OUTPUT_DIR / f"{today_str}.html"
    index_path = OUTPUT_DIR / "index.html"

    # Today's frozen snapshot keeps the full item set; the live front page hides
    # anything we can positively date as older than RECENCY_DAYS. Past snapshots
    # on disk are never re-rendered here, so they stay untouched.
    recent_items = filter_recent(items, today)

    # v3 Phase 2: load the versioned summary cache ONCE before any section is
    # summarized (never per-article). Threaded into add_summaries as an argument.
    cache = load_cache()

    # v3 Phase 1: attach AI summaries to the top recent articles per section.
    # Operates on the LIVE list only; the snapshot render below uses is_index=False
    # so summaries never appear in the dated file. Degrades to teasers on any error.
    add_summaries(recent_items, summaries.make_client(), cache)

    dated_path.write_text(
        render_page(items, date_label, is_index=False,
                    today=today, snapshot_dates=snapshot_dates),
        encoding="utf-8",
    )
    index_path.write_text(
        render_page(recent_items, date_label, is_index=True,
                    today=today, snapshot_dates=snapshot_dates),
        encoding="utf-8",
    )

    print(f"\nWrote:\n  {index_path} ({len(recent_items)} items)"
          f"\n  {dated_path} ({len(items)} items)")

    # Write-guard: only CI (the scheduler) persists the cache. GITHUB_ACTIONS is
    # set to "true" on GitHub's runners and is absent locally, so local builds READ
    # the cache (fast, no wasted quota) but never WRITE it — summary_cache.json
    # never shows up in a local git status, and the scheduler stays its sole writer.
    if os.environ.get("GITHUB_ACTIONS") == "true":
        save_cache(cache)
        print("[cache] saved (CI run)")
    else:
        print("[cache] not saved (local run — CI owns the cache file)")


if __name__ == "__main__":
    main()
