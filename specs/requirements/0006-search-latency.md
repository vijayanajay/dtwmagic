# Gate 1 — Requirement Spec `0006-search-latency`

**Status:** `APPROVED — Gate 1 signed off 2026-10-06 (user: “Approve Gate 1 for spec`
`0006”); Gate 2 test spec in authoring; Gate 3 not started.`
**Date:** 2026-10-06
**Consumes:** specs `0003-pattern-search-core` (its payload loop is the measured hot
spot; source-level refactor only — signature, semantics, and all 19 frozen evals
untouched) and `0005-regime-conditioning` (the wrapper becomes single-pass; its 17
frozen evals untouched). Specs 0001/0002/0004 are unaffected.
**Preceded by:** profile probe session (cProfile + wall-clock, below in §2.2) —
scope was pivoted on evidence, see §7 #1.

---

## 0. Gate 1 User-Value Flag

> **No waiver needed — latency is trader-facing.** The motivating symptom was the
> dev suite (50 s), which alone would be engineering value and flag-worthy. But the
> same measurements show the **product itself** pays this cost: every live
> `search_analogs_regime` call — the seam a Phase-1 dashboard query hits — takes
> **2.33 s**, blowing BRD §7.1's page-load budget (≤ 300 ms first meaningful paint)
> by ~8×. Search response time is the core interaction of F-01/F-02; making it
> ~5–15× faster is direct user value. The suite speedup rides along for free.

---

## 1. User Value Rationale (DIRECT — latency)

- **Why a paying trader cares:** the dashboard's central act is *run a search, see
  analogs*. Today the wrapper answers in **2.33 s** on the fixture store (probe,
  best-of-3). After this spec: **≤ 1.0 s** frozen bound (expected ≈ 0.2–0.4 s).
  BRD §7.1 sets ≤ 300 ms frontend load and ≤ 15 ms for *precomputed* endpoints;
  live Phase-1 compute cannot hit the API number (that is Phase 2's static-JSON
  job), but it can stop being the thing the trader waits on.
- **Phase-2 batch headroom:** the same waste multiplies by 2,000 stocks in the
  BRD §4.2 nightly job (≤ 90 s budget) — payload materialization for discarded
  candidates is exactly the cost the batch cannot afford.
- **Engineering loop (secondary, honest):** full suite 50 s → target ≤ 30 s,
  halving feedback time for every future spec.

---

## 2. What Is Needed (Scope)

### 2.1 Two surgical fixes, zero contract changes

| Fix | File | What changes | What must not change |
|---|---|---|---|
| **A — payload materialization** (the measured 95%) | `src/pattern_search.py` | The payload listcomp's per-row `df.iloc[...] .iterrows()` (51,084 Series constructions per full-pool call) is replaced by column-array indexing over hoisted `float64` arrays + the existing ISO `dates` array | `search_analogs` signature, ordering, tie-break, every payload value **bit-identical** to the read-back store (pinned by 0003's 19 frozen evals) |
| **B — single-pass wrapper** (the literal ask) | `src/regime.py` | The discarded pass-through call `search_analogs(symbol, L, K, ...)` is replaced by **inline `window` + `K` checks** mirroring 0003's frozen rules/messages verbatim; then **one** `search_analogs(symbol, L, n, ...)` call does the distance work and raises `bars`; then the `regime` gate | Frozen validation order `store → window → K → bars → regime`; error keywords; results identical to the current wrapper (17 frozen evals) |

### 2.2 Evidence (profile probe, fixture store, 2026-10-06)

```
wall-clock, best of 3 (data/parquet/^NSEI.parquet, n=4673, L=10):
  validate-shaped call  search_analogs(K=10)      17.3 ms   <- the "double computation"
  full pool            search_analogs(K=n)     2332.7 ms
  classify (_classify)                       5.8 ms
  wrapper               search_analogs_regime  2332.4 ms  ~= full pool (rest is noise)

cProfile of one full-pool call (6.32 s under instrumentation):
  pattern_search.py:75 listcomp (payload build)  5.995 s cumulative = 95%
  pandas iterrows x 51,084                       4.275 s cumulative
  distance/z-norm/sort + everything else         ~0.3 s
```

**Conclusion that defines this spec's scope:** eliminating the double *distance*
computation (Fix B) is worth ~17 ms (0.7%) — it is done because it was asked for
and is free, but **the halving is only honest with Fix A**, which eliminates the
payload materialization for candidates the wrapper discards (Fix A also speeds up
0003's own frozen tests, which call the full pool directly — those calls are
immutable and set the suite floor).

### 2.3 Measured targets (Gate 2 freezes exact bounds; not SLAs)

- Wrapper `search_analogs_regime` fixture call: **≤ 1.0 s** (baseline 2.332 s;
  expected ≈ 0.2–0.4 s after A+B).
- **Exactly 1** `search_analogs` invocation per wrapper call — assertable by
  monkeypatching the name bound in `src.regime` with a counting spy
  (machine-independent, encodes "no double computation" as behavior).
