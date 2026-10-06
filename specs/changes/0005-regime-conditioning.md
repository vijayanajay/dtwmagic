# Gate 4 — Change & Decision Record `0005-regime-conditioning`

**Date:** 2026-10-06
**Gates:** Gate 1 approved (2026-10-06) → Gate 2 frozen (2026-10-06, incl.
user-directed revision R1 during Gate 3) → Gate 3 Red → Green complete.

---

## 1. Files Added / Modified

| File | Change |
|---|---|
| `specs/requirements/0005-regime-conditioning.md` | Added — Gate 1 (approved; §4 soundness wording clarified by R1) |
| `specs/tests/0005-regime-conditioning.md` | Added — Gate 2 (FROZEN, 17 scenarios + six §0 freezes, revision R1) |
| `tests/test_0005.py` | Added — the frozen eval T-001…T-017, updated only by user-directed R1 |
| `src/regime.py` | Added — `search_analogs_regime(symbol, L, K, parquet_dir)` + private `_classify` |
| `src/ohlcv_store.py`, `src/eod_fetch.py`, `src/pattern_search.py`, `src/outcome_stats.py` | **Untouched** (0001–0004 evals re-run green) |
| `specs/tests/0005-regime-conditioning.md` Status + `specs/requirements/...` Status | Stamped through the gates; R1 logged in both |
| New fixtures | **None** — committed 0001 fixture (sha256-guarded) + in-test generated stores (incl. the 416-row slice) |

---

## 2. Architectural & Quantitative Decisions

1. **Composition, single source of truth for 0003's rules.** The wrapper checks
   `store` (path existence, Gate 1 §2.5's frozen textual order), then delegates
   `window`/`K`/`bars` to `search_analogs` **with the caller's own arguments**
   (result discarded), then applies its `regime` gate, then requests the full pool
   (`K = n`) and filters. Zero duplicated validation logic; the frozen order
   `store → window → K → bars → regime` falls out exactly (proven by T-015/T-016).
   Cost: one extra distance computation per call — see ceiling #6.
2. **Filter-then-cap, never cap-then-filter.** `kept[:K]` after the regime filter;
   T-006 discriminates the bug (0003's unfiltered top-3 are all out-of-regime, so
   a cap-first implementation returns < 3 items at K=3).
3. **Regime label lives at query level** (`{"regime", "analogs"}` dict) — the
   grilling decision #4/#5 intent realized without amending 0003's frozen payload
   keys (`test_t001_payload_contract` pins them exactly), and the label survives
   `analogs == []` so zero-result days stay explainable (BRD §6.2.1 header).
4. **Classification is literal Gate 1 §2.2** (probe-pinned): `ewm(span,
   adjust=True)` EMAs; `TR_0 = high−low`; Wilder `ewm(alpha=1/14, adjust=False)`;
   `rolling(252).rank(pct=True)` inclusive of `t`; disjoint `≤1/3`, `≤2/3` bins;
   cells `trend-volatility` with `None` for `t < 251`. The eval's reference
   (`ref_cells`) is an independent literal transcription in the test file — it
   never imports from `src.regime` — so a definition drift on either side breaks
   the cross-check.
5. **Strict no-fallback is real:** the fixture query pool is 131 (L≤30)/128 (L=60)
   of ~4,400; the slice store (2009-06-04) returns `analogs: []` legitimately at
   L=10 **and** L=60, with the regime block intact — zero-result days are data,
   not errors (T-012, T-014).
6. **R1 (user-directed, during Gate 3): frozen T-003 contradiction, found by the
   run.** The scenario pinned `len(analogs) == min(10, 131)` while its exclusion
   bullet demanded *every not-returned eligible date be out-of-regime* — the 121
   in-regime dates beyond the K=10 cap falsified the literal reading; no honest
   code could pass it. Evidence gathered, user approved the revision: the
   exclusion check now runs on a **K=131** call (whole in-regime pool), where
   *not returned ⇔ filtered out* holds literally, and additionally asserts
   `len == 131` and K=10-prefix identity. **No assertion that held was weakened;
   the defect was found by the run, not hidden by it** (same posture as 0003 R1
   and 0004 R1).

---

## 3. Known Limits & Ceilings (in `src/regime.py` docstring)

- Per-call regime recomputation + full-pool filtering → upgrade: precomputed
  regime column / nightly batch (BRD §4.2) at the 2,000-stock scale.
- Query regime = store's last session only → upgrade: Pro custom regime filters
  (BRD §2.2).
- Fixed 252-day rank window, fixed 3×3 grid → upgrade: configurable lookback.
- Two Parquet reads per call (0003's + wrapper's) → upgrade: shared-dataframe
  seam (touches 0003's frozen signature — avoid until forced).
- Filter-after-full-ranking → upgrade: regime-indexed candidate structure if the
  batch pipeline shows real cost.
- **Suite cost:** the pass-through delegation computes the distance matrix twice
  per wrapper call; full suite went 3 s → ~50 s (T-009's own bound, < 5 s,
  passed with margin). Upgrade path: a validate-only seam in 0003, or hoisting
  the user-`K` validation — a future spec's decision, not a silent code change.
- Score still has no regime alignment (BRD §5.4 Match Quality Score = future
  spec); fixture top in-regime scores ≈ 57.6.

---

## 4. Verification Output (Gate 3)

```
RED:   16 failed, 1 passed in 4.27s          RED_EXIT=1  (stub src/regime.py)
       (the 1 pass is T-002 — a pure reference-pin scenario that exercises
        only in-test code by design; all 16 seam-touching scenarios failed)
GREEN: 1 failed (T-003 frozen-spec contradiction, see R1), 16 passed
R1:    user-directed revision applied to Gate 1 §4, Gate 2 T-003 + revision
       log, and tests/test_0005.py (evidence: scenario's own 131-pool pin)
GREEN (after R1): 17 passed in 47.34s        GREEN_EXIT=0
Full suite (0001..0005): 89 passed           FULL_EXIT=0  (49.93s)
```

- Frozen anchors confirmed live by the eval: chain L=10 `4644 → 4402 → 131`,
  L=60 `4544 → 4352 → 128`, L=5 `4654 → 4407 → 131`; occupancy table exact;
  `p252 = 0.5476190476190477`; top-3 `2012-05-14 / 2016-01-12 / 2011-06-23`;
  L=60 top-1 `2012-06-04 → 4.612532697912032`; slice store `416` rows,
  `bullish-normal`, `p252 = 0.3492063492063492`, chains `387 → 145 → 0` and
  `287 → 95 → 0`.
- 0001–0004 sources untouched; their 72 evals pass in the same full-suite run
  (T-017's regression posture).

The test spec was changed only by **user-directed R1** (logged above); every
other scenario, freeze, and pinned value is untouched from approval, and no
assertion was ever relaxed to achieve green.
