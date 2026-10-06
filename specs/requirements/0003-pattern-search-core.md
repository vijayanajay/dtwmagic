# Gate 1 — Requirement Spec `0003-pattern-search-core`

**Status:** `APPROVED — Gate 1 signed off 2026-10-06 (user, incl. §2.3 disjointness
tightening); payload amended by user-directed Revision R2 (close key, 2026-10-06,
pre-0004); Gate 2 frozen, Gate 3 complete`
**Date:** 2026-10-06
**Consumes:** spec `0001-ohlcv-parquet-store` (store seam; evals build the fixture store
via `build_store`). Spec `0002-eod-data-fetcher` keeps the production store fresh but is
not on this spec's critical path.
**Preceded by:** grilling session resolving spec-0003 shape (see §7 Frozen Decisions)

---

## 0. Gate 1 User-Value Flag

> **No waiver needed.** This is the **first directly trader-facing spec**: it implements
> BRD **F-01 (Multi-Horizon Pattern Query Engine)** — the core act of the product
> ("has today's pattern occurred before?"). User value is direct under the Gate 1 rule.

---

## 1. User Value Rationale (DIRECT)

- **Why a paying trader cares:** specs 0001/0002 built a museum — a validated store
  with no way to ask it anything. F-01 answers the BRD §1.3 question that defines the
  product: *"Has this geometrical shape occurred before?"* Free tier (NIFTY 50, 10-bar
  window, top 3) and Pro (custom 5–60-bar windows, top 10) are both renderings of this
  one function (BRD §2.2, §3/F-01).
- **Monetization link:** the search result is the unit of value sold on every tier;
  F-03 (cone), F-04 (MAE/MFE), F-05 (ghost overlay) and F-06 (screener) are all
  downstream consumers of this seam. Without 0003, no priced feature exists.

---

## 2. What Is Needed (Scope)

### 2.1 Public seam — one pure function (frozen for golden evals)

```
search_analogs(symbol, L, K, parquet_dir) -> list[dict]
```

- `symbol`: store file name stem; reads `{parquet_dir}/{symbol}.parquet` (0001's
  output contract, untouched).
- `L`: query window length in bars. `int`, **5 <= L <= 60** (BRD §2.2 Pro range).
- `K`: maximum number of analogs. `int`, **K >= 1**.
- `parquet_dir`: directory containing the store (created by `build_store`).
- **All four arguments required; no defaults** (tier policy — Free 10-bar/top-3 —
  lives in the UI, not the engine).
- Returns a `list[dict]`, length `min(K, eligible pool size)`, best match first.

### 2.2 Matching math (per BRD §5.1–5.2, frozen)

**Close channel only** (BRD F-07's 60/20/20 wick-volume weighting is deferred):

1. **Query window** = the store's **last L rows** (store is ascending; no resampling —
   sessions are exactly as stored).
2. **Relative trajectory** over the window's L closes
   $r_t = c_t / c_0 - 1,\ t = 0..L{-}1$.
