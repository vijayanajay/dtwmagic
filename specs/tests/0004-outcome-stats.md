# Gate 2 — Frozen Test Spec `0004-outcome-stats`

**Status:** `FROZEN — approved by user 2026-10-06 (15 scenarios + all §0 freezes and
pinned values); user-directed revision R1 applied during Gate 3 (see Revision log).
This file is IMMUTABLE; it may never be edited to make failing code pass. Only a
user-directed revision may change it.`
**Date:** 2026-10-06
**Maps 1-to-1 to:** `specs/requirements/0004-outcome-stats.md` (Gate 1, APPROVED
2026-10-06, incl. pre-sign-off sign correction to §2.2/§4)
**Test file (Gate 3):** `tests/test_0004.py` (pytest)
**Import seam (frozen):** `from src.outcome_stats import summarize_analogs`
(Gate 3 creates `src/outcome_stats.py`; `src/ohlcv_store.py`, `src/eod_fetch.py`,
and `src/pattern_search.py` stay untouched.)

---

## 0. Eval Conventions (interface freezes — surfaced for approval with this spec)

1. **Reference implementation:** an independent **literal loop** inside the test file
   — computes R/MAE/MFE per analog per horizon and a **hand-rolled linear quantile**
   (`x = sorted(vals); h = (n-1)*q; lerp between floor(h) and ceil(h)`), **never
   `np.quantile`** (so a quantile-method disagreement cannot self-confirm). Must not
   import any helper from `src/`. Cross-check tolerance: **1e-12 abs**.
2. **Synthetic analog builder:** `mk(closes, base, lows, highs)` builds R2-shaped
   dicts (`date`/`distance`/`score` dummies — the reducer reads only `close` +
   `forward`); forward bars carry `date,open,high,low,close` with `open = close`.
3. **Composition store:** the session fixture store from 0003's eval — `build_store`
   on the sha256-guarded fixture
   (`25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e`), searched with
   `search_analogs("^NSEI", 10, 10, ...)` → exactly 10 R2 analogs. Drift in the
   fixture hash or 0003's frozen output invalidates this eval.
4. **Error style:** every rejection asserts `pytest.raises(ValueError)` **and** the
   frozen keyword substring (`analogs` / `analog` / `close` / `forward`).
5. **Frozen facts (probed 2026-10-06 through the real pipeline):** hand-case pins in
   §2 and composition anchors in §3 below; composition `n == 10`,
   `freq(3) == freq(5) == 0.7`, `freq(10) == 0.6`.

---

## 1. Output Contract

**T-001 — Frozen dict shape**
- *Given* `analogs` = three synthetic R2 analogs (varied returns),
- *When* `summarize_analogs(analogs)` runs,
- *Then* the result is a `dict` with keys **exactly**
  `{"n","horizons","cone","positive_frequency","mae","mfe"}`; `n == 3` (int);
  `horizons == [1,2,...,10]` with every element an `int`; each of the four maps has
  keys **exactly** the ints `1..10`; each `cone[h]` has keys **exactly**
  `{"p10","p25","p50","p75","p90"}`; each `mae[h]` = `{"p80": float}`; each
  `mfe[h]` = `{"p50": float}`; all values are floats; every
  `positive_frequency[h]` in `[0.0, 1.0]`; and `mae[h]["p80"] <= mfe[h]["p50"]`
  for every h (Gate 1 §2.2 invariant).

**T-002 — Independent reference cross-check + sign semantics**
- *Given* a varied synthetic set (analog X: closes rising with lows always above the
  baseline → MAE > 0; analog Y: falling with highs always below the baseline →
  MFE < 0; analog Z: zigzag with ordinary bars),
- *When* `summarize_analogs` output is compared with the in-test literal reference
  (§0 freeze 1),
