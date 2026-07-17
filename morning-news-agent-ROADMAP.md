# Morning News Agent — Product Roadmap

*Living document. This is the durable spine of the project — the north star we check every decision against. The per-session handoff docs answer "where exactly did we stop"; THIS answers "where are we going and why." Update it whenever a phase completes, a decision is made, or the plan changes.*

**Last updated:** 2026-07-17 (Session 17)
**Latest code commit:** `2d6af9f` (Session 17 — editorial reskin + three segmented filter toggles with fill-selection). Earlier same day: `3ef215b` (S17 — filter rewire, segmented topic/format toggles, killed the double-All). Prior: `c481f4e` (S15 — summary pacing fix). This roadmap update commits directly above `2d6af9f` — the roadmap commit is always the tip right after a session close.

---

## THE GOAL (the north star — check every decision against this)

A self-updating morning newspaper: a single page that, every morning, shows me the freshest, most useful content across the four topics I care about — **PM, GTM, AI, Startups** — pulled from sources I trust, with AI-generated summaries so I can decide what's worth my time without opening ten tabs.

**The finish line:** I open one page each morning, see recent article summaries that let me grasp the gist in seconds, plus video links for things I'd rather watch. No manual curation. It maintains itself.

---

## WHERE WE ARE RIGHT NOW

**v1 is complete and live** at `prady2909.github.io/morning-news-agent/`.

**v3 Phase 2 (caching) — ✅ COMPLETE, live payoff verified (Session 13).** The full caching layer is built, committed, and now PROVEN in production. The **July 15 cron ran cold** and populated the cache (7 summarized · 0 hits · 9 API calls · 68.6s); the **July 16 cron read it back** — **6 cache-hits · 3 API calls · 0 errors · 25.6s**, and Startups (SaaStr) got summarized instead of starved last. Every Phase 2 exit criterion met with real `[summaries]` log evidence.

**Phase 3 (scrape teaser-only feeds) — ❌ KILLED (Session 14).** A throwaway measurement probe (reusing the real `entry_source_text` + `MIN_SOURCE_CHARS = 300`) sampled all 22 article feeds: every one came back FULL-BODY, 0 teaser-only, 0 mixed, only 7/375 items (2%) under threshold and those were scattered one-off link/note posts. The premise of the phase — that some feeds ship only teasers — is false for the current feed list. Building brittle per-site scrapers to rescue ~2% of mostly-non-article items is a bad trade. Killed on evidence. See Decisions Log #15.

