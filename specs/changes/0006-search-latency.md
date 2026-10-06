# Gate 4 — Change & Decision Record `0006-search-latency`

**Date:** 2026-10-06
**Gates:** Gate 1 approved (2026-10-06, incl. the §2.2 evidence-based scope pivot)
→ Gate 2 frozen (2026-10-06, 9 scenarios + five §0 freezes) → Gate 3 Red →
Green complete.

---

## 1. Files Added / Modified

| File | Change |
|---|---|
| `specs/requirements/0006-search-latency.md` | Added — Gate 1 (approved) |
| `specs/tests/0006-search-latency.md` | Added — Gate 2 (FROZEN, 9 scenarios + five §0 freezes) |
| `tests/test_0006.py` | Added — the frozen eval T-001…T-009 (incl. the sha guard over all five prior evals) |
| `src/pattern_search.py` | **Modified — payload loop only (Fix A):** hoisted column arrays replace per-row `df.iloc[...] .iterrows()`; docstring ceiling comment added |
| `src/regime.py` | **Modified — validation flow (Fix B):** inline `window`/`K` mirrors (byte-identical messages), single `search_analogs(K = n)` call carries `bars`, then the `regime` gate |
| `tests/test_0001.py` … `tests/test_0005.py` | **Untouched** — sha256-pinned by Gate 2 §0 freeze 2 and asserted on every run |
| 0001–0004 sources (`ohlcv_store`, `eod_fetch`, `outcome_stats`) | **Untouched** |

---

## 2. Architectural & Quantitative Decisions

1. **Evidence pivoted the scope (Gate 1 §7 #1).** The ceiling 0005 recorded
   ("computes the distance matrix twice") was misleading about *cost*: the
   discarded validation call was 17 ms (0.7%) while payload materialization was
   **95%** of a 2.33 s call (cProfile: `pattern_search.py:75` listcomp 5.995 s of
   6.321 s; 51,084 `iterrows`). Fix B (the literal ask) was still done — it is
   now ~10 ms and gone from the wrapper path — but the halving credit belongs to
   Fix A. Both numbers stay visible in Gate 1 §2.2 and §4 below.
2. **Fix A = column arrays, not `itertuples`** (Gate 1 §7 #2): plain
   `to_numpy("float64")` hoisted once + `range(FORWARD)` indexing, explicit
   `float(...)` casts keep payloads builtin-`float` (Gate 2 §0 freeze 4,
   JSON-honesty for spec 0007) and **bit-identical** to read-back values —
   proven by T-004 sampled across the whole pool, not by assertion-free trust.
3. **Fix B = inline `window`/`K` mirrors + delegated `bars`** (Gate 1 §7 #4):
   messages copied byte-for-byte from 0003; the single `search_analogs(K = n)`
   call raises `bars`, and the `regime` gate runs after it — the frozen order
   `store → window → K → bars → regime` holds exactly, pinned by T-002/T-003 spy
   counts (0 calls for `store/window/K`, 1 call for `bars/regime`).
   Rejected: validating with the caller's `K` (forces the second computation
   back) and a manual `bars` check (a third copy of that rule).
4. **The regime gate sits after the pool call.** For `n ≥ 252` it cannot fail, so
   there is no wasted work on real stores; below 252 rows the pool is ≤ 222 items
   and the waste is microseconds. Simpler than re-ordering the frozen checks.
5. **Closed-spec source changed, frozen tests did not** (Gate 1 §7 #3/#6): 0003's
   module was edited at exactly one loop; correctness is enforced by its 19
   frozen evals, 0005's 17 (via T-004's bitwise wrapper↔`search_analogs` identity),
   and the sha guard that makes *any* prior-eval edit fail every 0006 test.
6. **RED honesty:** 3 of 9 scenarios failed at RED (T-001 spy count 2≠1, T-002
   spy count ≠0, T-007 2.322 s > 1.0 s) — the new-behavior set. The other 6
   **already passed** by design: they are regression guards for invariants the
   refactor must *keep* (payload identity, anchors, determinism, hermeticity), so
   their job starts at GREEN. Documented rather than gamed.

---

## 3. Known Limits & Ceilings (module docstring comments)

- `# ponytail: payload from hoisted column arrays (spec 0006 Fix A); upgrade
  path is a rank-only seam with survivor-only payload build (~15 ms) if a
  consumer needs the full pool routinely.` (in `pattern_search.py`)
- Full-pool calls still build all 4,644 payloads (now 70 ms total) — only
  consumers that request `K = n` pay it; the wrapper does, per frozen contract.
- Suite floor now set by the frozen tests' own direct full-pool calls (~4 s of
  the 6.26 s) — going lower requires editing frozen evals (forbidden).
- Inline `window`/`K` mirrors duplicate 0003's rules — drift would require a
  user-directed revision in both specs; both suites pin the keywords today.
- No caching/memoization (0003's separate documented ceiling).
- **Supersedes** 0005's Gate 4 ceiling #6 ("pass-through delegation computes the
  distance matrix twice"); 0005's record stays as historical truth.

---

## 4. Verification Output (Gate 3)

```
RED:   3 failed, 6 passed in 32.41s           RED_EXIT=1 (pre-fix code)
       T-001 (spy 2 != 1), T-002 (spy != 0), T-007 (2.322s > 1.0s)
       6 pre-passed = regression guards (see §2.6)
GREEN: 9 passed in 2.41s                      GREEN_EXIT=0
Full suite (0001..0006): 98 passed in 6.26s   FULL_EXIT=0
Suite bound (Gate 1 §2.3): 6.26s <= 30s       PASS (was 47-50s)
Frozen-eval sha guard: all five prior evals match (0 edits)  PASS

identical probe as Gate 1 §2.2 (best of 3, warm, PROF_EXIT=0):
  measure                    before      after      factor
  validate-shaped K=10        17.3 ms     10.0 ms    (gone from wrapper path)
  full pool K=n (L=10)      2332.7 ms     70.0 ms    33.4x
  classify                     5.8 ms      5.8 ms    -
  wrapper K=10              2332.4 ms     71.4 ms    32.7x
  full pool K=n (L=60)      2222.9 ms     71.1 ms    31.3x
  wrapper L=60 K=10         2292.6 ms     83.4 ms    27.5x
  wrapper bound               <= 1.0 s     0.071 s   14x headroom
```

Anchors re-pass through the refactored paths inside this eval (T-005:
`2019-05-14 / 0.570966011106`, T-006: `2012-05-14 / 0.73704193241622`,
`p252 = 0.5476190476190477`), and the full suite — including every eval of
specs 0001–0005 — is green in the same run.

No test file or test spec was edited to achieve green; the sha guard in
`tests/test_0006.py` proves it mechanically on every subsequent run.
