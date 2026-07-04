"""
fetch.py — Checks every feed in sources.py and reports its health.

What this file does:
  1. Imports the FEEDS list from sources.py
  2. Calls feedparser.parse() on each URL — this downloads and parses the feed
  3. Categorises each result as OK / EMPTY / DEAD
  4. Prints a live log as it runs, then a tidy summary at the end

Key thing to understand about feedparser:
  - It NEVER raises an exception — even if the URL is wrong or the site is down,
    it always returns an object. You read the object's properties to know what happened.
  - The 'bozo' flag is True when something went wrong (bad URL, parse error, etc.).
  - 'feed.entries' is the list of posts/videos found in the feed.
"""

import feedparser
from sources import FEEDS


# ── Status constants ──────────────────────────────────────────────────────────

OK    = "OK"
EMPTY = "EMPTY"   # URL worked but feed had 0 items
DEAD  = "DEAD"    # URL failed or feed was completely unparseable


# ── Core fetcher ──────────────────────────────────────────────────────────────

def fetch_one(feed_info: dict) -> dict:
    """
    Fetches a single RSS feed and returns a result dict.

    feedparser.parse() accepts any URL and returns a parsed feed object.
    We inspect three things:
      - feed.bozo       : True if something went wrong during fetch/parse
      - feed.entries    : list of items (posts, videos, etc.) found
      - feed.bozo_exception : the actual error, if bozo is True
    """
    feed = feedparser.parse(feed_info["url"])

    has_entries = len(feed.entries) > 0

    # A feed can be "bozo" but still have partial entries (sloppy XML).
    # We only call it DEAD when bozo fired AND there's nothing to show for it.
    if feed.bozo and not has_entries:
        exc = getattr(feed, "bozo_exception", "unknown error")
        return {**feed_info, "status": DEAD, "item_count": 0, "detail": str(exc)}

    if not has_entries:
        return {**feed_info, "status": EMPTY, "item_count": 0, "detail": "0 items returned"}

    return {**feed_info, "status": OK, "item_count": len(feed.entries), "detail": None}


# ── Runner ────────────────────────────────────────────────────────────────────

def fetch_all(feeds: list) -> list:
    """Iterates over every feed, prints a one-line status per feed, returns results."""
    results = []
    total = len(feeds)

    for i, feed_info in enumerate(feeds, start=1):
        name = feed_info["name"]
        print(f"[{i:>2}/{total}] {name}")

        result = fetch_one(feed_info)
        results.append(result)

        status = result["status"]
        if status == OK:
            print(f"         [OK]    {result['item_count']} items found")
        elif status == EMPTY:
            print(f"         [EMPTY] Feed reachable but returned 0 items")
        else:
            print(f"         [DEAD]  {result['detail']}")

    return results


# ── Summary printer ───────────────────────────────────────────────────────────

def print_summary(results: list) -> None:
    """
    Groups results into OK / EMPTY / DEAD and prints the ones that need
    attention. EMPTY feeds are worth fixing because they may just need a
    corrected URL; DEAD feeds are either wrong URLs or paywalled sources.
    """
    ok    = [r for r in results if r["status"] == OK]
    empty = [r for r in results if r["status"] == EMPTY]
    dead  = [r for r in results if r["status"] == DEAD]

    print()
    print("=" * 60)
    print(f" RESULTS: {len(ok)} OK  |  {len(empty)} EMPTY  |  {len(dead)} DEAD  (of {len(results)} total)")
    print("=" * 60)

    if not empty and not dead:
        print("\n All feeds are working — nothing to fix.")
        return

    print("\n Feeds to fix:\n")

    if dead:
        print(" --- DEAD (wrong URL, site down, or no RSS) ---")
        for r in dead:
            print(f"   [{r['topic']}] {r['name']}")
            print(f"          URL : {r['url']}")
            print(f"          ERR : {r['detail']}")
            print()

    if empty:
        print(" --- EMPTY (URL reachable but no items found) ---")
        for r in empty:
            print(f"   [{r['topic']}] {r['name']}")
            print(f"          URL : {r['url']}")
            print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Checking {len(FEEDS)} feeds ...\n")
    results = fetch_all(FEEDS)
    print_summary(results)
