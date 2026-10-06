# Gate 1 — Requirement Spec `0004-outcome-stats`

**Status:** `APPROVED — Gate 1 signed off 2026-10-06 (user: "continue with spec 4");
sign correction to 2.2/4 applied pre-sign-off (draft stage); §4 unweighted bullet
corrected by user-directed R1 during Gate 3; Gate 2 frozen, Gate 3 complete`
**Date:** 2026-10-06
**Consumes:** spec `0003-pattern-search-core` as **amended by user-directed Revision
R2** (each analog carries `close`, the p_tau baseline — implemented and verified
before this draft: 0003 evals 19/19, full suite 57/57 green).
**Preceded by:** grilling session resolving spec-0004 shape (see §7 Frozen Decisions)

---

## 0. Gate 1 User-Value Flag

> **No waiver needed.** Direct trader value: this implements BRD **F-03 (Historical
> Outcome Distribution Cone)** and **F-04 (Historical Excursion Profiler)** — F-04 is
> tagged *"Key conversion driver"* for the Pro tier in BRD §3.

---

## 1. User Value Rationale (DIRECT)

- **Why a paying trader cares:** 0003 answers *"has this happened before?"*; 0004
  answers the follow-through question that BRD §1.3 says traders actually pay for:
  *"in those past episodes, how did price behave over the subsequent 1 to 10
  sessions?"* — the empirical distribution of what happened next, plus the observed
  depth of historical drawdowns (MAE) and run-ups (MFE).
- **Monetization link:** Free tier shows median only; Pro shows the full quantile
  cone + excursion profiles (BRD §2.2); F-04 is the Pro conversion driver (BRD §3).
  The dashboard's statistics table (BRD §6.2.3) renders exactly this dict.

---

## 2. What Is Needed (Scope)

### 2.1 Public seam — one pure function (frozen for golden evals)

```
summarize_analogs(analogs) -> stats: dict
```

- `analogs`: the **exact list** returned by 0003's `search_analogs` (R2 payload:
  `date`, `distance`, `score`, `close`, `forward` with exactly 10 bars).
- **Pure reducer: no I/O, no store, no network, no dependencies on 0003's module.**
- All arguments required; no defaults.

### 2.2 Aggregation math (per BRD §5.1/§5.4, frozen)

For analog k (k = 1..n) with baseline `p_k = analogs[k]["close"]` and its forward
bars, at horizon h = 1..10:

1. **Forward return:** `R[k,h] = forward[h-1]["close"] / p_k − 1`
2. **Adverse excursion:** `MAE[k,h] = min_{1<=j<=h}(forward[j-1]["low"] / p_k − 1)`.
   **Sign unconstrained:** usually ≤ 0, but a gap-up regime can keep every low above
   the baseline (MAE > 0) — 0001's `low <= same-bar close` says nothing about p_tau.
3. **Favorable excursion:** `MFE[k,h] = max_{1<=j<=h}(forward[j-1]["high"] / p_k − 1)`.
   **Sign unconstrained:** usually ≥ 0; a sustained dump can keep every high below
   the baseline (MFE < 0). The invariant that *does* hold per analog is
   `MAE[k,h] <= MFE[k,h]` (min of lows ≤ max of highs), hence `mae[h] <= mfe[h]`
   at every h after aggregation.
4. **Cone quantiles:** `p10, p25, p50, p75, p90` of the n values of `R[.,h]` via
   `numpy.quantile(..., method="linear")` — the linear-interpolation definition is
   frozen (any other quantile method is a different number).
5. **Positive frequency:** `count(R[k,h] > 0) / n` — **strictly greater than zero**
   (a flat session is not "positive", per BRD §5.4 "closed positive").
6. **Observed MAE headline:** `mae[h]["p80"] = −quantile(−MAE[.,h], 0.80)` — the
   drawdown deeper than 80% of the sample, reported **signed** (≤ 0), matching BRD
   §6.2.3's *"Historical Observed MAE (80th percentile historical drawdown)"*.
