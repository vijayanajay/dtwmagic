# Gate 2 — Frozen Test Spec `0005-regime-conditioning`

**Status:** `PENDING USER FREEZE — authored 2026-10-06 (17 scenarios + six §0`
`interface freezes); every numeric pin below was verified by probe through the`
`production path (build_store → read_parquet) BEFORE authoring. This file becomes`
`IMMUTABLE on approval and may never be edited to make failing code pass. Only a`
`user-directed revision may change it.`
**Date:** 2026-10-06
**Maps 1-to-1 to:** `specs/requirements/0005-regime-conditioning.md` (Gate 1,
APPROVED 2026-10-06)
**Test file (Gate 3):** `tests/test_0005.py` (pytest)
**Import seam (frozen):** `from src.regime import search_analogs_regime`
(Gate 3 creates `src/regime.py` **only**; `src/ohlcv_store.py`, `src/eod_fetch.py`,
`src/pattern_search.py`, `src/outcome_stats.py` stay untouched. Tests also import
`build_store`, `search_analogs`, and `summarize_analogs` — all public frozen seams
of specs 0001/0003/0004.)

---

## 0. Interface Freezes (clarifying details of the approved Gate 1)

1. **Type strictness & validation order:** `L`/`K` are `int` **excluding `bool`**
   (0003 §0 freeze 1 verbatim); `symbol` is `str`; `parquet_dir` accepts `str` or
   `pathlib.Path`. Validation order is **0003's four checks first** (`store` →
   `window` → `K` → `bars`, pass-through), **then** the new `regime` check. A
   40-row store at `L=10` therefore reports `regime` (its `bars` check passes at
   `n ≥ 30`), while a 29-row store reports `bars`.
2. **Numeric tolerances:** `p252` pins within **1e-15** absolute (the value is a
   deterministic rank ratio `k/252`); pool/classifiable/occupancy counts are
   **exact ints**; distance pins within **1e-6** absolute (0003 §0 freeze 2);
   wrapper-vs-0003 item floats (`distance`, `score`, `close`) and `forward` rows
   are compared with **exact `==`** (composition must pass 0003's values through
   untouched — any reimplementation that drifts 1 ulp fails); cell strings exact.
3. **Reference implementation:** an independent **literal classification** written
   inside the test file — reads the store with `pandas.read_parquet` (**read-back
   closes/high/low are the reference input**, never the source CSV), computes
   EMAs/TR/ATR/rank directly with pandas using exactly Gate 1 §2.2's parameters
   (`ewm(span, adjust=True)`, `TR_0 = high−low`, `ewm(alpha=1/14, adjust=False)`,
   `rolling(252).rank(pct=True)`, disjoint `≤1/3`, `≤2/3` edges), and builds cells
   by string concatenation. It must **not import anything from `src.regime`**.
   The reference filter enumerates 0003's eligible pool by literal index arithmetic
   (`s ∈ [0, n−2L−10]`, `τ = s+L−1`) and may call the public `search_analogs` for
   composition checks (its output is a frozen seam, not regime code).
4. **Store construction:** main store built **once per session** via `build_store`
   from the 0001 fixture into `tmp_path_factory` (hermetic, no network).
   **Slice store:** fixture rows with `date ≤ 2009-06-04` written to CSV and built
   through the same `build_store` seam (**416 rows**, manifest first 2007-09-17,
   last 2009-06-04). **Tiny stores:** generated in-test as valid inline CSVs
   (varying prices, volume 0, `high ≥ max(open,close)`, `low ≤ min(open,close)`)
   under `tmp_path`, built through `build_store` — never hand-written Parquet.
