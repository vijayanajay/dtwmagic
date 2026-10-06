# Gate 1 — Requirement Spec `0005-regime-conditioning`

**Status:** `APPROVED — Gate 1 signed off 2026-10-06 (user: “Approve Gate 1 for spec`
`0005”); Gate 2 test spec authored, awaiting freeze approval; Gate 3 not started.`
**Date:** 2026-10-06
**Consumes:** spec `0001-ohlcv-parquet-store` (store seam) and spec
`0003-pattern-search-core` (composed verbatim as the unfiltered pool; its frozen
signature and evals are **untouched**). Spec `0004-outcome-stats` is a downstream
consumer of the `analogs` sub-list and is unchanged. Spec `0002-eod-data-fetcher`
keeps the store fresh but is not on this spec's critical path.
**Preceded by:** grilling session (7 decisions, §7) + **two probe runs** against the
committed fixture — CSV parse and the production `build_store → read_parquet` path —
both producing bit-identical regime arrays and anchors (§2.2, §4).

---

## 0. Gate 1 User-Value Flag

> **No waiver needed.** This implements BRD **F-02 (2-Factor Regime Conditioning
> Filter)**, whose BRD §3 user value is stated verbatim: *"Prevents false historical
> analogies."* The BRD marks F-02 as Free (current regime only) / Pro (custom regime
> filters) — a priced feature, not internal plumbing.

---

## 1. User Value Rationale (DIRECT)

- **Why a paying trader cares:** spec 0003 answers *"has this shape occurred
  before?"* but ignores **when**. On the fixture's last session (2026-10-05, a
  bearish regime), the unfiltered eligible pool is dominated by bull-market
  episodes — `Bull-Low` alone is 1,334 of 4,402 eligible windows (30%). A trader
  shown a bull-market consolidation as "precedent" for price action under a
  bearish regime draws exactly the invalid conclusion BRD §3/F-02 exists to
  prevent: *"Comparing a bull-market consolidation with a bear-market crash leads
  to invalid conclusions."*
