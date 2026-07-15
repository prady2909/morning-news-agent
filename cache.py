"""
cache.py — Versioned summary cache for the morning news aggregator.

Standalone, pure module: reads/writes a single local JSON file and manipulates
dicts. Makes NO network or API calls and imports no other project module.

Cache entries are keyed by a normalized article URL. Each entry records the
model and prompt_version that produced the summary, so a future prompt or model
change automatically invalidates stale summaries (they become misses).
"""

import json
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

CACHE_PATH = "summary_cache.json"


def normalize_url(url):
    """Lowercase scheme+host, drop query string and fragment. Must match the
    normalization used when the feeds were probed (query-strip is a safe no-op
    today but defends against feeds that start adding tracking params later)."""
    p = urlsplit(url or "")
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, "", ""))


def load_cache(path=CACHE_PATH):
    """Return the cache dict. If the file is missing or corrupt, return an empty
    dict and print a warning — a bad cache file must NEVER crash the build."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[cache] WARNING: could not read {path} ({e}); starting empty")
        return {}


def get_cached(cache, url, model, prompt_version):
    """Return the cached summary string ONLY if an entry exists for this
    normalized URL AND it was produced with the same model AND the same
    prompt_version. Otherwise return None (a miss -> caller re-summarizes)."""
    entry = cache.get(normalize_url(url))
    if not entry:
        return None
    if entry.get("model") != model or entry.get("prompt_version") != prompt_version:
        return None
    return entry.get("summary")


def set_cached(cache, url, summary, model, prompt_version):
    """Store a summary under the normalized URL. Mutates `cache` in place.
    NOTE: the caller must only call this on a SUCCESSFUL summary — never cache a
    rate-limit/error/too-thin fallback, so throttled items retry next build."""
    cache[normalize_url(url)] = {
        "summary": summary,
        "model": model,
        "prompt_version": prompt_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def save_cache(cache, path=CACHE_PATH):
    """Write the cache to disk as pretty JSON with sorted keys, so the daily git
    diff stays small and readable."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True, ensure_ascii=False)


if __name__ == "__main__":
    # Self-test: proves the logic with no network, Gemini, or build code.
    TMP = "_cache_selftest.json"
    passed = failed = 0

    def check(name, condition):
        global passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}")

    # Make sure we start clean.
    if os.path.exists(TMP):
        os.remove(TMP)

    print("cache.py self-test")
    print("-" * 40)

    try:
        # 1. Empty miss: non-existent cache -> get_cached returns None.
        cache = load_cache(TMP)
        check("empty miss returns None",
              get_cached(cache, "https://blog.com/a", "gemini-1", "v1") is None)

        # 2. Round-trip hit: set -> save -> reload -> same model/version hits.
        set_cached(cache, "https://blog.com/a", "summary-A", "gemini-1", "v1")
        save_cache(cache, TMP)
        reloaded = load_cache(TMP)
        check("round-trip hit returns summary",
              get_cached(reloaded, "https://blog.com/a", "gemini-1", "v1") == "summary-A")

        # 3. Prompt-version gate: bumped prompt_version -> miss.
        check("bumped prompt_version invalidates",
              get_cached(reloaded, "https://blog.com/a", "gemini-1", "v2") is None)

        # 4. Model gate: different model -> miss.
        check("different model invalidates",
              get_cached(reloaded, "https://blog.com/a", "gemini-2", "v1") is None)

        # 5. URL normalization: different query string, same article -> hit.
        norm_cache = {}
        set_cached(norm_cache, "https://Blog.com/post?ref=1", "summary-N", "gemini-1", "v1")
        check("query-strip + lowercase key hits",
              get_cached(norm_cache, "https://blog.com/post?ref=999", "gemini-1", "v1") == "summary-N")

        # 6. Corrupt file safety: garbage -> load_cache returns {} without raising.
        with open(TMP, "w", encoding="utf-8") as f:
            f.write("this is not json {{{")
        try:
            corrupt = load_cache(TMP)
            check("corrupt file returns {} without raising", corrupt == {})
        except Exception as e:
            check(f"corrupt file returns {{}} without raising (raised {e!r})", False)

    finally:
        if os.path.exists(TMP):
            os.remove(TMP)

    print("-" * 40)
    print(f"{passed} passed, {failed} failed")
    if os.path.exists(TMP):
        print(f"WARNING: temp file {TMP} still exists")
    else:
        print(f"temp file {TMP} cleaned up")