5. **Frozen facts (probe-verified through the production path):**
   - Fixture: `n = 4,673`, last row `2026-10-05`; query cell **`bearish-normal`**,
     `p252 = 0.5476190476190477`; first classified index **251** (`2008-09-19`).
   - Filter chains (full → classifiable → in-regime):
     `L=10: 4644 → 4402 → 131`, `L=60: 4544 → 4352 → 128`,
     `L=5: 4654 → 4407 → 131`; in-regime also **131** at L=15 and L=30.
   - Occupancy over `[251, n)`: `bullish-low 1334, bullish-normal 718,
     bullish-high 410, bearish-low 83, bearish-normal 145, bearish-high 381,
     neutral-low 320, neutral-normal 420, neutral-high 611` (sums to 4422; no
     empty cell; zero `None` after index 251).
   - Slice store (last session 2009-06-04): query cell **`bullish-normal`**,
     `p252 = 0.3492063492063492`; chains `L=10: 387 → 145 → 0`,
     `L=60: 287 → 95 → 0`.
   - Unfiltered 0003 facts (4644/4544/4654 pools, its top-K anchors) remain
     governed by 0003's own frozen test spec and must stay green unmodified.

**Eval conventions:**
- Runner: `python -m pytest tests/test_0005.py` from repo root (offline).
- Happy-path store: committed fixture `tests/fixtures/nifty50_daily_ohlcv.csv`
  (**sha256 `25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e`**
  — same file as 0001–0003; **no new fixture is created for 0005**). Any drift in
  that hash invalidates this eval (autouse guard on every test).
- Every rejection scenario asserts **both** `pytest.raises(ValueError)` **and** a
  non-empty message containing the frozen keyword (`store` / `window` / `K` /
  `bars` / `regime`).
- "Store read-back" means `pandas.read_parquet` of the built store.

---

## 1. Happy Path (fixture store, L=10, K=10)

**T-001 — Payload contract**
- *Given* the session store built from the fixture,
- *When* `search_analogs_regime("^NSEI", 10, 10, store_dir)` is called,
- *Then* the result is a `dict` with keys **exactly** `{"regime", "analogs"}`;
  `regime` is a `dict` with keys **exactly**
  `{"trend", "volatility", "cell", "p252"}`, `trend == "bearish"`,
  `volatility == "normal"`, `cell == "bearish-normal"` (and
  `cell == trend + "-" + volatility`), `p252` a float within **1e-15** of
  `0.5476190476190477`; `analogs` is a `list` of length ≤ 10 whose every element
  is a `dict` with keys **exactly** `{"date","distance","score","close","forward"}`
  (0003 §2.4 verbatim — no regime key inside items), `date` ISO `YYYY-MM-DD`,
  `distance`/`score`/`close` floats, `forward` a list of exactly 10 dicts with
  keys exactly `{"date","open","high","low","close"}`, and `distance`
  non-decreasing across the list.

**T-002 — Independent reference classification (§2.2 math)**
- *Given* the in-test literal reference (§0 freeze 3) run over the read-back store,
- *When* its cell series is inspected,
- *Then* indices `0..250` are unclassifiable (`None`), index **251** is the first
  classified session and its date is **`2008-09-19`**, the last session's cell is
  `"bearish-normal"`, and the occupancy over `[251, 4673)` equals **exactly** the
  §0 freeze-5 table (all nine cells, sum 4422, zero `None` in-range).

**T-003 — Filter soundness and the 3-stage chain**
- *Given* the reference classification and the fixture store,
- *When* `search_analogs_regime("^NSEI", 10, 10, store_dir)` runs,
- *Then* the reference reproduces the chain **4644 → 4402 → 131**, the result's
  `analogs` has length exactly `min(10, 131) = 10`, every returned `date` maps to
  a store index `τ ≥ 251` with `cell_τ == "bearish-normal"`, `analogs` is an
  **order-preserving subsequence** of `search_analogs("^NSEI", 10, 4673, ...)`
  (same relative order, no reordering), and every 0003-eligible date **not**
  returned has a `None` or `≠ bearish-normal` cell.

**T-004 — Composition identity with 0003 (filter-only proof)**
- *Given* the full unfiltered pool `search_analogs("^NSEI", 10, 4673, store_dir)`
  and T-001's `analogs`,
- *When* each analog is matched to its full-pool item by `date`,
- *Then* `distance`, `score`, `close` are **exactly equal** (`==`, bitwise), the
  `forward` rows are deep-equal, `score ≈ 100/(1 + distance)` within 1e-12
  relative, and regime conditioning changed **no numeric value** — only membership.

