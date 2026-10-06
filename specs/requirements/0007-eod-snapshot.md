# Gate 1 — Requirement Spec `0007-eod-snapshot`

**Status:** `AUTHORED 2026-10-06 — awaiting Gate 1 user approval (no code, no Gate 2`
`until signed off)`
**Date:** 2026-10-06
**Consumes:** specs `0003-pattern-search-core` (distance/score/forward payload),
`0005-regime-conditioning` (query regime + filtered analogs — its wrapper is the
only search entry point), `0004-outcome-stats` (reducer over the analog list).
Specs `0001`/`0002` supply and refresh the store but are **not modified and not
wired** (see §3).
**Preceded by:** user-directed scope instruction ("compose 0003+0004+0005 into
static JSON per BRD §4.2"); design choices made under it are surfaced as §7 frozen
decisions for approval.

---

## 0. Gate 1 User-Value Flag

> **No waiver needed.** This is the artifact BRD §7.1's serving SLAs are written
> for: **≤ 15 ms API response** and CDN-served static JSON at **$0 egress**
> (BRD §4.1/§4.2: *"dump results to flat files/…, serve static JSON"*) are only
> achievable by pre-computing search results into files. It is also the exact seam
> the Phase-1 dashboard (spec 0008) will render — without it the dashboard either
> pays live compute per view or does not exist.

---

## 1. User Value Rationale (DIRECT)

- **Instant, load-independent results:** the snapshot converts the search into a
  static read — page loads are served by Nginx/CDN, so 100 concurrent traders
  cost the same as 1 (BRD §4.1's *pre-computation over live complexity*). Repeat
  views are free; the ≤300 ms page-load budget (BRD §7.1) becomes a file fetch.
- **The BRD's own architecture:** Phase-1 scope (BRD §7.2) is *engine + artifact*
  on `^NSEI`; the nightly-batch → flat-file → static-serve chain is the product's
  stated cost model (single $10–20 VPS, zero cloud bills).
- **Freshness a trader can trust:** one deterministic file per store state,
  rewritten wholesale after EOD — "as of" is the store's last session, never a
  stale cache of an in-session compute.

---

## 2. What Is Needed (Scope)

### 2.1 Public seam — one function (frozen for golden evals)

```
build_snapshot(symbol, parquet_dir, out_dir) -> dict   # the manifest
```

- All three arguments required, **no defaults**; `symbol`/`parquet_dir` follow
  0003's contract (reads `{parquet_dir}/{symbol}.parquet`).
- **Module constants** (snapshot policy, not tier policy — tiers truncate in the
  UI, per 0003 frozen decision #5):
  - `WINDOWS = (5, 10, 15, 30, 60)` — BRD §6.2.2's selector set (5/10/15/30) plus
    Pro's 60-bar upper bound (BRD §2.2).
  - `K = 10` — the Pro-tier cap; Free's top-3 is a UI truncation of the same file.
- Writes exactly one file: `{out_dir}/{symbol}.json`, creating `out_dir`
  (with parents) if missing. Full rewrite every run (derived state — same posture
  as 0001's Parquet).

### 2.2 Output document (frozen schema)

```jsonc
{
  "schema": "dtwmagic.api.v1",
  "symbol": "^NSEI",
  "bars": 4673,
  "last_date": "2026-10-05",
  "regime": { "trend": "bearish", "volatility": "normal",
              "cell": "bearish-normal", "p252": 0.5476190476190477 },
  "windows": {
    "5":  { "L": 5,  "k": 10, "analogs": [ /* 0003 payload dicts */ ],
            "summary": { "n": …, "horizons": [1,…,10], "cone": {…},
                         "positive_frequency": {…}, "mae": {…}, "mfe": {…} } },
    "10": { … }, "15": { … }, "30": { … },
    "60": { … }
  }
}
```

- `regime` is computed **once** (it is query-session state, L-independent) and
  embedded verbatim from 0005's payload block.
- Each `analogs` list is `search_analogs_regime(symbol, L, K, parquet_dir)["analogs"]`
  verbatim — 0003's frozen item keys (`date/distance/score/close/forward`), order
  and values untouched; `k` records the requested cap (10).
- `summary` is `summarize_analogs(analogs)` verbatim when the list is non-empty.

### 2.3 Semantics pinned by real edge cases

- **Zero-pool days:** `summarize_analogs([])` **raises** (`analogs must be a
  non-empty list`) and 0005 legitimately returns `analogs: []` on ~52 historical
  dates (fixture). Contract: an empty window block gets **`"summary": null`** —
  the regime block and `analogs: []` still ship; the batch never crashes on a
  rare-regime day (BRD-honest: "no in-regime precedent" is a valid snapshot).
- **JSON round-trip of horizon keys:** 0004's dict keys are python `int`
  (`cone[5]`); JSON object keys are strings, so the file carries `"1"…"10"`
  while `summary.horizons` stays `[1,…,10]` (0004's documented ceiling becomes
  this spec's explicit contract for consumers).
- `bars`/`last_date` come from the store read-back (0001 manifest semantics).

### 2.4 Serialization & determinism (frozen)

- `json.dump(doc, fh, ensure_ascii=False)` + trailing `"\n"`, utf-8, **no
  `indent`, no `sort_keys`** — dict insertion order (language-guaranteed) gives
  `5,10,15,30,60` and byte-stable output. No wall-clock, no randomness: the same
  store state yields **byte-identical** files across runs (Gate 2 pins the
  fixture file's sha256). `last_date` is the freshness stamp — not `generated_at`.
- Overwrites are whole-file; no append, no partial patching.

### 2.5 Error contract

| Condition | Behavior |
|---|---|
| Store missing | `ValueError`, keyword `store` (0005's pass-through) |
| Store < 252 rows / unclassifiable query | `ValueError`, keyword `regime` (0005's pass-through) |
| `out_dir` missing | **created** (`mkdir(parents=True, exist_ok=True)`) |
| I/O failure while writing | plain `OSError` propagates (not a validation error) |

- `window`/`K`/`bars` cannot fire (constants are valid and the pass-through runs
  per call); any validation that does surface is 0005's, unchanged.

### 2.6 Dependencies

**None new** — stdlib `json` + already-installed pandas/pyarrow.

### 2.7 Hermetic evals & performance

- Eval builds the store from the sha-guarded 0001 fixture into a tmp dir, calls
  `build_snapshot`, and asserts on `json.load` of the file. **No network**;
  store Parquet sha unchanged (read-only over 0001's output).
- Sanity (not an SLA): `^NSEI` (5 windows × ~71 ms + summaries) completes in
  **≲ 2 s** on the dev machine.

---

## 3. What Is NOT Needed (Negative Scope)

- **No scheduler / cron / CLI / HTTP server / Nginx or CDN config** — the nightly
  *job* wiring (0001+0002+0007 end-to-end) is deferred with 0002's documented
  ceiling; this spec is the artifact builder the job will call.
- **No 0002 fetch integration** — input is an existing store; freshness stays
  0002's concern (the user's composition list is 0003+0004+0005).
- **No multi-symbol batch loop** — one symbol per call (0003 posture); Phase-2
  batch orchestration + BRD §4.1's 90 s budget arrive with F-06.
- **No full 56-value L grid** (5..60) — five windows now (§7 #2); grid expansion
  is a measured-cost decision for Phase 2.
- **No tier logic** (Free top-3 truncation is the UI's), **no SQLite**, **no
  compression/gzip**, **no atomic-replace choreography** (§6 ceiling), **no live
  compute fallback**, **no dashboard rendering** (spec 0008), **no changes to
  0003/0004/0005 math, payloads, or files** (their frozen evals are regression
  gates).

---

## 4. Acceptance Summary (for Gate 2 authoring; the test spec freezes the details)

- Schema: top-level keys exactly `{"schema","symbol","bars","last_date","regime","windows"}`;
  `windows` keys exactly `{"5","10","15","30","60"}`; each block keys exactly
  `{"L","k","analogs","summary"}`; `regime` block equals 0005's output for the
  same store (p252 pin `0.5476190476190477` ≤1e-15).
- Content: every window's `analogs` deep-equals a direct
  `search_analogs_regime(symbol, L, 10, …)` call; `summary` deep-equals a direct
  `summarize_analogs(analogs)` call (recomputed in the test), with JSON horizon
  keys `"1"…"10"` and `horizons` ints.
- Anchors: fixture top analogs per window re-pin the known values (L=10
  `2012-05-14 → 0.73704193241622`, L=60 `2012-06-04 → 4.612532697912032`);
  **L=5/15/30 top-1 and the fixture file sha256 are probe-verified before Gate 2
  freeze** (0003/0005 posture).
- Zero-pool path: the 416-row slice store (2009-06-04) produces all five windows
  with `analogs: []` and `summary: null`, regime intact, no exception —
  probe-verified before freeze (0005 showed L=10/L=60 empty; L=5/15/30 confirmed
  at probe time).
- Determinism: two runs on the same store are **byte-identical** (sha256 equal);
  a changed store changes the file.
- Hermetic: socket guard on; store sha unchanged after the call; `out_dir` auto-created.
- Perf: whole snapshot ≲ 2 s (best-of-3, generous); full suite (98 existing tests)
  stays green unmodified.

---

## 5. Architecture Alignment (Kailash Nadh)

- **One pure-ish function, stdlib only** — `json` is the standard library doing
  the job; no framework, no templating, no class (rung 3 + rung 6).
- **Composition only:** the snapshot calls 0005's wrapper per window and 0004's
  reducer per non-empty list — zero re-implementation of search, regime, or stats.
- **Pre-computation over live complexity, exactly BRD §4.1:** batch cost is paid
  once after market close; serving is a static file read.

---

## 6. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is five fixed windows; upgrade path is the full 5..60 grid
  once a measured Phase-2 budget exists (file size × 56).`
- `# ponytail: ceiling is plain open-write; upgrade path is os.replace atomic
  swap if a reader ever observes partial files.`
- `# ponytail: ceiling is ^NSEI-style symbol in the filename (^ is URL-unsafe);
  upgrade path is a URL-alias map when the dashboard serves it.`
- `# ponytail: ceiling is single-process per-symbol build; upgrade path is the
  rank-only seam (0006 §6) + multiprocessing for BRD §4.1's 2,000-stock <90 s.`
- `# ponytail: ceiling is no gzip; upgrade path is letting Nginx/CDN compress.`
- Inherited (0004): unweighted aggregates, linear quantiles, T+10 horizon cap.

---

## 7. Frozen Decisions (from the authoring session, per user instruction)

| # | Decision | Choice |
|---|---|---|
| 1 | Composition boundary | **0003+0004+0005 over an existing store**; 0001/0002 untouched; end-to-end nightly wiring deferred with 0002's ceiling |
| 2 | Window set | **`WINDOWS = (5,10,15,30,60)` module constant** — BRD §6.2.2 selector + Pro's 60; full grid deferred (measured Phase-2 decision) |
| 3 | K | **`K = 10` constant** — superset; Free top-3 truncation stays in the UI (0003 frozen #5) |
| 4 | Empty analogs | **`summary: null`** — 0004 raises on `[]` and ~52 fixture dates are zero-pool; the batch must survive them (pin surfaced here because it silently changes a failure into data) |
| 5 | Regime placement | **Top-level, computed once** — L-independent query-session state, verbatim 0005 block |
| 6 | Determinism | **Byte-identical reruns** — no wall-clock fields; `last_date` is freshness; exact dump args frozen in §2.4 so Gate 2 can pin a file sha256 |
| 7 | Horizon keys | **`"1"…"10"` strings in JSON** — 0004's ceiling made an explicit consumer contract rather than "fixed later" |
| 8 | Seam shape | **`build_snapshot(symbol, parquet_dir, out_dir) -> manifest`**, no defaults, no scheduler/CLI/HTTP — the EOD job's future call site |

---

## 8. Gate 1 Sign-Off

- [ ] **User approves** this requirement spec (incl. the §2.2 schema, §2.3
      `summary: null` edge contract, §2.4 serialization freeze, and the §7
      decisions) → agent may author Gate 2 test spec
      `specs/tests/0007-eod-snapshot.md`.
- [ ] **No new dependency requested** (§2.6) — nothing to approve.

**STOP:** No Gate 2 or Gate 3 work proceeds until the box above is checked by the
user. The test spec is **IMMUTABLE once approved**; Gate 3 (code) still requires
that separate approval.
