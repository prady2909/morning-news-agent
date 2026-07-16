"""
summaries.py — Gemini summarization helpers for build_page.py (v3 Phase 1).

The summarization logic here is lifted, unchanged, from summarize.py — same
prompt, same google-genai client call, same model, same HTML-stripping — so the
page build reuses the exact behaviour that was already proven to work, rather
than reinventing it. build_page.py owns the orchestration (which items, logging,
rate-limit sleep, graceful fallback); this module owns the low-level pieces.
"""

import os
import re

from dotenv import load_dotenv
from google import genai


# ── Config (lifted from summarize.py) ─────────────────────────────────────────

MODEL = "gemini-2.5-flash"   # current free-tier Flash model
SLEEP_SECONDS = 12           # 60/12 = 5 calls/min — safe under observed 5 RPM (and the ~10 RPM published for 2.5-flash). Bandaid pending real 429 backoff.

# A body shorter than this is basically already a teaser — summarizing it would
# be a summary-of-a-summary, so build_page skips it and keeps the teaser card.
MIN_SOURCE_CHARS = 300


# ── Source text helpers (lifted from summarize.py) ────────────────────────────

def strip_html(text: str) -> str:
    """Feed summaries are often HTML. Drop tags and collapse whitespace so the
    model sees clean prose (and we don't waste tokens on markup)."""
    no_tags = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", no_tags).strip()


def entry_source_text(entry) -> str:
    """Richest body text for an entry: the LONGER of the stripped content block
    and the stripped summary.

    NOTE: this intentionally differs from summarize.py, which preferred `summary`
    first. On many Substack feeds `summary` is only a ~40-150 char teaser while
    the full post lives in `content[0].value` (8k-34k chars); summary-first fed
    the summarizer the teaser and got most rich items skipped as too-thin. Taking
    the longer field matches how the candidate feeds were measured (richer of the
    two) and gives the model the actual article."""
    candidates = []
    if entry.get("content"):
        candidates.append(strip_html(entry["content"][0].get("value", "")))
    if entry.get("summary"):
        candidates.append(strip_html(entry["summary"]))
    return max(candidates, key=len) if candidates else ""


# ── Summarization (lifted from summarize.py) ──────────────────────────────────

# Bump this whenever PROMPT_TEMPLATE (or how we summarize) changes materially.
# The cache stores it alongside each summary, so a bump makes every summary built
# under an older prompt a cache miss → it gets re-summarized with the new prompt.
PROMPT_VERSION = 1

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


def make_client():
    """Build a Gemini client from GEMINI_API_KEY in .env. Returns None (never
    raises) if the key is missing or the client can't be constructed — a missing
    key degrades the build to teaser-only cards instead of crashing it."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def summarize_item(client: genai.Client, title: str, source_text: str) -> str:
    """Send a single item to Gemini and return the summary text (may raise —
    build_page wraps this so one failure can't crash the whole build)."""
    prompt = PROMPT_TEMPLATE.format(
        title=title,
        source_text=source_text or "(no body text available in the feed)",
    )
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return (response.text or "").strip()