7. **Observed MFE headline:** `mfe[h]["p50"] = median(MFE[.,h])` — matching BRD
   §6.2.3's *"Historical Observed MFE (Median peak move)"*.

**Unweighted across analogs** — every analog counts equally (no score/distance
weighting; see §7).

### 2.3 Output contract (frozen keys)

```python
{
  "n": int,                              # len(analogs), >= 1
  "horizons": [1, 2, 3, ..., 10],        # frozen list of ints
  "cone": {h: {"p10", "p25", "p50", "p75", "p90"}},   # floats, signed fractions
  "positive_frequency": {h: float},      # in [0, 1]
  "mae": {h: {"p80": float}},            # signed, <= 0
  "mfe": {h: {"p50": float}},            # signed, >= 0
}                                        # h are Python ints 1..10 in all four maps
```

- All floats are **signed fractions** (0.0153 = +1.53%), never pre-multiplied by
  100; the UI formats percentages.
- Deterministic: same input list → content-equal output.

### 2.4 Error contract — `ValueError` naming the failed rule

| Condition | Keyword |
|---|---|
| `analogs` not a list, or empty (`n = 0`) | `analogs` |
| element not a dict | `analog` |
| missing `close`, non-finite, or `<= 0` | `close` |
| missing `forward`, not a list, or `len < 10` | `forward` |

- Forward-bar **contents** are trusted (0001 validated OHLC at write time;
  composition, not re-validation). Structure (≥10 bars) is the reducer's contract.

### 2.5 Dependencies

**None new** — numpy + pandas already installed (quantile + nothing else).

### 2.6 Hermetic evals & performance

- Evals build `analogs` **in-test**: synthetic lists for edge cases, plus one
  composition case = fixture-store `search_analogs("^NSEI", 10, 10, ...)` output
  (session store, sha256-guarded fixture as in 0003). **No network in any test.**
- Sanity (not an SLA): summarize of the 10-analog fixture result completes in
  **≲ 1 s** (actual: milliseconds).

---

## 3. What Is NOT Needed (Negative Scope)

- **No per-analog tables** — raw R/MAE/MFE per episode are derivable from 0003's
  payload; 0004 returns aggregates only.
- **No regime conditioning (F-02)** and **no score/distance weighting** — unweighted
  over exactly the analogs passed in.
