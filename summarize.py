"""
summarize.py — Turns real RSS items into short, faithful summaries with Gemini.

Pipeline:
  1. Load GEMINI_API_KEY from .env (python-dotenv).
  2. Reuse fetch.py's health logic to find a working feed, then pull its
     actual items (feedparser entries: title, link, summary text).
  3. Send the first few items to Gemini Flash, one at a time, asking for a
     short summary that uses ONLY the source and invents nothing.
  4. Sleep briefly between calls to stay under free-tier rate limits.
  5. Print title / summary / link for each so quality can be eyeballed.

Model: gemini-2.5-flash — current-gen Flash, free-tier friendly, and plenty
capable for one-article summaries (no need for the heavier Pro model).
"""

import os
import re
import sys
import time

import feedparser
from dotenv import load_dotenv
from google import genai

# Reuse the fetching/health logic already written in fetch.py.
from fetch import FEEDS, fetch_one, OK


# ── Config ──────────────────────────────────────────────────────────────────

MODEL = "gemini-2.5-flash"   # current free-tier Flash model
MAX_ITEMS = 4                # keep it to the first 3-5 items for a quality check
SLEEP_SECONDS = 4            # ~15 calls/min max — comfortably under free-tier RPM


# ── Source text helpers ───────────────────────────────────────────────────────

def strip_html(text: str) -> str:
    """Feed summaries are often HTML. Drop tags and collapse whitespace so the
    model sees clean prose (and we don't waste tokens on markup)."""
    no_tags = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", no_tags).strip()


def entry_source_text(entry) -> str:
    """Best available body text for an entry: summary, else first content block."""
    if entry.get("summary"):
        return strip_html(entry["summary"])
    if entry.get("content"):
        return strip_html(entry["content"][0].get("value", ""))
    return ""


def get_items(limit: int) -> list:
    """
    Walk FEEDS, use fetch_one() to find healthy (OK) feeds, and take the FIRST
    item from each of the first `limit` healthy feeds — one item per source, so
    the sample spans different feeds and we can compare how rich each one is.
    Returns a list of {title, link, source_text, feed_name} dicts.
    """
    items = []

    for feed_info in FEEDS:
        if len(items) >= limit:
            break

        health = fetch_one(feed_info)
        if health["status"] != OK:
            continue

        parsed = feedparser.parse(feed_info["url"])
        if not parsed.entries:
            continue

        entry = parsed.entries[0]
        print(f"Using feed: {feed_info['name']}  ({feed_info['url']})")
        items.append({
            "title": entry.get("title", "(no title)"),
            "link": entry.get("link", ""),
            "source_text": entry_source_text(entry),
            "feed_name": feed_info["name"],
        })

    if items:
        print()
    return items


# ── Summarization ─────────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """You are summarizing one item for a personal morning news briefing.

Write a short summary (2-3 sentences) of the item below.

Strict rules:
- Use ONLY the information in the SOURCE text. Do not add facts, figures,
  names, dates, or conclusions that are not explicitly present.
- If the source is too thin to summarize meaningfully, say so in one line
  instead of inventing detail.
- Plain, factual tone. No preamble like "This article discusses".

TITLE: {title}

SOURCE:
{source_text}
"""


def summarize_item(client: genai.Client, item: dict) -> str:
    """Send a single item to Gemini and return the summary text."""
    prompt = PROMPT_TEMPLATE.format(
        title=item["title"],
        source_text=item["source_text"] or "(no body text available in the feed)",
    )
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return (response.text or "").strip()


# ── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    # Feed titles/summaries can contain emoji & non-Latin chars; the Windows
    # console defaults to cp1252, which crashes on them. Force UTF-8 output.
    sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY not found. Add it to your .env file.")

    client = genai.Client(api_key=api_key)

    items = get_items(MAX_ITEMS)
    if not items:
        sys.exit("No healthy feeds returned any items.")

    print(f"Summarizing {len(items)} item(s) with {MODEL} ...\n")
    print("=" * 70)

    for i, item in enumerate(items, start=1):
        summary = summarize_item(client, item)

        print(f"\n[{i}] {item['title']}")
        print(f"    Source: {item['feed_name']}")
        print(f"\n{summary}")
        print(f"\nLink: {item['link']}")
        print("\n" + "=" * 70)

        # Respect free-tier rate limits: pause between calls (skip after the last).
        if i < len(items):
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
