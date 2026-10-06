# Gate 4 — Change & Decision Record `0003-pattern-search-core`

**Date:** 2026-10-06
**Gates:** Gate 1 approved (2026-10-06, incl. §2.3 disjointness tightening) → Gate 2
frozen with five §0 interface freezes + revision R1 → Gate 3 Red → Green complete.

---

## 1. Files Added / Modified

| File | Change |
|---|---|
| `specs/requirements/0003-pattern-search-core.md` | Added — Gate 1 (approved, incl. §2.3 formalization) |
| `specs/tests/0003-pattern-search-core.md` | Added — Gate 2 (FROZEN, 19 scenarios, revision R1) |
| `tests/test_0003.py` | Added — the frozen eval T-001…T-019 + in-test literal reference |
| `src/pattern_search.py` | Added — `search_analogs(symbol, L, K, parquet_dir)` |
| `src/ohlcv_store.py`, `src/eod_fetch.py` | **Untouched** (0001/0002 evals re-run green) |
| Fixtures | **None added** — evals reuse the committed 0001 fixture (sha256-guarded) |

---

## 2. Architectural & Quantitative Decisions

1. **Vectorized candidates, boring sort.** `sliding_window_view` normalizes all
   eligible windows in one array pass; ranking is a plain Python list of
   `(distance, date, index)` tuples sorted with a tuple key — the tie-break (earlier
   date first) falls out of the sort itself, no custom comparator (Kailash rung 6).
2. **Validation order: `window` → `K` → `store` → `bars`.** Each frozen keyword wins
   deterministically; tests pin keywords, order beyond that is unconstrained.
   `bool` is rejected before `int` (Python's `isinstance(True, int)` trap, §0 freeze 1).
3. **σ=0 flat windows are load-bearing, not an edge case:** Gate 1 §2.2's
   "flat → zero vector" rule is what makes T-019's exact tie provable — two constant
   windows both normalize to all-zero vectors, giving bitwise-equal distances the
   `(distance, date)` ordering can then break.
4. **pandas' default `read_csv` float parser is not correctly rounded** (observed
   1-ulp drift, e.g. `0x…599c → 0x…599b`), which **invalidated the first T-019
   construction** (power-of-2 scaled windows → distances differing at 1e-14). Found
   by probe *before* Gate 2 approval; the scenario was rebuilt on constant short
   decimal windows and the caveat became §0 freeze 3's note. The frozen anchors were
   computed **through** the real `build_store` path, so they already absorb any such
   drift (tolerance 1e-6 vs ~1e-13 effect).
5. **Reference lives in the test, reads the store** (§0 freeze 3): literal loop over
   `read_parquet` closes with `ddof=0` — never imports from `src/`, and never reads
   the source CSV (so it and the implementation always see identical floats).
6. **Green-phase harness fix (zero assertion changes):** `read_store` hardcoded
   `^NSEI.parquet`, so T-013's tiny `TINY` store raised `FileNotFoundError`. Fixed by
   adding a `symbol` parameter (default `"^NSEI"`). **No frozen scenario, assertion,
   tolerance, or value was altered** — a helper's filename resolution was corrected
   to implement the scenario as written.

---

## 3. Known Limits & Ceilings

Carried verbatim from Gate 1 §6 (`# ponytail` comments are in the module docstring):

- Live single-symbol compute; nightly precompute + static JSON (BRD §4.2) arrives
  with the 2,000-symbol batch.
- Close-channel Euclidean only; Sakoe-Chiba DTW refinement (BRD §4.3) deferred.
- Score has no regime alignment yet (F-02 later spec); observed best fixture score
  ≈ 63.7, so BRD's illustrative "94.2% match" copy needs a future mapping revision.
- Matched window's own bars not in the payload — consumers re-slice the store by
  `date` + `L`.
- No result caching; no writes; store trusted, never re-validated (0001's contract).
- Candidate windows may overlap **each other** (only query-disjointness is enforced) —
  top-K can contain adjacent, near-identical episodes; independence of analogs is a
  future concern (dedup) if the UI shows redundant ghosts.

---

## 4. Verification Output (Gate 3)

```
RED:   19 failed in 1.49s                    RED_EXIT=1   (stub src/pattern_search.py)
GREEN: 18 passed, 1 failed (test helper bug: read_store hardcoded ^NSEI)
       fix = symbol param on helper, NO assertion changed
GREEN (after helper fix): 19 passed          GREEN_EXIT=0
Full suite (0001 + 0002 + 0003): 57 passed   FULL_EXIT=0   (2.61s)

Frozen anchors confirmed live by the eval:
  L=10 pool=4644  top-3 2019-05-14/0.570966011106, 2020-03-20/0.659910750504,
                      2018-05-24/0.668395481286
  L=60 pool=4544  top-1 2018-10-29/2.581337345431   (R1-corrected arithmetic)
  L=5  pool=4654  top-1 2018-09-25/0.164200033042
  T-019 exact tie 3.1622748239264022 == ... , earlier date first, adjacent
```

The test spec was not edited after freezing except for **R1 (user-directed, applied
before any Gate 3 code existed)** and the Green-phase helper fix above — no assertion
was ever relaxed to achieve green. The RED run is genuine: all 19 scenarios failed
against the stub before implementation existed.