- **No tier logic** — the full cone is always computed; Free tier's "median only"
  is the UI showing `p50` alone (same policy pattern as 0003's K cap).
- **No chart/overlay geometry (F-05)** — no ghost paths, no chart series beyond the
  four aggregate maps.
- **No store reads, no network, no CLI, no HTTP/JSON writing** — callers serialize.
- **No horizons beyond T+10**, no intraday, no volume stats, no benchmark-relative
  or risk-adjusted (Sharpe-style) statistics.
- **No predictions, no forward guidance** — output is descriptive historical
  aggregates only; SEBI tooltip wording (BRD §8.2C) belongs to the UI spec, not here.
- **No NaN policy games** — with `n >= 1` every frozen statistic is defined.
- **No caching/memoization.**

---

## 4. Acceptance Summary (for Gate 2 authoring; the test spec freezes the details)

- Given the fixture-store 10-analog result (R2), `summarize_analogs` returns
  `n == 10`, `horizons == [1..10]`, and every frozen key present; all
  `positive_frequency` values in `[0,1]`; and `mae[h] <= mfe[h]` at every h
  (mathematical invariant from §2.2).
- An **independent literal reference** (hand-rolled linear-interpolation quantile,
  no `np.quantile`) matches every frozen value to `1e-12`.
- **Unweighted proof (corrected by R1):** (a) duplicating the whole input list
  doubles `n` and leaves `positive_frequency` **exactly** unchanged — the ratio is
  the only duplication-invariant statistic (linear-interpolation quantiles are
  *not* invariant, so cone/mae/mfe legitimately shift with n); and (b) both the
  original and the duplicated list match the independent reference to `1e-12`
  (any weighting diverges from the unweighted reference).
- **Monotonicity (mathematical, frozen):** `mfe[h+1] >= mfe[h]` and
  `mae[h+1] <= mae[h]` for all h — max/min over a growing window.
- `n == 1` (single analog): cone is flat at that analog's returns, frequency is
  exactly `0.0` or `1.0`, mae/mfe equal its own excursions — no NaN, no error.
- Each §2.4 error keyword has a rejection case (`analogs` / `analog` / `close` /
  `forward`), including `close == 0` and `forward` with 9 bars.
- Offline proof (no sockets touched by construction) + ≲1 s sanity.

---

## 5. Architecture Alignment (Kailash Nadh)

- One pure function, ~60 lines: numpy quantile + three aggregations. No classes, no
  framework, no I/O (rung 6).
- Consumes 0003 verbatim (R2) — same list the UI already receives; zero duplicated
  slicing logic, zero new validation beyond the four structural rules.
- Pre-computation unnecessary: K ≤ ~10 × 10 horizons = milliseconds; batching this
  would be complexity without a workload (BRD §4.1's pre-compute rule targets the
  2,000-symbol search itself, not a 10×10 reduction).

---

## 6. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is linear-interpolation quantiles on small n (Free tier
  K=3); upgrade path is a min-sample guard or bootstrap interval when tiering
  moves to the UI.`
- `# ponytail: ceiling is unweighted over the returned analogs; upgrade path is
  distance/score-weighted aggregates if traders find near-duplicates dominate.`
- `# ponytail: ceiling is horizon cap T+10 (0003 payload bound); upgrade path is
  T+20 forward paths in 0003 + this reducer's horizons list.`
- `# ponytail: ceiling is MAE=p80 / MFE=p50 headlines only (BRD 6.2.3 copy);
  upgrade path is full MAE/MFE quantile cones on request.`
- JSON serialization stringifies the int horizon keys (`1` → `"1"`) — a consumer
  note, not a contract change.

---

## 7. Frozen Decisions (pre-Gate-1 grilling session)

| # | Decision | Choice |
|---|---|---|
| 1 | Baseline p_tau source | **0003 payload amended by R2** (`close` key) — implemented and verified (19 + 57 green) before this draft; beats passing a closes-lookup arg or letting the reducer read the store |
| 2 | Aggregate set | **Full h=1..10 profiles** — cone (p10/p25/p50/p75/p90) + positive frequency + MAE p80 + MFE p50 per horizon (superset of every BRD citation, incl. §5.4's {1,3,5,10}) |
| 3 | Seam shape | **Pure reducer** — `summarize_analogs(analogs)`, no I/O (0003 decision #2 honored) |
| 4 | Weighting | **Unweighted** across exactly the analogs passed in (BRD is silent; weighting is tier/policy, not engine) |
| 5 | Conventions | `np.quantile(..., method="linear")`; frequency strict `> 0`; MAE signed via `−quantile(−MAE, 0.80)`; values as signed fractions |

---

## 8. Gate 1 Sign-Off

- [x] **User approves** this requirement spec (incl. §2.2 conventions and the §2.3
      output keys) → agent may author Gate 2 test spec
      `specs/tests/0004-outcome-stats.md`. **(Approved 2026-10-06)**
- [x] **Precondition:** 0003 Revision R2 (payload `close` key) executed and verified
      — 0003 evals 19/19, full suite 57/57. **(Directed by user 2026-10-06)**
- [x] **No new dependency requested** (§2.5) — nothing to approve.

**STOP:** No Gate 2 or Gate 3 work proceeds until the box above is checked by the user.
The test spec is **IMMUTABLE once approved**; Gate 3 (code) still requires that
separate approval.