**T-005 — Frozen anchors (drift guard, L=10 in-regime top-3)**
- *Given* the fixture store at `L=10, K=10`,
- *When* the first three `analogs` are inspected,
- *Then* they are exactly, in order, distances within **1e-6**:
  1. `2012-05-14` → `distance = 0.73704193241622`
  2. `2016-01-12` → `distance = 0.8686873884829724`
  3. `2011-06-23` → `distance = 1.1371357193691016`
  (These are the best **bearish-normal** windows — deliberately different from
  0003's unfiltered top-3 `2019-05-14 / 2020-03-20 / 2018-05-24`, which are
  out-of-regime. The pins fail if the filter, the ε/σ convention, or the fixture
  changes.)

**T-006 — K caps AFTER the filter (discriminates cap-then-filter bugs)**
- *Given* the fixture store,
- *When* results for `K=3`, `K=1`, and `K=10` are compared,
- *Then* `K=3`'s `analogs` equals the first 3 of `K=10`'s exactly (dates and
  distances), `K=1` equals the first item, and `K=3` has **length 3** — a
  cap-then-filter implementation would return fewer (0003's unfiltered top-3 are
  all out-of-regime, per T-005).

**T-007 — Determinism**
- *Given* the same store,
- *When* `search_analogs_regime("^NSEI", 10, 10, store_dir)` is called twice,
- *Then* both results are content-equal (same regime block, dates, distances,
  scores, forward rows).

**T-008 — Hermetic and read-only**
- *Given* socket access monkeypatched to raise on any use, and the store Parquet's
  sha256 captured before the call,
- *When* `search_analogs_regime` runs on the fixture store,
- *Then* it completes successfully and the store file's sha256 is **unchanged**
  (no network, no writes).