- **Accuracy is the trust primitive:** every downstream priced feature (F-03 cone,
  F-04 MAE/MFE, F-05 ghost overlay) is only worth paying for if the matched
  episodes are **apples-to-apples** (BRD §1.3: *"under analogous market regimes"*).
  A dishonest zero-result day is also value: *"no in-regime precedent exists"* is a
  legitimate, decision-relevant search answer (frozen decision #4).

---

## 2. What Is Needed (Scope)

### 2.1 Public seam — one new pure function (frozen for golden evals)

```
search_analogs_regime(symbol, L, K, parquet_dir) -> dict
```

- Same four required arguments, same validation semantics as 0003 §2.1 (no
  defaults; tier policy lives in the UI).
- `search_analogs` from 0003 is **called, never modified or re-implemented**
  (0002's composition-over-re-implementation precedent): the wrapper requests the
  full unfiltered pool (`K = n` rows), then filters by regime.
- Returns a **two-key dict**:

```python
{
  "regime": { ... },   # query-level block — ALWAYS present, even when analogs == []
  "analogs": [ ... ],  # list[dict], exactly 0003 §2.4 payload dicts
}
```

### 2.2 Regime classification math (probe-pinned, frozen)

All computed from the store's own OHLC (read via `pd.read_parquet`, 0001 contract).
Let `n` = rows, ascending by date. For every session `t`:

1. **EMA trend:** `EMA50`, `EMA200` = pandas `ewm(span=S, adjust=True).mean()` of
   close.
   - `bullish` iff `c_t > EMA50_t and EMA50_t > EMA200_t`
   - `bearish` iff `c_t < EMA50_t and EMA50_t < EMA200_t`
   - `neutral` otherwise (exact ties are neutral — BRD §5.3's strict inequalities)
2. **True range:** `TR_0 = high_0 − low_0`; for `t ≥ 1`,
   `TR_t = max(high−low, |high−c_{t−1}|, |low−c_{t−1}|)`.
3. **ATR14 (Wilder):** `ewm(alpha=1/14, adjust=False).mean()` of TR.
4. **Normalized ATR:** `NATR_t = ATR14_t / close_t`.
5. **Percentile rank:** `p252_t = pd.Series(NATR).rolling(252).rank(pct=True)_t` —
   trailing 252 sessions **including `t`**; average rank for ties; **NaN for
   `t < 251`** (the 252-day warmup — probe: first classified session is index 251,
   2008-09-19).
6. **Volatility bins — disjoint, exact edges pinned** (BRD §5.3's "0–33rd /
   33rd–66th" wording overlaps at the edges; 37 fixture rows sit exactly on ⅓ or
   ⅔, so this rule is load-bearing):
   - `low` iff `p252 ≤ 1/3`; `normal` iff `1/3 < p252 ≤ 2/3`; `high` iff `p252 > 2/3`
7. **Cell:** `cell_t = f"{trend}-{volatility}"` with `trend ∈ {bullish, bearish,
   neutral}`, `volatility ∈ {low, normal, high}` → **9 cells** (BRD §5.3 literal;
   `cell_t is None` iff `t < 251`).
8. **Query regime** = `cell_{n-1}` (the store's last session).

**Why exactly these definitions (probe evidence, both runs):** ATR method choice
flips the volatility bin on **16%** of sessions (705/4,409) and rank-window choice
on **7.4%** (329/4,421) — both must be frozen; EMA `adjust` flips only 36 sessions
(35 inside warmup), pinned to pandas' default anyway. Today's cell is `bearish-normal`
under **all 8** definition combinations (EMA-adjust × ATR-method × rank-window), so
the anchor is not a coin flip.

### 2.3 Hard filter rule (BRD §5.3, frozen)

A candidate from 0003's eligible set (`s ∈ [0, n − 2L − 10]`, window end
`τ = s + L − 1`) survives the regime filter iff:

```
cell_τ is not None   AND   cell_τ == cell_{n-1}
```

- **Hard filter only.** Distance and score are byte-identical to what 0003 returns
  for the same item; ordering (distance asc, earlier date on ties) is preserved.
  **Regime never enters the score** (BRD §5.4's regime-aware Match Quality Score is
  a future spec — frozen decision #2).
- **Strict, no fallback** (frozen decision #4): no pool widening, no degradation
  ladder, no error on empty. In-regime pool size may be `< K` (return all) or
  **`0`** (return `"analogs": []` — legitimate per §1).
- Candidates with `τ < 251` are **silently excluded** (regime unknowable), never an
  error; the query itself must be classifiable (§2.5).
- Fixture reality (probe): in-regime pool for today = **131** (L = 5/10/15/30),
  **128** (L = 60) out of ~4,400 eligible; across history the strict pool is 0 on
  **52** days (L=10) / **132** days (L=60), and `< K=10` on 3.8% / 5.8% of days.

### 2.4 Result payload (frozen keys)

```python
{
  "regime": {
    "trend": "bearish",          # "bullish" | "bearish" | "neutral"
    "volatility": "normal",      # "low" | "normal" | "high"
    "cell": "bearish-normal",    # f"{trend}-{volatility}"
    "p252": 0.5476190476190477,  # RAW percentile rank float; UI formats
  },
  "analogs": [ ...0003 §2.4 dicts verbatim: date, distance, score, close, forward... ],
}
```

- **Query-level block, not per-analog** — the label identifies the query session
  once, not each match; `regime` survives an empty `analogs` list, so the BRD
  §6.2.1 dashboard header (`HISTORICAL REGIME: …`) can explain *why* results are
  empty on the 52 zero-pool days.
- **No `date` key** in `regime` (the caller knows the query session; snapshot
  shape belongs to spec 0006).
- **0003's payload keys are not amended.** 0003's frozen eval
  (`test_t001_payload_contract`) pins `set(item) == {"date", "distance", "score",
  "close", "forward"}` exactly — amending items would force a revision of a frozen
  test spec to make new code convenient, which this protocol forbids without
  explicit user direction. This realizes the *intent* of grilling decision #5
  (label reaches the payload; zero further 0003 churn) without one (§7 #5).

### 2.5 Error contract — `ValueError` naming the failed rule

| Condition | Error keyword |
|---|---|
| 0003's four checks, in its order: missing store / bad `L` / bad `K` / `n < 2L+10` | `store` / `window` / `K` / `bars` |
| Query session unclassifiable (`n < 252`, i.e. `n−1 < 251`) | `regime` |

- Validation order: 0003's checks fire first (pass-through), then the `regime`
  check. So a 40-row store at `L=10` reports `regime`, and `L=61` reports `window`.
- `in-regime pool < K` — **not an error** (0003's short-pool rule, inherited).
- `n ≥ 252` but no classifiable candidates (`n − L − 11 < 251`) — **not an error**:
  `regime` block present, `analogs: []`.

### 2.6 Dependencies

**None new.** pandas + pyarrow already installed from spec 0001.

### 2.7 Hermetic evals & performance

- Golden evals build the store from the **committed 0001 fixture** (sha256-pinned
  in both 0001 specs) via `build_store` into a tmp dir; **no network** (0001's
  socket-guard rule). No new fixture.
- The test's reference implementation computes cells **literally in the test**
  (0003 §0 freeze-3 pattern: never imports classification code from `src/`), so
  implementation and reference cannot self-confirm.
- Sanity (not an SLA): fixture (4,673 rows) at `L=10` completes **≲ 1 second**
  (probe runs, including full-history starvation scans, were sub-second).

---

## 3. What Is NOT Needed (Negative Scope)

- **No changes to `search_analogs`, `summarize_analogs`, or the store format** —
  specs 0001–0004 sources, payloads, and frozen evals stay green and untouched;
  the full 72-test suite is a regression gate for this spec.
- **No regime in the score / no Match Quality Score rework** (BRD §5.4 mapping is
  a future spec; probe recorded that fixture scores top out ≈ 63.7).
- **No custom regime filters** (Pro tier, BRD §2.2) — the query regime is always
  the store's last session; Free/Pro filter UI comes later.
- **No standalone public classifier API** — one seam (grilling option C was
  rejected); classification helpers are module-private.
- **No DTW / Sakoe-Chiba, no overlapping-analog dedup, no F-07 channels.**
- **No UI, no pipeline/CLI, no static JSON snapshots, no SQLite, no cron, no
  multi-symbol batch, no screener (F-06)** — spec 0006+ territory.
- **No precomputed regime column in the Parquet store** (would touch 0001's
  frozen contract), **no new fixture, no trading calendar, no writes.**

---

## 4. Acceptance Summary (for Gate 2 authoring; the test spec freezes the details)

- **Fixture anchors (verified twice: CSV path and production `build_store →
  read_parquet` path, bit-identical):**
  - query cell `bearish-normal`, `p252 == 0.5476190476190477` at 2026-10-05;
  - in-regime pools **131 / 131 / 131 / 131 / 128** for L = 5 / 10 / 15 / 30 / 60;
  - 9-cell occupancy over `[251, n)` = `bullish-low 1334, bullish-normal 718,
    bullish-high 410, bearish-low 83, bearish-normal 145, bearish-high 381,
    neutral-low 320, neutral-normal 420, neutral-high 611` (no empty cell, 0 NA);
  - warmup: first classified session = index **251** (2008-09-19); no returned
    analog has `τ < 251`.
- **Independent reference:** literal cell classification + filter in the test
  reproduces `analogs` (dates, order) exactly, and each item's `distance`/`score`
  equals `search_analogs`'s output for the same date — proving filter-only.
- **Soundness:** every returned `τ` shares the query cell; every excluded eligible
  cell differs or is `None`; `analogs` is an order-preserving subsequence of the
  full pool.
- **Empty path:** a query whose cell has zero eligible members returns the regime
  block with `analogs: []`, no exception (real fixture dates exist: the 52
  zero-pool days, e.g. 2009-06-04 at L=10).
- **Errors:** keyword cases for `window`, `K`, `bars`, `store`, and `regime`
  (251-row store) in the §2.5 order; short in-regime pool is not an error.
- **Composition:** `summarize_analogs(result["analogs"])` yields identical output
  to passing the unfiltered 0003 subset — 0004 unchanged and green.
- **Regression:** all 72 existing tests pass unmodified; two identical calls are
  content-equal; socket-guarded; ≲ 1 s at L=10 (L=60 exercised).

---

## 5. Architecture Alignment (Kailash Nadh)

- **Composition over re-implementation:** the filter is a thin wrapper around the
  proven 0003 seam — no second distance implementation to drift (0002 §2.4
  precedent). Vectorized cell classification is one array pass over the store.
- **One new file, two functions max** (`search_analogs_regime` + private helpers)
  — no classes, no framework, no new dependency (rung 6).
- **Honest cost:** the wrapper materializes the full pool then filters
  (`K = n`), and reads the Parquet twice per call (0003's read + the wrapper's
  regime read). At fixture scale both are sub-millisecond consequences; see §6.

---

## 6. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is per-call regime recomputation + full-pool filtering;
  upgrade path is a precomputed regime column / nightly batch (BRD §4.2) when the
  2,000-stock screener lands.`
- `# ponytail: ceiling is query regime = store's last session only; upgrade path
  is Pro custom regime filters (BRD §2.2).`
- `# ponytail: ceiling is fixed 252-day rank window and fixed 3x3 grid; upgrade
  path is configurable percentile lookback if users demand regime sensitivity.`
- `# ponytail: ceiling is two Parquet reads per call (0003's + wrapper's);
  upgrade path is a shared-dataframe seam, which would touch 0003's frozen
  signature — avoid until profiling forces it.`
- `# ponytail: ceiling is filter-after-full-ranking; upgrade path is a
  regime-indexed candidate structure if the batch pipeline shows real cost.`

---

## 7. Frozen Decisions (from pre-Gate-1 grilling session + probes)

| # | Decision | Choice |
|---|---|---|
| 1 | Next item after 0004 | **0005 F-02 regime conditioning** — regime semantics change every payload, so it lands before the snapshot pipeline (0006) and dashboard (0007) freeze/serve results |
| 2 | Filter vs score (BRD §5.3 vs §5.4 contradiction) | **Hard candidate-pool filter, §5.3** — score stays pure `100/(1+d)`; §5.4 regime-aware score is a later spec |
| 3 | Grid size (F-02 says "4 quadrants", §5.3 says 3×3) | **9 cells, §5.3 literal** — the normative math section supersedes the F-02 row's quadrant wording; `neutral` is a real trend state |
| 4 | Pool starvation policy | **Strict, no fallback** — `< K` or `0` results are valid search answers; widening reintroduces the false analogies F-02 exists to kill. Probe: 0-pool days really occur (52/132) |
| 5 | Payload seam (grilling chose "add regime label now") | **Realized as the wrapper's query-level `{"regime", "analogs"}` dict instead of amending 0003's items** — `test_t001` pins 0003's item keys exactly, so the literal reading of the grilling answer would require a user-directed revision of a frozen test spec (R3); the wrapper gets the label into the payload with **zero** 0003 churn and keeps the label alive on empty-result days. *Flagged as a deliberate deviation for Gate 1 approval.* |
| 6 | Definition freezes (from both probes) | EMA `adjust=True`; Wilder ATR (`ewm(alpha=1/14, adjust=False)`, `TR_0 = high−low`); rank window **includes** `t`; disjoint exact-edge bins; regime evaluated at **window end τ**; warmup floor **251** — each is a real fork (16% / 7.4% / 37-row edge effects) and today's cell is stable across all 8 combinations |
| 7 | Seam placement | **New `src/regime.py::search_analogs_regime`** — 0003's signature and behavior frozen and untouched; classification helpers private |

---

## 8. Gate 1 Sign-Off

- [x] **User approves** this requirement spec (incl. §2.2 probe-pinned definitions,
      §2.3 strict-filter rule, §2.4 payload keys, and the §7 #5 deviation from the
      literal grilling answer) → agent may author Gate 2 test spec
      `specs/tests/0005-regime-conditioning.md`. **(Approved 2026-10-06)**
- [x] **No new dependency requested** (§2.6) — nothing to approve. **(Approved
      2026-10-06)**

**STOP:** No Gate 2 or Gate 3 work proceeds until the box above is checked by the
user. The test spec is **IMMUTABLE once approved**; Gate 3 (code) still requires
that separate approval.
