# Morning News Agent — Product Roadmap

*Living document. This is the durable spine of the project — the north star we check every decision against. The per-session handoff docs answer "where exactly did we stop"; THIS answers "where are we going and why." Update it whenever a phase completes, a decision is made, or the plan changes.*

**Last updated:** 2026-07-13 (Session 11)
**Current commit:** `bd77739` · local == origin · working tree clean

---

## THE GOAL (the north star — check every decision against this)

A self-updating morning newspaper: a single page that, every morning, shows me the freshest, most useful content across the four topics I care about — **PM, GTM, AI, Startups** — pulled from sources I trust, with AI-generated summaries so I can decide what's worth my time without opening ten tabs.

**The finish line:** I open one page each morning, see recent article summaries that let me grasp the gist in seconds, plus video links for things I'd rather watch. No manual curation. It maintains itself.

---

## WHERE WE ARE RIGHT NOW

**v1 is complete and live** at `prady2909.github.io/morning-news-agent/`.
The pipeline is stateless — it rebuilds from scratch daily via a GitHub Actions scheduler (~7am Boston), builds static HTML, serves via GitHub Pages.

**Next up:** v3 Phase 2 (caching). Phase 0 and Phase 1 are DONE. As of Session 11, the Actions **scheduler** now correctly runs summaries too (the first scheduled run after Phase 1 had been crashing on a missing dependency + missing key — both fixed this session). The remaining phases are below.

