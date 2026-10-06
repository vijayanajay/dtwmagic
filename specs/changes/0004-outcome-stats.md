# Gate 4 — Change & Decision Record `0004-outcome-stats`

**Date:** 2026-10-06
**Gates:** Gate 1 approved (incl. pre-sign-off sign correction to §2.2/§4) → Gate 2
frozen with five §0 freezes + 15 scenarios → Gate 3 Red → Green complete
(user-directed revision R1 applied during Green).

---

## 1. Files Added / Modified

| File | Change |
|---|---|
| `specs/requirements/0004-outcome-stats.md` | Added — Gate 1 (approved; §4 bullet corrected by R1) |
| `specs/tests/0004-outcome-stats.md` | Added — Gate 2 (FROZEN, 15 scenarios, revision R1) |
| `tests/test_0004.py` | Added — the frozen eval T-001…T-015 + hand-lerp reference |
| `src/outcome_stats.py` | Added — `summarize_analogs(analogs)` |
| 0003 files (2 specs, `src`, `tests`) | **Modified earlier by user-directed R2** — payload `close` key (precondition: 19 + 57 green) |
| New fixtures | **None** — synthetic builders + the sha256-guarded 0001 fixture for composition |

---

## 2. Architectural & Quantitative Decisions

1. **Pure reducer, baseline via R2.** `summarize_analogs` reads only the R2 payload
   (`close` + `forward`) — no store, no network — because 0003's payload was amended
   first rather than leaking a `closes` lookup into every consumer (frozen decision #1
   of Gate 1 §7).
2. **Sign correction before approval (pre-freeze).** Gate 1 originally claimed
   "MAE ≤ 0, MFE ≥ 0 always" — false: excursions are measured against baseline
   p_τ, not the same-bar close (0001's `low ≤ close` binds bar-to-bar only). Corrected
   to the true invariant `mae[h] ≤ mfe[h]` (min-of-lows ≤ max-of-highs per analog,
   quantile-monotone) and pinned through the seam by T-002/T-014 (MAE > 0 and
   MFE < 0 single-analog cases).
3. **Two independent quantile implementations.** The eval's reference hand-rolls
   linear interpolation (`lerp` on `(n−1)q`) and is forbidden from `np.quantile`, so
   a quantile-method disagreement cannot self-confirm; cross-checks run at 1e-12.
4. **R1 (user-directed, during Green): frozen duplication claim was false.**
   Linear-interpolation quantiles are **not** duplication-invariant — counterexample
   `p10([a,b]) = −0.035` vs `p10([a,a,b,b]) = −0.050`; on the actual test input
   `−0.006 → −0.010` (delta 0.004). No honest code can pass it while honoring Gate 1
   §2.2.4 (quantiles over the n values). T-006 and Gate 1 §4's twin bullet were
   reworded to the true, sufficient assertions: `n` doubles, `positive_frequency`
   exactly unchanged (the only invariant ratio), and **both** lists match the
   unweighted reference to 1e-12 — the real unweighted proof, backed by T-002/T-009.
   **No assertion that held was weakened; the defect was found by the run, not hidden
   by it.**
5. **Validation order `analogs → analog → close → forward`**, `bool` rejected before
   `int`; forward contents trusted (0001 validated OHLC), structure (≥10 bars) checked.

---

## 3. Known Limits & Ceilings

From Gate 1 §6 (module docstring carries the `# ponytail` comments):

- Linear quantiles on small n (Free tier K=3) — upgrade: min-sample guard or
  bootstrap interval at tiering time.
- Unweighted — upgrade: distance/score weighting if near-duplicates dominate.
- Horizon cap T+10 (0003 payload bound) — upgrade: T+20 forward paths.
- MAE p80 / MFE p50 headlines only (BRD §6.2.3 copy) — upgrade: full MAE/MFE cones.
- JSON serialization stringifies the int horizon keys (consumer note).

---

## 4. Verification Output (Gate 3)

```
RED:   15 failed in 1.20s                     RED_EXIT=1   (stub src/outcome_stats.py)
GREEN (first run): 14 passed, 1 failed
       T-006 — frozen-spec math defect (duplication invariance), NOT a code bug;
       evidence gathered, user-directed R1 applied to Gate 1 4 + Gate 2 T-006
       + tests/test_0004.py (assertion replaced with true/sufficient ones)
GREEN (after R1): 15 passed                   GREEN_EXIT=0
Full suite (0001..0004): 72 passed            FULL_EXIT=0   (2.92s)

Pins re-verified by probe before/after R1:
  T-005 hand-case (incl. corrected mfe = 0.005h − 0.005): ALL PASS
  T-014 single-A (incl. mae = +0.01 > 0 sign semantics):  ALL PASS
  T-007 monotonicity (mfe ↑, mae ↓):                      holds
  T-009 composition anchors (n=10, freq 0.7/0.7/0.6, cone/mae/mfe): matched
```

The test spec was changed only by **user-directed R1** during Green (logged above);
every other scenario, freeze, and pinned value is untouched from approval.