- *Then* every value of `cone`, `positive_frequency`, `mae`, `mfe` matches within
  `1e-12`; **and** `summarize_analogs([X])["mae"][1]["p80"] > 0` while
  `summarize_analogs([Y])["mfe"][1]["p50"] < 0` — pinning Gate 1's sign-correction
  (excursions are unconstrained relative to baseline p_tau).

**T-003 — Determinism**
- *Given* the same input list,
- *When* `summarize_analogs` runs twice,
- *Then* both results are content-equal.

**T-004 — Performance sanity (non-SLA)**
- *When* `summarize_analogs` runs on the 10-analog composition input,
- *Then* wall-clock is `< 5.0 s` (Gate 1's ≲1 s sanity; actual is milliseconds).

---

## 2. Aggregation Math (hand-verifiable golden pins)

**T-005 — Two-analog hand case (pins every frozen convention)**
- *Given* two analogs, both `close = 100`, flat bars (`low = high = close`):
  analog A's forward closes = `101, 102, …, 110` (R = +1%…+10%),
  analog B's = `99, 98, …, 90` (R = −1%…−10%),
- *When* `summarize_analogs([A, B])` runs,
- *Then* for **every** h = 1..10:
  - `cone[h]["p10"] == −0.008h`, `p25 == −0.005h`, `p50 == 0.0`,
    `p75 == +0.005h`, `p90 == +0.008h` (abs 1e-12),
  - `positive_frequency[h] == 0.5` exactly,
  - `mae[h]["p80"] == −(0.008h − 0.002)` (abs 1e-12),
  - `mfe[h]["p50"] == 0.005h − 0.005` (abs 1e-12; probe-verified — A's MFE grows
    with h, so the median is not 0 for h ≥ 2).

**T-006 — Unweighted across analogs (revision R1)**
- *Given* a synthetic list and the same list with every element duplicated,
- *When* both are summarized,
- *Then* `n` doubles; `positive_frequency` is **exactly** unchanged at every h
  (the ratio is duplication-invariant); and **both** results match the in-test
  literal reference within `1e-12`. Linear-interpolation quantiles are *not*
  duplication-invariant (cone/mae/mfe legitimately shift with n), so the unweighted
  guarantee rests on the reference cross-check — any weighting would diverge from
  the unweighted reference here exactly as in T-002/T-009.

**T-007 — Monotonicity invariants (mathematical, exact)**
- *Given* the hand-case input of T-005 and the composition input of T-009,
- *When* profiles are inspected across h,
- *Then* `mfe[h+1]["p50"] >= mfe[h]["p50"]` and
  `mae[h+1]["p80"] <= mae[h]["p80"]` for all h = 1..9 (**exact** comparisons),
  and `mae[h]["p80"] <= mfe[h]["p50"]` at every h.

**T-008 — Strictly-positive frequency (zero is not positive)**
- *Given* one analog whose forward closes all equal its `close` (R = 0 at every
  horizon) and one whose closes all rise,
- *When* each is summarized alone,
- *Then* the flat one yields `positive_frequency[h] == 0.0` for every h, and the
  rising one yields `1.0` — exactly (BRD §5.4 "closed positive" is strict).

---

## 3. Composition (fixture store → 0003 → 0004)

**T-009 — End-to-end on the frozen fixture search, with anchors**
- *Given* the session fixture store and `search_analogs("^NSEI", 10, 10, ...)`
  (exactly 10 R2 analogs),
- *When* `summarize_analogs` consumes that list,
- *Then*: `n == 10`; the in-test reference matches every value within `1e-12`;
  T-007's monotonicity holds; **and** these anchors match (abs `1e-9`):
  - `cone[10]` = `{"p10": −0.01247148067428826, "p25": −0.009747233614655182,
    "p50": 0.01105743068690379, "p75": 0.023938272265599192,
    "p90": 0.061937355116913805}`
  - `cone[1]["p50"]` = `0.002058221272220273`
  - `positive_frequency[3] == 0.7`, `[5] == 0.7`, `[10] == 0.6` (exact)
  - `mae[10]["p80"]` = `−0.0267533227`, `mae[1]["p80"]` = `−0.0116546747`
  - `mfe[5]["p50"]` = `0.0232016430`, `mfe[10]["p50"]` = `0.0287962421`

---

## 4. Rejections (each: `pytest.raises(ValueError)` + frozen keyword)

**T-010 — `analogs`:** input `"nope"` (str) and `{}` (dict) → message contains
`analogs`; **empty list `[]`** → message contains `analogs`.
**T-011 — `analog`:** list elements `42` and `None` (not dicts) → message contains
`analog`.
**T-012 — `close`:** element missing `close`; `close == 0`; `close == −5`;
`close == float("nan")` → message contains `close`.
**T-013 — `forward`:** element missing `forward`; `forward` with 9 bars;
`forward = 123` (not a list) → message contains `forward`.

---

## 5. Edge Semantics

**T-014 — Single analog (n = 1)**
- *Given* hand-case analog A alone (`close = 100`, forward closes 101…110, flat bars),
- *When* `summarize_analogs([A])` runs,
- *Then* `n == 1`; for every h: all five cone quantiles equal `0.01h` (abs 1e-12),
  `positive_frequency[h] == 1.0` exactly, `mae[h]["p80"] == 0.01` (its minimum low
  never dips below baseline — **and is > 0**, re-pinning the sign semantics),
  `mfe[h]["p50"] == 0.01h`; no NaN anywhere.

**T-015 — Hermetic (no network)**
- *Given* socket access monkeypatched to raise on any use,
- *When* the synthetic scenarios and the fixture composition scenario run,
- *Then* all complete successfully (the reducer does no I/O by construction).

---

## 6. Coverage Map (requirement §2 → scenarios)

| Requirement rule | Scenarios |
|---|---|
| Seam + frozen dict keys (§2.1, §2.3) | T-001 |
| R / MAE / MFE formulas vs baseline p_tau (§2.2.1–3) | T-002, T-005, T-014 |
| Quantile `method="linear"` (§2.2.4) | T-002, T-005 (hand-rolled lerp reference) |
| Frequency strict `> 0` (§2.2.5) | T-005, T-008 |
| MAE p80 signed, MFE p50 (§2.2.6–7) | T-002, T-005, T-009, T-014 |
| `mae[h] <= mfe[h]` invariant (§2.2) | T-001, T-007 |
| Unweighted (§7 #4) | T-006 |
| Errors `analogs`/`analog`/`close`/`forward` (§2.4) | T-010 … T-013 |
| Composition with 0003 R2 output (§2.1) | T-009 (sha256-guarded) |
| Determinism, ≲1 s sanity, hermetic (§2.3, §2.6) | T-003, T-004, T-015 |

---

## 7. Gate 2 Sign-Off

- [x] **User approves** this test spec **including the §0 freezes and every pinned
  value** → it becomes **IMMUTABLE**; Gate 3 (Red → Green in `tests/test_0004.py`)
  may begin. **(Approved 2026-10-06)**

**STOP:** No code in `src/outcome_stats.py` may be written until the box above is
checked by the user.

**Revision log:**
- **R1 (2026-10-06, user-directed, during Gate 3 Green):** T-006's original claim
  (cone/mae/mfe unchanged under duplication) is mathematically false for
  linear-interpolation quantiles — counterexample `p10([a,b]) = −0.035` vs
  `p10([a,a,b,b]) = −0.050`; on the test input `−0.006 → −0.010` (delta 0.004).
  No honest implementation can satisfy it while honoring Gate 1 §2.2.4. Reworded to
  the true, sufficient assertions: `n` doubles, `positive_frequency` exactly
  unchanged, both lists match the reference to `1e-12`. Gate 1 §4's identical false
  bullet was corrected in the same revision. All other scenarios, freezes, and
  pinned values untouched; found by the Red run, not by weakening any assertion
  that held.
