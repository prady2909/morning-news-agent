# Morning News Agent — Product Roadmap

*Living document. This is the durable spine of the project — the north star we check every decision against. The per-session handoff docs answer "where exactly did we stop"; THIS answers "where are we going and why." Update it whenever a phase completes, a decision is made, or the plan changes.*

**Last updated:** 2026-07-12 (Session 10)
**Current commit:** `f20c8a2` · local == origin · working tree clean

---

## THE GOAL (the north star — check every decision against this)

A self-updating morning newspaper: a single page that, every morning, shows me the freshest, most useful content across the four topics I care about — **PM, GTM, AI, Startups** — pulled from sources I trust, with AI-generated summaries so I can decide what's worth my time without opening ten tabs.

**The finish line:** I open one page each morning, see recent article summaries that let me grasp the gist in seconds, plus video links for things I'd rather watch. No manual curation. It maintains itself.

---

## WHERE WE ARE RIGHT NOW

**v1 is complete and live** at `prady2909.github.io/morning-news-agent/`.
The pipeline is stateless — it rebuilds from scratch daily via a GitHub Actions scheduler (~7am Boston), builds static HTML, serves via GitHub Pages.

**Next up:** v3 (the AI summarization layer). This is the last big thing between the current product and the goal. It is scoped into 4 phases below. **Session 11 begins with Phase 0.**

**IMPORTANT — we are NOT starting from scratch.** A working proof-of-concept already exists: `summarize.py` (written ~July 4, forgotten until rediscovered in Session 10). It already makes real Gemini calls with a proper anti-hallucination prompt and free-tier rate-limiting. It is dormant and console-only — nothing in the build uses it. So v3 is mostly a *wiring + caching* job, not a build-from-zero. See Decisions Log #6 and the per-phase notes below.

---

## DONE (banked — do not relitigate)

- **v1 core pipeline** — RSS/Atom fetch across 4 topics, daily static build, GitHub Pages serving.
- **Archive calendar** — two-column layout, scan-based clickable days, client-side month navigation, redundant bottom date-list removed. Complete.
- **15-day recency filter** — live front page hides items positively dated older than 15 days; frozen snapshots stay unfiltered. Killed the stale 2022 junk.
- **Source diversity (Session 10)** — 12 feeds added across two commits after rigorous measure-first vetting. GTM went from weakest section to healthy. Live page 48 → 73 items of *recent* content.

---

## THE PLAN — v3 AI Layer (4 phases)

*Discipline: one phase at a time. Each phase is independently shippable and must be verified by ground truth before advancing. Do NOT bundle phases — debugging two hard things at once is how this stalls.*

### Phase 0 — Verify `summarize.py` still works against current Gemini
**Why first:** v3 rests on an assumption never re-tested — that the Gemini key works AND that the July-4 `summarize.py` code (model string `gemini-2.5-flash`, `google-genai` SDK) is still valid against Gemini's current API. Model names and SDK conventions change; that code is weeks old. Verify the foundation before building on it (same measure-first discipline that saved us from dead feeds).
**Work:** Run the EXISTING `summarize.py` as-is (it samples ~4 items and prints Gemini summaries to the console). Do not rewrite it yet — just run it and see.
**Exit criteria:** It runs clean and prints sensible summaries of real feed items. If it errors (bad/expired key, no quota, stale model string, changed SDK call) — fix THAT first, before any Phase 1 wiring. That fix IS the real Phase 0 work if it's needed.
**Note:** Running it consumes a little Gemini quota (~4 calls). Fine.
**Status:** ⬜ Not started