**UI redesign — editorial reskin — ✅ COMPLETE (Session 17, commits `3ef215b` + `2d6af9f`).** Portfolio-driven visual overhaul, done in three verified steps. (1) Filter rewire (`3ef215b`): killed both "All" buttons, topic (AI·PM·GTM·Startups) + format (Articles·Videos) became segmented toggles, × per group resets, default = everything; the old topic-All + format-All double-"All" is gone. (2) Editorial reskin + three toggles (`2d6af9f`): serif headlines (Georgia, high-contrast, never red), warm off-white light (`#faf8f3`) / warm off-black dark (`#161410`, deliberately tinted — NOT pure black, pairs with the serif), manual light/dark via a THIRD segmented toggle (sun·moon, inline SVG, no icon-font dep, no-flash script, localStorage-persisted), neutral card tags (dropped `TOPIC_COLORS`/`color_for`), tabular figures, ~65ch measure, darker greys. (3) Selection mechanic settled on FILL, not slide: the selected segment fills solid — black in light / white in dark — with the label flipping to page-bg colour for contrast while unselected labels stay red; internal dividers neutral, only the outer bar border red. A sliding-pill version was built and rejected (the free-floating pill couldn't align to the segment → visible gap + red corner leak; filling the segment itself is exact). Net result: NO animation on the page. All filter behaviour (null-state logic, count, card-tag-drives-topic, calendar) preserved byte-for-byte from v1. See Decisions Log #18.

**Where the work goes next:**
- **Summarization hardening (recommended next build):** (1) ✅ DONE S15 — honest pacing, `SLEEP_SECONDS` 4→12 (was pacing ~15/min against a ~5–10 RPM limit, no retry). (2) NEXT — exponential backoff on 429 (the permanent cure; makes the exact RPM number stop mattering). (3) THEN — raise `SUMMARIES_PER_SECTION` 4→6, safe ONLY after backoff. Do not reorder these.
- **v4 (live news feed):** 🔵 CANDIDATE — needs a scoping decision (curated-digest vs. news-aggregator identity) + concept pick (A/B/C) before any code. Fresh chat.
- **Dark-mode palette taste-tweak (optional, trivial):** the warm off-black (`#161410`/`#1f1c17`) reads slightly brown/chocolate. Prady saw it, considered neutral charcoal (`#141414`) vs true-black (`#0d0d0d`), and chose to KEEP the warm tint. Revisit only if it nags — a 3-value swap in `:root[data-theme="dark"]`.

---

## DONE (banked — do not relitigate)

- **v1 core pipeline** — RSS/Atom fetch across 4 topics, daily static build, GitHub Pages serving.
- **Archive calendar** — two-column layout, scan-based clickable days, client-side month navigation, redundant bottom date-list removed. Complete.
- **15-day recency filter** — live front page hides items positively dated older than 15 days; frozen snapshots stay unfiltered. Killed the stale 2022 junk.
- **Source diversity (Session 10)** — 12 feeds added across two commits after rigorous measure-first vetting. GTM went from weakest section to healthy. Live page 48 → 73 items of *recent* content.
- **Living roadmap created + committed (Session 10)** — this file, now tracked in the repo (commit `0839ab1`).
- **v3 Phase 0 — Gemini verified (Session 10)** — ran `summarize.py` as-is; key works, quota live, `gemini-2.5-flash` + `google-genai` SDK still valid, summaries sensible. Foundation confirmed.
- **v3 Phase 1 — AI summaries live (Session 10, commit `e76dff2`)** — new `summaries.py` helper + `build_page.py` wiring; top ~4 recent article items per section get a Gemini summary on the LIVE page (snapshots stay raw v1); YouTube untouched; graceful fallback to teaser on any skip/error verified in the wild. The SaaStr "summary of an ad" trap that killed v2 is defeated (now reads full bodies).
- **Scheduler summary fix (Session 11, commit `bd77739`)** — Phase 1 shipped `summaries.py` but the Actions workflow still only did `pip install feedparser` and passed NO Gemini key, so the *first scheduled run* after Phase 1 crashed with `ModuleNotFoundError: No module named 'dotenv'`. Fixed the install line + added an `env:` block passing `GEMINI_API_KEY`; created the repo secret. Verified green + real summaries on the scheduler-built page.
- **v3 Phase 2 — Caching ✅ COMPLETE (Session 12 shipped · Session 13 verified)** — three commits, one clean phase, verified one hard thing at a time:
  - `cache.py` (commit `44948b6`) — standalone, pure module. Reads/writes `summary_cache.json`, keyed on normalized URL, versioned entries. 6/6 self-test PASS (empty-miss, round-trip hit, prompt-version gate, model gate, URL normalization, corrupt-file safety). No network, no imports of project code.
  - Cache wiring (commit `eab195c`) — `add_summaries(items, client, cache)` threads the cache dict as an argument (no global); loaded once in `main()`; checked at the top of the item loop (hit → reuse, no API call, no sleep); `set_cached` fires ONLY on the success path; CI-only write-guard on `GITHUB_ACTIONS == "true"`.
  - Workflow persistence (commit `4a83821`) — `.github/workflows/daily-build.yml` commit step now stages `docs/ summary_cache.json` (was `docs/`); existing "nothing changed" guard preserved.
  - **Verified in the wild:** manual `workflow_dispatch` run #11 went green, and `summary_cache.json` now exists in the repo as a bot-committed file. Its `{}` (empty) content is CORRECT for that run — every summary 429'd (quota already spent by earlier local tests), and only successes are cached, so nothing was stored. Plumbing proven; live HIT still pending (see Phase 2 exit criteria + Decisions Log #13).
  - **LIVE PAYOFF VERIFIED (Session 13, from `[summaries]` logs of the two scheduled crons):** July 15 (`Daily news build #12`) ran cold → 7 summarized · 0 cache-hit · 2 skipped-error · **9 API calls** · 68.6s, wrote 7 entries. July 16 (`Daily news build #13`) ran warm → 3 summarized · **6 cache-hit** · 0 skipped-error · **3 API calls** · 25.6s. Call volume 9→3, errors 2→0, runtime 68.6s→25.6s, and Startups/SaaStr summarized (3 fresh entries) instead of starved. Cache file confirmed 10 total entries (7×07-15, 3×07-16), all `gemini-2.5-flash` / pv 1. This is the Phase 2 proof. (See Decisions Log #14.)

---

## THE PLAN — v3 AI Layer (4 phases)

*Discipline: one phase at a time. Each phase is independently shippable and must be verified by ground truth before advancing. Do NOT bundle phases — debugging two hard things at once is how this stalls.*

### Phase 0 — Verify `summarize.py` still works against current Gemini ✅ DONE (Session 10)
**Status:** ✅ Done

### Phase 1 — Wire summaries into the build (full-body article feeds) ✅ DONE (Session 10, commit `e76dff2`)
**Status:** ✅ Done
**Open polish note (not a blocker):** summaries run a touch long (4–6 lines); tighten the prompt to a hard 2-sentence cap later. NOTE: doing this means bumping `PROMPT_VERSION` (see Decisions Log #11) so the cache re-summarizes old entries under the new prompt.

### Phase 2 — Caching (the stateful piece) ✅ DONE (Session 12 shipped · Session 13 verified)
**Status:** ✅ Done
**What shipped:** `cache.py` + wiring + workflow persistence, all committed & green (see DONE). Key = normalized URL (Decisions Log #10). Value = versioned object (Decisions Log #11). Local discipline solved via a CI-only write-guard, NOT the git-restore originally planned (Decisions Log #12).
**Still to verify (the one thing we haven't seen):** a real cache HIT. This needs a run that summarizes successfully first (to populate the cache), then a subsequent run that reads it. Run #11 came back empty because its quota was already spent by same-evening local tests — expected, self-heals.
**Cold-start caveat (confirmed in practice):** the first populated build still fires real API calls; caching cuts *volume*, not the per-minute *rate*, and does nothing for 503s. Keep the graceful teaser fallback and keep `SUMMARIES_PER_SECTION = 4` at least through cold-start.
**Exit criteria — ALL MET (Session 13):** ✅ article summarized once isn't re-summarized (6 cache-hits on the July 16 cron); ✅ cache persists across runs (10 entries committed by CI across the 15th + 16th); ✅ 429s measurably drop and Startups stops getting starved (API calls 9→3, skipped-error 2→0, SaaStr/Startups summarized). Proof lines: July 15 `#12` = 7 summarized · 0 hit · 9 calls; July 16 `#13` = 3 summarized · 6 hit · 3 calls.
**Once fully verified:** `SUMMARIES_PER_SECTION = 4` can likely be raised (keep SOME cap through cold-start).

### Phase 3 — Scrape teaser-only article feeds ❌ KILLED (Session 14)
**Status:** ❌ Killed — not built, deliberately abandoned on evidence.
**Why killed:** Session 14 measurement probe found 0/22 article feeds are teaser-only (all FULL-BODY; 2% of items under the 300-char threshold, mostly one-off link/note posts). No scrape candidates exist, so there's nothing to justify fragile per-site scraping. The Phase-1 `MIN_SOURCE_CHARS` + longer-field logic already handles the rare thin item via graceful teaser fallback.
**If a feed ever goes teaser-only:** re-run the probe pattern; handle it as a targeted fix, not a standing phase. Don't build scraper infra pre-emptively.

### v4 — Live news feed 🔵 CANDIDATE (needs scoping — Session 14)
**The idea:** a section fed by actual news sources (news-wire RSS, Google News by topic), refreshed more often than the daily digest, so genuinely breaking items show up intraday.
**Concept options surfaced (Session 14, not yet chosen):** A = breaking column on the existing page (news-wire + Google News RSS, hourly cron; lowest risk, reuses everything). B = separate `/live` page refreshing hourly. C = topic-search via a news API (GNews/NewsAPI; most powerful, adds an API + quota).
**Ruled out as not viable on free static hosting:** X/Twitter (paid/locked API, scraping breaks ToS), YouTube "trending" (no clean free feed), true real-time (needs a server).
**Open scoping question before this goes active:** adding news-wire sources + an hourly cron shifts the project from "curated thought-leadership digest" toward "news aggregator." That's an identity decision, not just a build task — resolve it before writing code.
**Next step:** fresh chat, pick a concept, scope it. Do NOT start building until the concept is locked (standing rule: new window for the first real step of a phase).

---

## PARKED — deliberately not doing (and why)

*Revisit only if the stated reason changes. Don't re-raise unprompted.*

- **Dedup / "memory notebook"** — the recency filter already fixed the worst pain. Phase 2's caching is now the project's stateful foundation; revisit dedup only if still wanted after Phase 2 is fully verified.
- **YouTube transcript summarization** — KILLED, not parked (Decisions Log #3). Videos stay as plain links.
- **Node 20 deprecation warning** — non-blocking Actions warning that `checkout@v4` / `setup-python@v5` run on deprecated Node 20 (build stays green; it's being force-run on Node 24). Low-priority: bump to `checkout@v5` / `setup-python@v6` someday. Surfaced again Session 11 & 12; still parked.
- **Chip-color polish** — cosmetic filler task.
- **Snapshot rollup** — reorganizing the growing `docs/*.html` pile. Premature.
- **YouTube-first "All" tab** — off the table.
- **OneDrive + git file-locks after rebases** — parked; don't re-diagnose unprompted.
- **The `Co-Authored-By: Claude` on an old commit + `claude` listed as a repo contributor** — legacy from an early commit; rewriting public history isn't worth it. Prady confirmed it doesn't bother him. Note: keep NEW commits free of AI attribution (standing rule).

---

## DECISIONS LOG (the *why* behind settled calls — don't relitigate)

1. **Measure feeds before adding them.** (Session 10) Always check URL resolves AND feed is alive AND content is rich.
2. **Confirmed-dead feeds — do NOT re-chase:** Shreyas Doshi (2019), Melissa Perri (Sep 2024), Growth Unhinged (Substack feed frozen Jan 2026).
3. **YouTube items stay as links — never summarized.** Discovery, not summarization; RSS only gives a promo blurb.
4. **Sequence v3 as test → summarize → cache → scrape.** One hard thing at a time.
5. **measure_feeds.py deleted (Session 10).** Future measuring = fresh throwaway scratchpad scripts on demand.
6. **`summarize.py` is a working POC, left untouched.** Its logic was lifted into `summaries.py` in Phase 1; the original stays dormant for reference. (NOT the deleted `measure_feeds.py`.)
7. **Body extraction takes the LONGER of `content[0].value` vs `summary` (Session 10).** Prevents feeding the summarizer tiny teasers and skipping rich Substack posts.
8. **Gemini free tier has TWO failure modes.** 429 RESOURCE_EXHAUSTED (rate/quota) and 503 UNAVAILABLE ("high demand", Gemini's own capacity, independent of usage). Caching helps the 429s, not the 503s. Both fall back to teasers gracefully → build stays green. (See #13 for a correction to the specific quota numbers.)
9. **Startups is ALWAYS processed last, so it ALWAYS gets starved without caching (Session 11).** Order is PM → GTM → AI → Startups; quota's spent by the time Startups fires. Deterministic, not the SaaStr teaser-trap (the build log's skip-reason `skipped-error`, not `skipped-too-thin`, disproved that). Phase 2 caching is the fix. Lesson: read the log's skip-reason, don't guess.
10. **Cache key = normalized URL — chosen by EVIDENCE, not assumption (Session 12).** A throwaway `probe_urls.py` fetched all 22 article feeds twice and checked for URL wobble, query-identity risk, and GUID usability. Result: **22/22 STABLE** — zero wobble, zero query-identity risk, and not a single feed link even contains a `?`. So the key is the URL with scheme+host lowercased and the query string stripped (`normalize_url()` in `cache.py`). The query-strip is a no-op on today's data but is kept as cheap defense against a feed that later adds tracking params. A GUID/hash fallback chain was considered and REJECTED as over-engineering (YAGNI) since no feed needs it. Known weak spot: two thin feeds (Stuart Balcombe = 1 entry, Aakash Gupta = 4) were too sparse to sample collisions confidently; if either ever misbehaves, look here first. (`probe_urls.py` was a scratchpad — deleted after use, never committed.)
11. **Cache value = versioned object, not a bare string (Session 12).** Each entry is `{summary, model, prompt_version, created_at}`. `get_cached` returns a hit ONLY if both `model` AND `prompt_version` match the current build's values; otherwise it's a miss and the item is re-summarized. `PROMPT_VERSION = 1` lives in `summaries.py` next to `PROMPT_TEMPLATE`. WHY: the open Phase-1 note to tighten the prompt to 2 sentences would otherwise leave every already-cached summary frozen in the old long format forever. Bumping `PROMPT_VERSION` (or changing `MODEL`) now auto-invalidates stale entries. Added upfront because the structure is greenfield (one dict vs. a later migration of a live cache). Decided over the "ship bare strings, manually nuke the cache on every prompt change" alternative.
12. **Local-build discipline = CI-only write-guard, replacing the planned git-restore (Session 12).** The build calls `save_cache()` ONLY when `os.environ.get("GITHUB_ACTIONS") == "true"`. So the scheduler is the sole writer; local builds READ the cache (fast, no wasted quota) but never WRITE it → `summary_cache.json` never appears in a local `git status`, so there's nothing to restore and no `.gitignore` entry needed. This supersedes the original Phase-2 plan to `git restore` the cache locally like `docs/<date>.html`. (Note: GitHub Actions can't touch the local machine anyway — an early "use Actions to avoid local updates" idea was a wrong-computer category error.) Verified: two local builds produced NO cache file (`Test-Path → False`).
13. **[PARTIALLY SUPERSEDED BY #16 — the "5 RPM is trustworthy" claim below no longer holds; treat ~10 RPM published + your own 429 body/dashboard as ground truth.]** **Correction to the Gemini quota numbers — "20/day" was an unverified inference (Session 12).** Claude Code claimed run #11 died on a "free-tier daily cap of 20 requests." That number is NOT from an error body — it was inferred — and contradicts published limits (post-Dec-2025 free-tier `gemini-2.5-flash` is documented around 10 RPM / 250 RPD, some sources 1,500 RPD; nobody publishes 20/day). The project's real **5 RPM** figure (from Session 11) is trustworthy because it came from an actual 429 quota-name in a log. The simplest explanation for run #11's all-error result: two full local builds earlier that evening + the manual CI run fired ~29 calls in a short window, saturating the 5 RPM rolling limit — no mystery daily cap required. To confirm which limit a 429 hit, read the error body (it distinguishes RPM / RPD / TPM). Do NOT log "20/day" as fact. Lesson reaffirmed: read the log, don't infer; and search for current provider limits rather than trusting a single confident claim.
14. **Phase 2 payoff confirmed by log line, not by cache file alone (Session 13).** The pulled `summary_cache.json` (10 entries: 7×07-15, 3×07-16, all SaaStr new on the 16th) was *suggestive* but genuinely ambiguous — an unchanged-but-cached article and an errored-and-teaser'd article both leave NO new cache entry, so the file cannot distinguish a hit from a fallback. The proof only came from the `[summaries]` log lines: July 16 `#13` showed `6 cache-hit · 3 API call(s) · 0 skipped-error` vs July 15 `#12`'s `0 cache-hit · 9 API call(s) · 2 skipped-error`. Reaffirms the standing rule: green build (or a plausible-looking artifact) ≠ done — read the log's own counters. Caveat banked: the 6 hits partly reflect PM/GTM/AI feeds not turning over between the two days; churny news days will show fewer hits + more calls, and cold-start still fires the full ~9. Caching cut *volume*, not the per-minute *rate ceiling* — keep `SUMMARIES_PER_SECTION = 4` and the teaser fallback through cold-start.
15. **Phase 3 (scrape teaser-only feeds) KILLED on evidence, not built (Session 14).** A throwaway probe (`probe_teasers.py`, deleted after use per Decisions Log #5) reused the real pipeline logic — `summaries.entry_source_text` + `MIN_SOURCE_CHARS = 300` — and sampled all 22 article feeds live. Result: 22/22 FULL-BODY, 0 teaser-only, 0 mixed; only 7/375 items (2%) under threshold, scattered one-off link/note posts across 4 feeds. The phase's whole premise (feeds shipping only teasers) is false for the current list, so per-site scraping has no work to justify its fragility. Measure-first (Decisions Log #1) paid off — it prevented an entire wasted phase. Caveat: this is a snapshot; if a feed later goes teaser-only the existing teaser-fallback keeps the build green, and we'd handle it as a targeted fix. Also logged: v4 (live news feed) as a CANDIDATE needing a scoping decision (news-wire sources + hourly cron shifts the project toward "news aggregator" — an identity call to make before building).
16. **Summary pacing bug fixed + Gemini rate-limit number settled for good (Session 15).** The summarize loop paced at `SLEEP_SECONDS = 4` (~15 calls/min) with NO retry/backoff — roughly 3× over the real free-tier limit; overflow calls just became silent teaser fallbacks. Fixed to `SLEEP_SECONDS = 12` (5 calls/min) — commit `c481f4e`. On the recurring "what's the RPM" confusion: current published Gemini 2.5 Flash free-tier is ~10 RPM / 250 RPD (some sources say 15; Google cut free quotas 50–80% on 2025-12-07, hence the drift; varies by region + account). The old logged "5 RPM" was likely the Dec-2025 transition or a rolling-window burst. STANDING RULE: do NOT trust memory, blogs, or the code comment for this — ground truth = the 429 error body (it names RPM/TPM/RPD) + the Google AI Studio dashboard. 12s is safe even under the pessimistic 5 RPM. This is a bandaid; #17 is the cure.
17. **Fix ordering for summarization throughput — do NOT reorder (Session 15).** (1) honest pacing [done]; (2) exponential backoff on 429 [next — permanent fix]; (3) raise `SUMMARIES_PER_SECTION` [only after backoff]. Bumping the cap before backoff widens the cold-start burst against a limit with no retry → reintroduces the exact Startups starvation Phase 2 relieved. Also clarified: Startups starves because the rate limit is GLOBAL (rolling per-minute across all sections) and Startups is simply LAST in `TOPIC_ORDER` (PM→GTM→AI→Startups) — positional, not a combined-"ALL"-section bug. Optional cheap mitigation: rotate/reverse section order per day so Startups isn't always the one holding the empty bag.
18. **Editorial reskin — design decisions locked (Session 17).** Direction: editorial base + boxed cards + red as the single accent, chosen over minimal/bold for the strongest portfolio story. Concrete calls: (a) filters are three segmented toggles on ONE row — topic (AI·PM·GTM·Startups), format (Articles·Videos), and mode (sun·moon), split by neutral dividers; NO "All" buttons (the × per group is the reset, default = everything) — this killed the double-"All" that annoyed Prady. (b) Selection = the segment FILLS solid (black in light `#1c1a17` / white in dark `#efe8da`), label flips to page-bg colour for contrast, unselected labels stay red, only the outer bar border is red. (c) A sliding-highlight-pill version was built and REJECTED: a free-floating pill positioned by pixel math can't align to the segment cleanly → visible gap + red corner leak; filling the segment itself is pixel-exact. Consequence: the page now has zero animation (the earlier scoped "pill-slide motion exception" no longer applies). (d) Light/dark is a manual toggle (no-flash inline script, localStorage), NOT auto `prefers-color-scheme` — though the script still falls back to OS pref on first visit. (e) Dark bg is deliberately WARM off-black (`#161410`), not pure black, to pair with the Georgia serif; Prady confirmed he prefers the warm tint. (f) `taste-skill` (github.com/Leonxlnx) was evaluated and NOT used: its own SKILL.md scopes it to landing-pages/portfolios (explicitly not data lists), it's motion-first (the fenced-out thing), and the locked spec left nothing for its brief-inference to do; the useful audit items were folded into the prompts directly instead. Method lesson banked: for look-and-feel work, build an interactive inline prototype and get sign-off BEFORE writing the Claude Code prompt — describing craft in words underspecified it twice (two wrong builds) before the prototype-first loop converged.

---

## KEY ARCHITECTURE FACTS (context for every future decision)

- **Pipeline is now stateful in ONE place.** It still rebuilds pages from scratch daily, but `summary_cache.json` (keyed on normalized URL, versioned entries) persists between runs. Phase 2 is the first deliberate break from statelessness.
- **Archive = capture-date, not publish-date.**
- **Live page filtered to 15 days; snapshots never filtered.**
- **Scheduler commits to origin/main ~7am Boston daily** — always `git fetch`/`git pull` at session start; local drifts behind each morning. As of Session 12 the scheduler commits `summary_cache.json` alongside `docs/`.
- **Files:** `build_page.py` (pipeline + page builder + summary/cache orchestration), `sources.py` (FEEDS list only, no imports), `fetch.py` (feed fetch + health logic), `summaries.py` (LIVE summarization helper — prompt, `MODEL`, `PROMPT_VERSION`, longer-field extraction), `summarize.py` (original dormant POC, unchanged), `cache.py` (pure versioned-cache module — `normalize_url`, `load_cache`, `get_cached`, `set_cached`, `save_cache`), `summary_cache.json` (the persisted cache — scheduler-owned, do NOT git-ignore, do NOT restore locally). `.env` holds the Gemini key locally (git-ignored, verified never leaked); CI uses the `GEMINI_API_KEY` repo secret.
- **Cache write-guard:** `save_cache()` runs only when `GITHUB_ACTIONS == "true"`. Scheduler writes; local reads only.
- **`gemini-2.5-flash`** via `google-genai` (`from google import genai`). Project's observed limit **5 RPM** (real, from a log); published free-tier RPD figures vary (~250–1,500) — see Decisions Log #13. 429 (rate/quota) + 503 (capacity) both fall back to teasers.
- **Summaries are LIVE-index only** — snapshots stay raw v1. `SUMMARIES_PER_SECTION = 4`.

---

## HOW TO USE & MAINTAIN THIS DOC

- **At session start:** read WHERE WE ARE + the current phase's exit criteria. Expect BOTH this roadmap and the latest handoff to be attached; if either is missing, ask for it before doing project work.
- **When a phase completes:** flip its status, move a one-line summary into DONE, update "Last updated" + current commit.
- **When a real decision is made:** add it to the Decisions Log with the *why*.
- **When the plan changes:** edit the phases directly.
- **This doc ≠ the handoff.** Roadmap = durable "where we're going." Handoff = disposable "where we stopped, resume here." Keep both.