3. **Z-normalization:** $\mu$ = mean of $r$, $\sigma$ = population std of $r$
   (divisor L, matching BRD §5.1's population convention),
   $z_t = (r_t - \mu) / (\sigma + \epsilon)$ with **$\epsilon = 10^{-8}$**.
   A flat window ($\sigma = 0$) normalizes to the all-zero vector — valid data, not an
   error.
4. **Candidate windows:** every run of L consecutive closes in the store, normalized
   identically.
5. **Distance:** $d = \sqrt{\sum_{t}(z_{Q,t} - z_{H,t})^2}$ — plain z-Euclidean.
   **No DTW / Sakoe-Chiba refinement** (0001 frozen decision #7: Euclidean only).
6. **Score:** `score = 100 / (1 + d)`, returned as a raw float (no rounding; the UI
   formats). Monotone similarity index, 100 = identical shape. **Regime alignment is
   NOT part of the score** — F-02 is a later spec (0001 frozen decision #7), so this
   index is explicitly *not* BRD §5.4's full regime-aware Match Quality Score yet.
   **Observed scale (probed on the fixture):** best L=10 match scores ≈ 63.7
   (d ≈ 0.57); scores like BRD §6.2's illustrative "94.2% match" require d ≈ 0.06
   and are rare. The mapping is frozen as decided; rescaling it is a future spec
   revision, not a code change.

### 2.3 Eligibility rule (precise formalization of frozen decision #4)

Let `n` = rows in the store, query start index `q0 = n - L`. A candidate starting at
index `s` occupies `s .. s+L-1` (its window) and `s+L .. s+L+9` (its T+1..T+10 forward
path).

**A candidate is eligible iff its window AND all 10 forward bars lie strictly before
the query window:**

```
s + L + 9 < q0   =>   s in [0, n - 2L - 10]   =>   pool size = n - 2L - 9
```

- No shared bars between a candidate (window *or forward path*) and the query —
  the query can never be its own analog, and an analog's "future" never contains the
  query's own sessions.
- Every returned analog therefore carries a **complete T+1..T+10 path** (no ragged
  or null-padded results).

### 2.4 Result payload (frozen keys)

Each `list` element, in this exact shape:

```python
{
  "date": "YYYY-MM-DD",   # tau_k: LAST session of the matched window
  "distance": float,      # d, raw
  "score": float,         # 100 / (1 + d), raw
  "close": float,         # p_tau: tau_k's own close — baseline for spec 0004's
                           # returns/MAE/MFE (Revision R2, user-directed 2026-10-06)
  "forward": [            # exactly 10 entries, T+1 .. T+10, chronological
    {"date": "YYYY-MM-DD", "open": float, "high": float,
     "low": float, "close": float},
    ...
  ],
}
```

- Dates as ISO strings (consistent with 0001's manifest); OHLC as stored float64.
- **Volume is not returned** (nothing in F-03/F-04/F-05 consumes it).
- **The matched window's own bars are not returned** — they are derivable from the
  store by `date` + `L` (see §6 ceiling).
- **Ordering:** `distance` ascending; exact ties broken by **earlier `date` first**
  (deterministic).

### 2.5 Error contract — `ValueError` naming the failed rule

| Condition | Error keyword |
|---|---|
| Store file `{parquet_dir}/{symbol}.parquet` missing | `store` |
| `L` not an int, or outside 5..60 | `window` |
| `K` not an int, or < 1 | `K` |
| Eligible pool empty (`n < 2L + 10`) | `bars` |

- `pool size < K` is **NOT an error**: return the whole pool (short list).
- The store is trusted, not re-validated — 0001's validation already ran at write
  time (composition, as in 0002 §2.4).

### 2.6 Dependencies

**None new.** pandas + pyarrow are already installed from spec 0001
(`pd.read_parquet`); stdlib/already-installed deps cover the whole spec.

### 2.7 Hermetic evals & performance

- Golden evals build the store from the **committed 0001 fixture**
  (`tests/fixtures/nifty50_daily_ohlcv.csv`) into a tmp dir via `build_store`, then
  call `search_analogs`. **No network in any test** (0001's socket-guard rule).
  No new fixture is needed.
- Sanity (not an SLA, same posture as 0001): fixture (4,673 rows) at `L=10`
  completes in **≲ 1 second** on the dev machine.

---

## 3. What Is NOT Needed (Negative Scope)

- **No DTW / Sakoe-Chiba refinement** — Euclidean only (0001 §7 #7); BRD §4.3's
  "refine top-50 with DTW" is a future upgrade, not 0003.
- **No regime conditioning (F-02)** — no EMA/ATR/percentile logic, no regime tags in
  output (0001 §7 #7: "DTW + regime later").
- **No aggregate statistics** — no forward returns, quantile cone, MAE/MFE, or
  positive frequency. 0004 (reducers) computes those from 0003's `forward` payloads.
- **No multi-channel weighting (F-07)** — close channel only.
- **No HTTP endpoint, no static JSON snapshots, no SQLite, no CLI, no cron/scheduler**
  (0002's deferred nightly wiring), **no UI/dashboard**.
- **No multi-symbol batch, screener (F-06), or caching/memoization** — one symbol
  per call.
- **No trading-calendar or gap logic** — sessions are as stored; no resampling.
- **No re-validation of store contents** and **no writes** — read-only over 0001's
  output.

---

## 4. Acceptance Summary (for Gate 2 authoring; the test spec freezes the details)

- Fixture store, `L=10, K=10` → list of length ≤ 10, `distance` ascending, every item
  with exactly 10 `forward` entries and `score ≈ 100/(1+distance)`.
- Every returned item satisfies §2.3 (window + forward disjoint from query); the
  query window itself never appears.
- **Independent cross-check:** distances/ordering match a straight-line reference
  implementation written literally in the test (to 1e-9), with the §2.4 tie-break.
- Determinism: two identical calls return content-equal lists.
- Short pool: pool < K returns the whole pool without error.
- Each §2.5 error keyword has a rejection case (`missing store`, `L=4`, `L=61`,
  `K=0`, and a store shorter than `2L+10` rows).
- Offline proof (socket guard) + ≲ 1 s sanity at `L=10`; `L=60` also exercised to
  prove parameterization.

---

## 5. Architecture Alignment (Kailash Nadh)

- One pure function, no classes, no framework — vectorized NumPy/pandas over a flat
  Parquet file (rung 6: can it be smaller? It is one function).
- **Pre-computation deferred honestly:** BRD §4.2's nightly batch → static JSON is
  unnecessary while Phase 1 is a single symbol at ~ms-scale live compute; it becomes
  real with the Phase 2 screener (frozen decision #3).
- Composes 0001 verbatim: same store file, same date/price conventions, zero new
  validation code.

---

## 6. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is live single-symbol compute; upgrade path is nightly
  precompute + static JSON (BRD §4.2) when the 2,000-symbol batch arrives.`
- `# ponytail: ceiling is close-channel Euclidean only; upgrade path is
  Sakoe-Chiba DTW refinement on top-50 candidates (BRD §4.3) if shape-warped
  misses surface.`
- `# ponytail: ceiling is score without regime alignment; upgrade path is F-02
  regime conditioning folded into the score (BRD §5.4).`
- `# ponytail: ceiling is forward path only (window bars re-sliced from the store
  by date); upgrade path is including the matched window in the payload if the
  ghost-overlay UI makes it a hot path.`
- `# ponytail: ceiling is no result caching; upgrade path is memoizing per
  (symbol, L) when a screener replays queries.`

---

## 7. Frozen Decisions (from pre-Gate-1 grilling session)

| # | Decision | Choice |
|---|---|---|
| 1 | Next spec after 0002 | **0003 search core (F-01)** — batch cron, dashboard, regime all defer; everything user-facing renders search output |
| 2 | Spec boundary | **Retrieval + forward paths** — top-K with distance/score/raw T+1..T+10 OHLC; aggregates (F-03 cone, F-04 MAE/MFE) are spec 0004 reducers over this seam |
| 3 | Architecture | **Live pure function** — BRD §4.2 nightly precompute/static JSON deferred to Phase 2 / F-06 |
| 4 | Eligibility | **No overlap + full T+10**, formalized in §2.3 as strict disjointness (window *and* forward path before the query) |
| 5 | K & score | **K=10 fixed in-call**, `score = 100/(1+d)`; regime component deferred (0001 #7) |
| 6 | Seam shape | **Symbol-in, store-backed** — `search_analogs(symbol, L, K, parquet_dir) -> list[dict]`; evals build the fixture store hermetically |

---

## 8. Gate 1 Sign-Off

- [x] **User approves** this requirement spec (incl. the §2.3 formalization of
      frozen decision #4 and the §2.4 payload keys) → agent may author Gate 2 test
      spec `specs/tests/0003-pattern-search-core.md`. **(Approved 2026-10-06)**
- [x] **No new dependency requested** (§2.6) — nothing to approve.

**STOP:** No Gate 2 or Gate 3 work proceeds until the box above is checked by the user.
The test spec is **IMMUTABLE once approved**; Gate 3 (code) still requires that
separate approval.