### Phase 1 — Wire summaries into the build (full-body article feeds)
**Why this slice:** Several feeds already carry full article bodies in RSS (Interconnects, Import AI, MKT1, etc. — measured at 5k–40k chars). No scraping needed — the content is already in hand. Simplest possible slice that proves the end-to-end loop.
**The work is porting, not inventing:** The summarization LOGIC already exists in `summarize.py` (prompt, Gemini call, HTML-strip, rate-limit). Phase 1 = lift that logic into the actual build so `build_page.py` generates a summary per article item and renders it on the card. `summarize.py` currently only prints to console and returns nothing to any caller — that's the gap to close.
**Deliberately excluded:** YouTube items (they stay as links — see Decisions Log #3), teaser-only feeds (Phase 3), caching (Phase 2).
**Accept for now:** Re-summarizing the same articles on every daily build. Wasteful but simple — prove the loop works before optimizing. Watch build time / rate-limits: `summarize.py` sleeps 4s/call, so summarizing 20+ items serially could make the 7am build slow — flag if it does.
**Exit criteria:** AI summaries visibly appear on article cards on the built page, generated from real feed content, verified in the browser.
**Status:** ⬜ Not started

### Phase 2 — Caching (the stateful piece)
**Why:** The pipeline rebuilds from scratch daily. Without caching, Phase 1 re-summarizes identical articles every morning — real cost, slower 7am build, more API calls = more failure surface. Caching stops that.
**The big deal:** This is the FIRST time the project remembers something between runs. It's the exact stateful-architecture problem we parked dedup to avoid — v3 forces us to finally solve it. Treat it as a genuine architectural step, not a tweak.
**Exit criteria:** An article summarized once is not re-summarized on subsequent builds; build time and API calls drop measurably.
**Status:** ⬜ Not started

### Phase 3 — Scrape teaser-only article feeds
**Why last (of the article work):** Fragile, per-site, breaks when sites change. Only worth it once summarization + caching are proven. Fetches full article text for feeds that only provide a teaser in RSS, so those items can also be summarized.
**Exit criteria:** Teaser-only feeds get fetched and summarized like full-body ones, with graceful failure when a scrape fails (don't break the build).
**Status:** ⬜ Not started

---

## PARKED — deliberately not doing (and why)

*Revisit only if the stated reason changes. Don't re-raise unprompted.*

- **Dedup / "memory notebook"** — stop showing the same item across days. High-risk stateful work; the recency filter already fixed the worst pain (old junk). v3's caching work (Phase 2) may reshape the stateful foundation — revisit dedup only AFTER Phase 2, if it's still wanted.
- **YouTube transcript summarization** — KILLED, not parked. YouTube items are a discovery problem, not a summarization one: title + link already does the job. Summarizing a promo blurb = summarizing an ad. This deleted what was originally v3's hardest phase. (Decisions Log #3.)
- **Chip-color polish** — cosmetic, near-zero impact. Filler task if ever bored, not a priority.
- **Snapshot rollup** — reorganizing the growing `docs/*.html` pile. ~365 files/yr, harmless. Premature until the folder is genuinely unwieldy.
- **YouTube-first "All" tab** — Prady confirmed it doesn't bother him. Off the table.

---

## DECISIONS LOG (the *why* behind settled calls — don't relitigate)

1. **Measure feeds before adding them.** Proven in Session 10 — caught a 2019 corpse (Shreyas Doshi), a 2024 abandoned feed (Melissa Perri), and a frozen-since-Jan-2026 feed (Growth Unhinged) before they polluted the build. Always check: URL resolves AND feed is alive (recent post) AND content is rich (not teaser). All three, not just "it parsed."
2. **Confirmed-dead feeds — do NOT re-chase:** Shreyas Doshi (2019 legacy URL), Melissa Perri (Sep 2024, abandoned), Growth Unhinged (Substack feed `kylepoyar.substack.com/feed` frozen Jan 2026; only possible live path is the custom-domain feed, a v3-level hunt not worth it now).
3. **YouTube items stay as links — never summarized.** They're for discovery ("go watch this"), and RSS only gives a promo blurb anyway. `sources.py` already tags `type: "article"` vs YouTube channels, so summarization can cleanly attach to articles only. Design consequence: the feed will have two card types (video = "go watch", article = "here's the gist") — that's fine, arguably good.
4. **Sequence v3 as test → summarize → cache → scrape.** Caching is NOT optional — it's what makes daily summarization viable instead of slow/expensive. But it comes AFTER a dumb-but-working summarization pass, so we debug one hard thing at a time.
5. **measure_feeds.py deleted (Session 10).** The old diagnostic was hardwired to fetch.py's feeds and never actually did the measuring — throwaway scratchpad scripts did. Future measuring = fresh scratchpad scripts on demand (worked great). No standing tool to maintain.
6. **`summarize.py` is a working July-4 POC, not junk and not the deleted file.** (Note: it is NOT `measure_feeds.py` — that separate diagnostic was deleted in Session 10; these two get confused because of similar vibes.) `summarize.py` loads the Gemini key from `.env`, reuses `fetch.py`'s health logic to sample ~4 items, and calls `gemini-2.5-flash` via the `google-genai` SDK with a strict source-only/no-fabrication prompt, 4s rate-limit between calls. It PROVES Gemini summarization works on these feeds — but it's dormant: console-only, returns nothing, and nothing in `build_page.py`/`fetch.py` imports it (only comment references). So v3 is "wire this in + cache," not "build summarization from scratch." Unverified: whether `gemini-2.5-flash` + the SDK calls are still current as of today — Phase 0 checks that.

---

## KEY ARCHITECTURE FACTS (context for every future decision)

- **Stateless pipeline** — rebuilds from scratch daily, no memory between runs. Phase 2 is the first deliberate break from this.
- **Archive = capture-date, not publish-date** — the calendar shows what the feed displayed on a given day.
- **Live page filtered to 15 days; snapshots never filtered.**
- **Scheduler commits to origin/main ~7am Boston daily** — always `git fetch`/`git pull` at session start; local drifts behind each morning.
- **Files:** `build_page.py` (pipeline + page builder), `sources.py` (FEEDS list only, no imports), `fetch.py` (feed fetch + health logic), `summarize.py` (dormant Gemini summarization POC — see Decisions Log #6). `.env` holds the Gemini key, git-ignored.
- **`gemini-2.5-flash`** is the intended summarization model, via the `google-genai` SDK (`from google import genai`). Used in `summarize.py` but unverified against current Gemini docs — Phase 0 confirms it still works.

---

## HOW TO USE & MAINTAIN THIS DOC

- **At session start:** read WHERE WE ARE + the current phase's exit criteria. That's your orientation.
- **When a phase completes:** flip its status ⬜ → ✅, move a one-line summary into DONE, update "Last updated" + current commit.
- **When a real decision is made:** add it to the Decisions Log with the *why*. This is what stops future sessions (and fresh Claude instances) from relitigating settled questions.
- **When the plan changes:** edit the phases directly. This doc is meant to be rewritten as reality shifts — a stale roadmap is worse than none.
- **This doc ≠ the handoff.** Roadmap = the durable "where we're going." Handoff = the disposable "where we stopped this session, resume here." Keep both.