**T-009 — Performance sanity (non-SLA)**
- *Given* the fixture store (n = 4,673),
- *When* an `L=10, K=10` call runs,
- *Then* wall-clock is `< 5.0 s` (generous bound encoding Gate 1's "≲1 s sanity,
  not an SLA"; probe measures well under 1 s including full-pool materialization).

---

## 2. Parameterization (window length L)

**T-010 — L=60 (long window)**
- *Given* the fixture store,
- *When* `search_analogs_regime("^NSEI", 60, 10, store_dir)` runs,
- *Then* the reference chain is **4544 → 4352 → 128**, `len(analogs) == 10`, the
  top-1 is date `2012-06-04` with `distance ≈ 4.612532697912032` (±1e-6), every
  item has `τ ≥ 251` and cell `bearish-normal`, every item carries exactly 10
  forward bars, and ordering matches the reference filter within exact equality.

**T-011 — L=5 (lower boundary)**
- *Given* the fixture store,
- *When* `search_analogs_regime("^NSEI", 5, 10, store_dir)` runs,
- *Then* the reference chain is **4654 → 4407 → 131**, `len(analogs) == 10`, the
  T-001 contract holds, and eligibility uses `q0 = n − 5` with `τ ≥ 251`.

---

## 3. Zero-Result Path (slice store, last session 2009-06-04)

**T-012 — Empty in-regime pool returns regime + empty list, no error**
- *Given* the slice store built from fixture rows `date ≤ 2009-06-04` (416 rows,
  §0 freeze 4),
- *When* `search_analogs_regime("SLICE", 10, 10, tmp_dir)` runs,
- *Then* no exception is raised; the result has keys exactly
  `{"regime", "analogs"}`; `regime ==` `{"trend": "bullish",
  "volatility": "normal", "cell": "bullish-normal", "p252": 0.3492063492063492}`
  (p252 within 1e-15); `analogs == []`; and the reference reproduces the chain
  **387 → 145 → 0**. Repeating at `L=60` gives chain **287 → 95 → 0** with
  `analogs == []` and the same regime block — the §2.5 "pool = 0 is not an error"
  rule, exercised twice.

---

## 4. Warmup & Tiny Stores

**T-013 — Unclassifiable query rejected (`regime` keyword)**
- *Given* a valid in-test store with exactly **251 rows** (last index 250 < 251),
- *When* `search_analogs_regime(sym, 10, 10, tmp_store)` runs,
- *Then* `ValueError` whose message contains `regime` (its `bars` check passes:
  `251 ≥ 2·10 + 10`).

**T-014 — Classifiable query with zero classifiable candidates is not an error**
- *Given* a valid in-test store with exactly **252 rows** (last index 251 — the
  first classifiable session) and `L=60`,
- *When* `search_analogs_regime(sym, 60, 10, tmp_store)` runs,
- *Then* no exception; `regime` block present with a finite `p252` float and
  `cell` equal to the in-test reference's cell for index 251; `analogs == []`
  (every eligible `τ ≤ 252 − 60 − 11 = 181 < 251` is unclassifiable) — Gate 1
  §2.5's last bullet.

**T-015 — Validation order (bars before regime)**
- *Given* valid in-test stores of **40 rows** and **29 rows**,
- *When* `search_analogs_regime(sym, 10, 10, ...)` runs on each,
- *Then* the 40-row store raises `ValueError` containing **`regime`** (its
  `bars` check passes at `n ≥ 30`, then the query at index 39 is
  unclassifiable), and the 29-row store raises `ValueError` containing
  **`bars`** — proving 0003's four checks precede the `regime` check.

---

## 5. Rejections (pass-through keywords, fixture store)

**T-016 — 0003's error contract survives composition**
- *Given* the fixture store directory,
- *When* the seam is called with (a) a `symbol` with no parquet file → message
  contains `store`; (b) `L=4` and `L=61` → `window`; (c) `L=10.5` and `L=True`
  → `window`; (d) `K=0`, `K=-1`, `K=1.5`, `K=True` → `K`,
- *Then* every case raises `ValueError` with exactly the frozen keyword, and no
  case reaches the `regime` stage (order proof with T-015).

---

## 6. Composition with 0004 & Regression

**T-017 — Reducer seam unaffected + 72-test regression**
- *Given* T-001's result and the reference-filtered subset of the full pool,
- *When* `summarize_analogs(result["analogs"])` runs and is compared with
  `summarize_analogs(reference_subset)`,
- *Then* both summaries are content-equal (0004 consumes 0003-shaped dicts
  unchanged — the regime block never reaches the reducer), and **the entire
  existing suite (specs 0001–0004, 72 tests) passes unmodified in the same run**,
  proving no source of a prior spec was touched.

---

## 7. Coverage Map (requirement §2 → scenarios)

| Requirement rule | Scenarios |
|---|---|
| Seam signature, two-key return, no defaults (§2.1) | T-001, T-006 |
| EMA/TR/ATR/rank/bins math, warmup 251, cell strings (§2.2) | T-002, T-013, T-014 |
| Hard filter at τ, strict no-fallback, pool < K / = 0 (§2.3) | T-003, T-012, T-014 |
| Filter-only: scores/distances untouched, order preserved (§2.3) | T-004, T-005, T-010 |
| Payload keys, regime block always present (§2.4) | T-001, T-012 |
| Errors `store`/`window`/`K`/`bars`/`regime` + order (§2.5) | T-013, T-015, T-016 |
| No new deps (§2.6) | — (pandas/pyarrow already installed) |
| Hermetic, fixture sha256 reuse, ≲1 s sanity (§2.7) | T-008, T-009 |
| Composition with 0001/0003/0004, suite regression (§5, §3) | T-004, T-008, T-017 |
| Parameterization L=5..60 (§2.1) | T-005, T-010, T-011 |
| Anchors: chains, occupancy, p252, top-K pins (§4) | T-002, T-003, T-005, T-010, T-011, T-012 |

---

## 8. Gate 2 Sign-Off

- [ ] **User approves** this test spec **including the six §0 interface freezes**
      → it becomes **IMMUTABLE**; Gate 3 (TDD: Red → Green in `tests/test_0005.py`)
      may begin.

**STOP:** No code in `src/regime.py` may be written until the box above is checked
by the user.

**Revision log:** *(none — authored after all pins were probe-verified; any future
change must be a user-directed revision recorded here, like 0003 R1/R2.)*