**Where the summarization work stands:** The `summarize.py` POC (rediscovered Session 10) was verified working (Phase 0) and its logic is now wired into the build via a new `summaries.py` helper (Phase 1). Summaries appear on the top ~4 recent article cards per section on the LIVE page only. Phase 2 (caching) is the next real step and also the fix for the rate-limit ceiling found in Phase 1 (see Decisions Log #8).

---

## DONE (banked — do not relitigate)

- **v1 core pipeline** — RSS/Atom fetch across 4 topics, daily static build, GitHub Pages serving.
- **Archive calendar** — two-column layout, scan-based clickable days, client-side month navigation, redundant bottom date-list removed. Complete.
- **15-day recency filter** — live front page hides items positively dated older than 15 days; frozen snapshots stay unfiltered. Killed the stale 2022 junk.
- **Source diversity (Session 10)** — 12 feeds added across two commits after rigorous measure-first vetting. GTM went from weakest section to healthy. Live page 48 → 73 items of *recent* content.
- **Living roadmap created + committed (Session 10)** — this file, now tracked in the repo (commit `0839ab1`).
- **v3 Phase 0 — Gemini verified (Session 10)** — ran `summarize.py` as-is; key works, quota live, `gemini-2.5-flash` + `google-genai` SDK still valid, summaries sensible. Foundation confirmed.
- **v3 Phase 1 — AI summaries live (Session 10, commit `e76dff2`)** — new `summaries.py` helper + `build_page.py` wiring; top ~4 recent article items per section get a Gemini summary on the LIVE page (snapshots stay raw v1); YouTube untouched; graceful fallback to teaser on any skip/error verified in the wild. The SaaStr "summary of an ad" trap that killed v2 is defeated (now reads full bodies).
- **Scheduler summary fix (Session 11, commit `bd77739`)** — Phase 1 shipped `summaries.py` but the Actions workflow still only did `pip install feedparser` and passed NO Gemini key, so the *first scheduled run* after Phase 1 crashed with `ModuleNotFoundError: No module named 'dotenv'`. Fixed two things in `.github/workflows/daily-build.yml`: (1) install line now `pip install feedparser google-genai python-dotenv`; (2) added an `env:` block to the "Build the news page" step passing `GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}`. Also created the `GEMINI_API_KEY` repository secret (Settings → Secrets → Actions) — it did not exist before. Verified: manual `workflow_dispatch` run #9 went green and real summaries render on the live scheduler-built page. (The earlier red run that first surfaced this was masked by an unrelated GitHub infra outage — "Failed to resolve action download info" — which cleared on re-run.)

---

## THE PLAN — v3 AI Layer (4 phases)

*Discipline: one phase at a time. Each phase is independently shippable and must be verified by ground truth before advancing. Do NOT bundle phases — debugging two hard things at once is how this stalls.*

### Phase 0 — Verify `summarize.py` still works against current Gemini ✅ DONE (Session 10)
Ran `summarize.py` as-is. Key works, quota available, `gemini-2.5-flash` + `google-genai` SDK still valid, summaries sensible. The anti-hallucination guard fired correctly on a thin item. Foundation confirmed — no fix was needed.
**Status:** ✅ Done

### Phase 1 — Wire summaries into the build (full-body article feeds) ✅ DONE (Session 10, commit `e76dff2`)
Built `summaries.py` (lifts prompt/client/model/HTML-strip from `summarize.py`) + wired `add_summaries()` into `build_page.py`. Top `SUMMARIES_PER_SECTION = 4` most-recent article items per section get a Gemini summary; videos never summarized; summaries gated to the LIVE index only (`is_index`), snapshots stay raw v1; every skip/error falls back to the teaser card. Verified in browser: ~12 good summaries, clean fallback, layout holds, YouTube untouched.
**Two findings logged for Phase 2 (see Decisions Log #7, #8):**
- **Field-priority bug fixed:** the lifted `entry_source_text` preferred the tiny `summary` field; changed to take the LONGER of `content[0].value` vs `summary` (matches how feeds were measured). Without this, rich Substack posts were wrongly skipped as "too thin."
- **Rate limit is real:** Gemini free tier is **5 requests/minute** for `gemini-2.5-flash` (ground-truth from the build; ~3 of 16 calls hit 429 and fell back to teasers). Left the 4s sleep as-is because Phase 2 caching dissolves this (only new items get summarized).
**Open polish note (not a blocker):** summaries run a touch long (4–6 lines); if it feels heavy in daily use, tighten the prompt to a hard 2-sentence cap later.
**Status:** ✅ Done

### Phase 2 — Caching (the stateful piece) ← NEXT UP
**Why:** The pipeline rebuilds from scratch daily. Without caching, Phase 1 re-summarizes identical articles every morning — real cost, more API calls = more failure surface, AND it collides with the 5-req/min free-tier limit. **Session 11 gave hard evidence:** the scheduler's run #9 made 10 calls, 4 failed (429 quota + 503 capacity), and Startups — always processed last — got starved to zero summaries every build (see Decisions Log #9). Caching means only NEW articles get summarized each day (~3–5), which drops under the 5/min cap — so caching is both the efficiency fix AND the (429) rate-limit fix.
**IMPORTANT caveat (don't be surprised):** caching fixes *volume*, not *rate*. (a) The FIRST build after caching deploys has an empty cache → every item is "new" → you'll hit the same 429s once while it fills. (b) Caching does NOT touch 503 "high demand" errors — those are Gemini capacity, independent of usage. So keep the graceful teaser-fallback AND keep SUMMARIES_PER_SECTION capped at least through the cold-start build. Don't rip the cap out the moment caching lands.
**The big deal:** This is the FIRST time the project remembers something between runs. It's the exact stateful-architecture problem we parked dedup to avoid — v3 forces us to finally solve it. Treat it as a genuine architectural step, not a tweak. Key design question to resolve FIRST: WHERE the cache lives and how it survives the scheduler's daily rebuild. Leading candidate = a committed JSON file keyed by article URL. **Critical sub-questions to settle before coding:** (1) The Actions workflow currently only commits `docs/` — the cache file must ALSO be written+committed back to origin each run or it never persists (check/extend the "Commit & push" step). (2) Only cache SUCCESSFUL summaries — a 429/503 fallback must stay uncached so it retries next build, else a throttled item is stuck as a teaser forever. (3) Local-build discipline: like `docs/<today>.html`, decide whether the cache is `git restore`d locally so only the scheduler owns it.
**Once caching lands:** the `SUMMARIES_PER_SECTION = 4` cap can likely be raised (but keep SOME cap through cold-start — see caveat).
**Exit criteria:** An article summarized once is not re-summarized on subsequent builds; build time and API calls drop measurably; 429s effectively disappear under normal daily volume (Startups stops getting starved); occasional 503s still tolerated via fallback.
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
- **Node 20 deprecation warning (surfaced Session 11)** — the Actions build throws a non-blocking warning that `actions/checkout@v4` and `actions/setup-python@v5` run on deprecated Node 20. Harmless for now (warning only, build stays green). Low-priority cleanup: bump to `checkout@v5` / `setup-python@v6` someday. Not urgent.
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
6. **`summarize.py` is a working July-4 POC, not junk and not the deleted file.** (Note: it is NOT `measure_feeds.py` — that separate diagnostic was deleted in Session 10; these two get confused because of similar vibes.) `summarize.py` loads the Gemini key from `.env`, reuses `fetch.py`'s health logic to sample ~4 items, and calls `gemini-2.5-flash` via the `google-genai` SDK with a strict source-only/no-fabrication prompt, 4s rate-limit between calls. It PROVES Gemini summarization works on these feeds. As of Phase 1 its logic is lifted into `summaries.py`; `summarize.py` itself is left in place, unchanged, as the original POC.
7. **Body extraction takes the LONGER of `content[0].value` vs `summary` (Session 10).** The POC preferred `summary` first, but on Substack feeds `summary` is a tiny teaser (37–311 chars) while the full post lives in `content[0].value` (8k–34k). Preferring summary silently fed the summarizer teasers and skipped rich posts as "too thin" — and worse, produced weak summaries of ad-blurbs (the v2-killer trap). `summaries.py` `entry_source_text` now takes the longer field, matching how feeds were originally measured. `summarize.py` still has the old summary-first logic but it's dormant, so not worth touching.
8. **Gemini free tier has TWO failure modes, not one (corrected Session 11).** The quota is **5 requests/minute** (`GenerateRequestsPerMinutePerProjectPerModel-FreeTier`, `quotaValue: '5'`) → over-limit calls return **429 RESOURCE_EXHAUSTED**. SEPARATELY, Gemini also returns intermittent **503 UNAVAILABLE ("high demand")** that has nothing to do with your usage — it's their capacity. Session 11's scheduler run (#9) made 10 API calls: 6 summarized, 4 skipped-error (two 429s + two 503s), 1 skipped-too-thin. **Implications:** (a) real daily call volume is ~10, not the ~16 the SUMMARIES_PER_SECTION=4 cap implied (many sections have <4 article candidates). (b) **Phase 2 caching fixes the 429s** (fewer calls/build → under 5/min) but does NOT fix 503s — an occasional 503 will still drop a summary to teaser even post-cache; that self-heals next run and the graceful fallback keeps the build green. (c) Do NOT pay for a higher tier for a hobby project.
9. **Startups is ALWAYS processed last, so it ALWAYS gets starved without caching (Session 11).** Sections summarize in order PM → GTM → AI → Startups. The 5/min quota is spent by the time Startups' calls fire, so on run #9 all 4 Startups items errored (429/503) and fell back to teasers while PM/GTM/AI got real summaries. This is deterministic, not random — Startups loses the race every no-cache build. IMPORTANT: this was initially mis-hypothesized as the SaaStr "teaser-trap" (body too thin → Phase 3 territory); the build log disproved that — every Startups skip was `skipped-error` (rate/capacity), NOT `skipped-too-thin`. SaaStr bodies ARE rich enough. So this is purely a rate-limit ordering artifact that Phase 2 caching resolves — NOT a scraping problem. (Lesson: check the log's skip-reason, don't guess.)

---

## KEY ARCHITECTURE FACTS (context for every future decision)

- **Stateless pipeline** — rebuilds from scratch daily, no memory between runs. Phase 2 is the first deliberate break from this.
- **Archive = capture-date, not publish-date** — the calendar shows what the feed displayed on a given day.
- **Live page filtered to 15 days; snapshots never filtered.**
- **Scheduler commits to origin/main ~7am Boston daily** — always `git fetch`/`git pull` at session start; local drifts behind each morning.
- **Files:** `build_page.py` (pipeline + page builder, now also orchestrates summaries), `sources.py` (FEEDS list only, no imports), `fetch.py` (feed fetch + health logic), `summaries.py` (LIVE summarization helper used by the build — prompt, Gemini client, longer-field extraction), `summarize.py` (original dormant POC, unchanged, kept for reference). `.env` holds the Gemini key, git-ignored.
- **`gemini-2.5-flash`** via the `google-genai` SDK (`from google import genai`) — verified working Session 10. Free tier: **5 req/min** quota (429 on over-limit) PLUS intermittent 503 capacity errors (see Decisions Log #8).
- **Actions workflow now installs summary deps + passes the key (Session 11).** `.github/workflows/daily-build.yml` runs `pip install feedparser google-genai python-dotenv` and passes `GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}` to the build step. The key lives as a **repository secret** (Settings → Secrets → Actions), NOT in `.env` on the runner (there is no `.env` on the runner — `load_dotenv()` no-ops there and the key comes from the env var). Locally, the key still comes from the git-ignored `.env`.
- **Summaries are LIVE-index only** — `render_item(is_index=True)` gates them; snapshots never carry summaries and stay raw v1. `SUMMARIES_PER_SECTION = 4` caps how many per section (revisit after Phase 2 caching).

---

## HOW TO USE & MAINTAIN THIS DOC

- **At session start:** read WHERE WE ARE + the current phase's exit criteria. That's your orientation.
- **When a phase completes:** flip its status ⬜ → ✅, move a one-line summary into DONE, update "Last updated" + current commit.
- **When a real decision is made:** add it to the Decisions Log with the *why*. This is what stops future sessions (and fresh Claude instances) from relitigating settled questions.
- **When the plan changes:** edit the phases directly. This doc is meant to be rewritten as reality shifts — a stale roadmap is worse than none.
- **This doc ≠ the handoff.** Roadmap = the durable "where we're going." Handoff = the disposable "where we stopped this session, resume here." Keep both.