- Full suite (`pytest -q`): **≤ 30 s** (baseline 47–50 s; floor ≈ 8–15 s set by
  frozen tests' own direct full-pool calls).
- T-009's existing `< 5.0 s` bound unchanged and still green.

### 2.4 Golden regression (the load-bearing requirement)

**All 89 frozen evals of specs 0001–0005 pass with ZERO edits to any test file or
test spec.** The refactor's correctness is enforced entirely by contracts written
before this spec existed: 0003's payload exact-float pins, 0005's T-004
bitwise-identity between wrapper and `search_analogs` output, T-015/T-016 error
order/keywords, T-007 determinism.

### 2.5 Dependencies

**None new.**

---

## 3. What Is NOT Needed (Negative Scope)

- **No new API seams** — the alternative "rank-only function in `pattern_search`
  + wrapper builds survivor payloads" was rejected (§7 #2): it duplicates payload
  construction across two modules.
- **No caching/memoization** — that is 0003's separate documented ceiling
  (per `(symbol, L)` replay for the screener); statefulness + staleness risk is
  not worth it here.
- **No edits to any test file or test spec** of 0001–0005 (the golden regression
  rule), **no fixture changes**, **no store format changes**.
- **No rule changes:** window/K/bars/`regime` rules and messages stay byte-for-byte
  equivalent (0005's T-016/T-015 pin the keywords; 0003's T-015..T-018 pin its side).
- **No payload format changes, no rounding, no parallelism, no async, no new deps.**
- **No regime/score/math changes** — distances, cells, pools stay bit-identical.

---

## 4. Acceptance Summary (for Gate 2 authoring; the test spec freezes the details)

- Spy: one wrapper call ⇒ **exactly 1** `search_analogs` invocation (K = n),
  validated order: an invalid `L` on a store-missing path still reports `store`
  first; `L=61` ⇒ `window` (now inline); `n=29` ⇒ `bars` (now via the single
  call); `n=40` ⇒ `regime` — T-015/T-016 scenarios re-pass **unmodified**.
- Payload bit-identity after Fix A: wrapper/`search_analogs` outputs deep-equal to
  their pre-refactor values (0003's pinned anchors `2019-05-14 / 0.570966011106`
  etc. and 0005's `2012-05-14 / 0.73704193241622` etc. all re-pass at 1e-6).
- Perf bounds per §2.3 measured on the fixture store, best-of-3, generous margins.
- Full suite ≤ 30 s, 89/89 green, `git status` clean of test edits.

---

## 5. Architecture Alignment (Kailash Nadh)

- **Measure first, then cut:** the scope pivot (§7 #1) is the spec — the original
  ceiling's wording would have shipped a 0.7% "fix" branded as a halving.
- **Smallest diff that hits the data:** one loop swapped for array indexing; six
  lines inlined in the wrapper. No classes, no new modules, no deps (rung 6).
- **Closed-spec sources are not sacred, frozen tests are:** 0003's module changes
  only where its own 19 evals can prove behavior identical — the evals, not the
  file's age, are the contract.

---

## 6. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is building payloads for all n candidates in the full-pool
  call; upgrade path is a rank-only seam + survivor-only payload build (wrapper
  ~50 ms) once a consumer needs it — rejected now as payload-logic duplication.`
- `# ponytail: ceiling is suite floor from frozen tests' own direct full-pool
  calls; reaching < 8 s requires editing frozen evals — forbidden.`
- `# ponytail: ceiling is single-process, no caching; upgrade path is 0003's
  per-(symbol, L) memo when the screener replays queries.`

---

## 7. Frozen Decisions (from the pre-Gate-1 profile session)

| # | Decision | Choice |
|---|---|---|
| 1 | Scope pivot on evidence | The requested "eliminate double distance computation" is worth **17 ms (0.7%)**; payload materialization is **95%**. Spec does **both** (B as asked, A to actually halve) and the Gate 1/2/4 records keep the numbers visible so no one later credits the wrong fix |
| 2 | Mechanism for A | **In-place payload loop refactor** (column arrays) — rejected: rank-only seam + wrapper payloads (duplicates payload logic), memoization (statefulness; separate 0003 ceiling), `iterrows → itertuples` alone (same shape, less clear than plain arrays) |
| 3 | Touching closed spec 0003 | Allowed as a **behavior-neutral source refactor**; correctness enforced by re-running its 19 frozen evals + the full 89 — frozen tests are the contract, source files are not |
| 4 | Mechanism for B | Inline `window`/`K` mirrors of 0003's frozen rules + single `search_analogs(K=n)` for `bars` + `regime` gate — preserves the frozen order exactly; rejected: manual `bars` duplication (third copy of a rule) and validating with the user's `K` (forces the second call back) |
| 5 | Perf claims | Generous bounded targets (≤ 1.0 s wrapper, ≤ 30 s suite), best-of-3 on the fixture, explicitly **not SLAs** (0001 posture); plus the machine-independent spy count = 1 |
| 6 | Golden regression | **Zero edits** to any test file or test spec of 0001–0005; if a frozen eval fails, the refactor is wrong — never the eval |

---

## 8. Gate 1 Sign-Off

- [x] **User approves** this requirement spec (incl. the §2.2 evidence-based scope
      pivot, Fix A touching `src/pattern_search.py`'s payload loop, and the §2.3
      perf bounds) → agent may author Gate 2 test spec
      `specs/tests/0006-search-latency.md`. **(Approved 2026-10-06)**
- [x] **No new dependency requested** (§2.5) — nothing to approve. **(Approved
      2026-10-06)**

**STOP:** No Gate 2 or Gate 3 work proceeds until the box above is checked by the
user. The test spec is **IMMUTABLE once approved**; Gate 3 (code) still requires
that separate approval.
