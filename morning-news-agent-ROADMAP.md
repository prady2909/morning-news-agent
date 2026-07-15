# Morning News Agent — Product Roadmap

*Living document. This is the durable spine of the project — the north star we check every decision against. The per-session handoff docs answer "where exactly did we stop"; THIS answers "where are we going and why." Update it whenever a phase completes, a decision is made, or the plan changes.*

**Last updated:** 2026-07-14 (Session 12)
**Current commit:** `4a83821` (last human commit — CI cache persistence). Scheduler/bot has since auto-committed the initial empty cache + docs (`198fabe`). Roadmap commit pending this session close.

---

## THE GOAL (the north star — check every decision against this)

A self-updating morning newspaper: a single page that, every morning, shows me the freshest, most useful content across the four topics I care about — **PM, GTM, AI, Startups** — pulled from sources I trust, with AI-generated summaries so I can decide what's worth my time without opening ten tabs.

**The finish line:** I open one page each morning, see recent article summaries that let me grasp the gist in seconds, plus video links for things I'd rather watch. No manual curation. It maintains itself.

---

## WHERE WE ARE RIGHT NOW

**v1 is complete and live** at `prady2909.github.io/morning-news-agent/`.

**v3 Phase 2 (caching) — CODE SHIPPED, live payoff pending verification.** As of Session 12 the entire caching layer is built, committed, and green: a standalone `cache.py` module, wiring into `build_page.py`/`summaries.py`, and a workflow change so the scheduler commits `summary_cache.json` back to origin each run. The write/commit/persist plumbing is verified in the wild (the file exists in the repo, bot-committed, correct structure). The ONLY thing not yet seen with our own eyes is a real cache HIT — that requires a run that successfully summarizes first, which is pending a clean Gemini quota window (see Decisions Log #13).

**Next up:** verify the live payoff (first HIT) on the next successful scheduler run, then v3 Phase 3 (scrape teaser-only feeds).

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
- **v3 Phase 2 — Caching CODE SHIPPED (Session 12)** — three commits, one clean phase, verified one hard thing at a time:
  - `cache.py` (commit `44948b6`) — standalone, pure module. Reads/writes `summary_cache.json`, keyed on normalized URL, versioned entries. 6/6 self-test PASS (empty-miss, round-trip hit, prompt-version gate, model gate, URL normalization, corrupt-file safety). No network, no imports of project code.
  - Cache wiring (commit `eab195c`) — `add_summaries(items, client, cache)` threads the cache dict as an argument (no global); loaded once in `main()`; checked at the top of the item loop (hit → reuse, no API call, no sleep); `set_cached` fires ONLY on the success path; CI-only write-guard on `GITHUB_ACTIONS == "true"`.
  - Workflow persistence (commit `4a83821`) — `.github/workflows/daily-build.yml` commit step now stages `docs/ summary_cache.json` (was `docs/`); existing "nothing changed" guard preserved.
  - **Verified in the wild:** manual `workflow_dispatch` run #11 went green, and `summary_cache.json` now exists in the repo as a bot-committed file. Its `{}` (empty) content is CORRECT for that run — every summary 429'd (quota already spent by earlier local tests), and only successes are cached, so nothing was stored. Plumbing proven; live HIT still pending (see Phase 2 exit criteria + Decisions Log #13).

---

## THE PLAN — v3 AI Layer (4 phases)

*Discipline: one phase at a time. Each phase is independently shippable and must be verified by ground truth before advancing. Do NOT bundle phases — debugging two hard things at once is how this stalls.*

### Phase 0 — Verify `summarize.py` still works against current Gemini ✅ DONE (Session 10)
**Status:** ✅ Done

### Phase 1 — Wire summaries into the build (full-body article feeds) ✅ DONE (Session 10, commit `e76dff2`)
**Status:** ✅ Done
**Open polish note (not a blocker):** summaries run a touch long (4–6 lines); tighten the prompt to a hard 2-sentence cap later. NOTE: doing this means bumping `PROMPT_VERSION` (see Decisions Log #11) so the cache re-summarizes old entries under the new prompt.

### Phase 2 — Caching (the stateful piece) 🟡 CODE SHIPPED — live payoff pending (Session 12)
**What shipped:** `cache.py` + wiring + workflow persistence, all committed & green (see DONE). Key = normalized URL (Decisions Log #10). Value = versioned object (Decisions Log #11). Local discipline solved via a CI-only write-guard, NOT the git-restore originally planned (Decisions Log #12).
**Still to verify (the one thing we haven't seen):** a real cache HIT. This needs a run that summarizes successfully first (to populate the cache), then a subsequent run that reads it. Run #11 came back empty because its quota was already spent by same-evening local tests — expected, self-heals.
**Cold-start caveat (confirmed in practice):** the first populated build still fires real API calls; caching cuts *volume*, not the per-minute *rate*, and does nothing for 503s. Keep the graceful teaser fallback and keep `SUMMARIES_PER_SECTION = 4` at least through cold-start.
**Exit criteria (partially met):** ✅ article summarized once isn't re-summarized (logic proven by self-test + wiring); ✅ cache persists across runs (file committed by CI); ⬜ 429s measurably drop and Startups stops getting starved under normal daily volume — PENDING first live HIT. Once a scheduler run shows `[summaries] … cache-hit > 0 …` with fewer API calls and Startups summarized, flip this to ✅.
**Once fully verified:** `SUMMARIES_PER_SECTION = 4` can likely be raised (keep SOME cap through cold-start).

### Phase 3 — Scrape teaser-only article feeds ⬜ NEXT (after Phase 2 live-verified)
**Why last (of the article work):** Fragile, per-site, breaks when sites change. Only worth it once summarization + caching are proven. Fetches full article text for feeds that only provide a teaser in RSS, so those items can also be summarized.
**Exit criteria:** Teaser-only feeds get fetched and summarized like full-body ones, with graceful failure when a scrape fails (don't break the build).
**Status:** ⬜ Not started

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
13. **Correction to the Gemini quota numbers — "20/day" was an unverified inference (Session 12).** Claude Code claimed run #11 died on a "free-tier daily cap of 20 requests." That number is NOT from an error body — it was inferred — and contradicts published limits (post-Dec-2025 free-tier `gemini-2.5-flash` is documented around 10 RPM / 250 RPD, some sources 1,500 RPD; nobody publishes 20/day). The project's real **5 RPM** figure (from Session 11) is trustworthy because it came from an actual 429 quota-name in a log. The simplest explanation for run #11's all-error result: two full local builds earlier that evening + the manual CI run fired ~29 calls in a short window, saturating the 5 RPM rolling limit — no mystery daily cap required. To confirm which limit a 429 hit, read the error body (it distinguishes RPM / RPD / TPM). Do NOT log "20/day" as fact. Lesson reaffirmed: read the log, don't infer; and search for current provider limits rather than trusting a single confident claim.

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
