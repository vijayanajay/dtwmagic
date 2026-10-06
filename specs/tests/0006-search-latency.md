# Gate 2 — Frozen Test Spec `0006-search-latency`

**Status:** `FROZEN — approved by user 2026-10-06 (“Approve Gate 2 freeze for spec`
`0006”); 9 scenarios + five §0 interface freezes; baselines/pins come from the`
`Gate 1 §2.2 profile probe (PROF_EXIT=0). This file is IMMUTABLE; it may never be`
`edited to make failing code pass. Only a user-directed revision may change it.`
**Date:** 2026-10-06
**Maps 1-to-1 to:** `specs/requirements/0006-search-latency.md` (Gate 1, APPROVED
2026-10-06)
**Test file (Gate 3):** `tests/test_0006.py` (pytest)
**Import seams (frozen):** `from src.regime import search_analogs_regime`,
`from src.pattern_search import search_analogs`, `from src.ohlcv_store import build_store`
(Gate 3 modifies **only** the payload loop of `src/pattern_search.py` and the body
of `src/regime.py`, exactly per Gate 1 §2.1. No other source file, **no test file
of specs 0001–0005, no test spec** may change — enforced by §0 freeze 2.)

---

## 0. Interface Freezes (clarifying details of the approved Gate 1)

1. **Spy seam (encodes “exactly one computation”):** tests monkeypatch the name
   `search_analogs` **as bound in `src.regime`'s namespace**
   (`monkeypatch.setattr("src.regime.search_analogs", spy)` where `spy` counts the
   call and forwards to the real function). Counts are per-`search_analogs_regime`
   invocation; the success-path assertion is `count == 1` **and** the call's third
   positional argument `== n` (the full-pool request, Gate 1 §2.1 Fix B).
2. **Frozen-eval integrity guard (autouse):** sha256 of every prior eval file must
   match — this operationalizes Gate 1 §2.4's “zero edits” golden regression:
   | File | sha256 |
   |---|---|
   | `tests/test_0001.py` | `804a090d4db3b1ce9e37a6f186e6fefaf1966b69078daf5d128820725f99a09c` |
   | `tests/test_0002.py` | `9a5ba0cb6f88b6948c0b5a6c4cecfa2289cea583a5201065bf13f6e1927f1cfc` |
   | `tests/test_0003.py` | `0b3d1c560a68f538a1800d3bab0fc55adca951f7e986531694809f5d6490c06d` |
   | `tests/test_0004.py` | `78d6184716ac333460c01565bd9db83be3d18855ea27048925e984906ab94730` |
   | `tests/test_0005.py` | `a3769489f4a9b75ab9b507a91822593579c658979f2ea33f68d60caf92a94213` |
   (Post-R1 state of `test_0005.py`. Guard updates only via a user-directed
   revision logged in this file's revision log.)
3. **Perf methodology:** fixture store; `time.perf_counter`, **best of 3** after
   one warm-up call; bounds (generous, **not SLAs** — 0001 posture):
   full-pool `search_analogs("^NSEI", 10, 4673, store)` **≤ 1.0 s**; wrapper
   `search_analogs_regime("^NSEI", 10, 10, store)` **≤ 1.0 s**. Baselines that must
   stop being true: **2.332 s** each (probe). The **≤ 30 s full-suite** bound
   (baseline 47–50 s) is recorded in Gate 4's verification output — a test cannot
   meaningfully assert the duration of the run it belongs to.
4. **Payload value types (tightening 0003's `isinstance`, surfaced for approval):**
   payload numbers are **builtin** `float` — `type(v) is float` (no numpy scalar
   leakage; keeps 0007's JSON serialization honest) — dates are ISO `str`, sizes
   per 0003 §2.4.
5. **Store construction:** session store built once via `build_store` from the
   sha-guarded 0001 fixture; tiny error-path stores generated inline (0005's
   `make_rows` pattern: valid CSV → `build_store`, never hand-written Parquet).

**Eval conventions:**
- Runner: `python -m pytest tests/test_0006.py` from repo root (offline).
- Autouse guards: fixture sha256 `25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e`
  **and** the §0 freeze-2 eval-file table.
- Rejections assert **both** `pytest.raises(ValueError)` **and** the frozen keyword
  (`store` / `window` / `K` / `bars` / `regime`).
- “Store read-back” = `pandas.read_parquet` of the built store.

---

## 1. Single-Pass Behavior (Fix B)

**T-001 — Success path computes exactly once**
- *Given* the spy installed over `src.regime.search_analogs` and the fixture store,
- *When* `search_analogs_regime("^NSEI", 10, 10, store_dir)` runs,
- *Then* the spy recorded **exactly 1** call, its third positional argument equals
  `n = 4673`, the result has keys exactly `{"regime", "analogs"}` with
  `len(analogs) == 10`, and the regime block equals the 0005 contract
  (`bearish-normal`, `p252` within 1e-15 of `0.5476190476190477`).

**T-002 — Frozen validations short-circuit without reaching the search**
- *Given* the spy and (a) a missing symbol, (b) `L=61`, (c) `L=True`, (d) `K=0`,
  (e) `K=-1`,
- *When* each call is made on the fixture store directory,
- *Then* each raises `ValueError` with keywords `store` / `window` / `window` /
  `K` / `K` respectively, and the spy count is **0** for every case — no
  computation is spent on arguments that cannot run (Gate 1 §2.1 Fix B: inline
  `window`/`K` checks precede the single pool call).

**T-003 — bars and regime keep their frozen order and counts**
- *Given* the spy and tiny inline stores (0005 `make_rows` pattern),
- *When* `search_analogs_regime("TINY", 10, 10, ...)` runs on a **29-row** store,
  then on a **40-row** store,
- *Then* the 29-row call raises `ValueError` containing **`bars`** with spy count
  **1** (the single call is what reports `bars`), and the 40-row call raises
  containing **`regime`** with spy count **1** (call succeeded, then the regime
  gate fired) — Gate 1's frozen order `store → window → K → bars → regime`.

---

## 2. Payload Integrity (Fix A)

**T-004 — Payload bit-identity and builtin-float types after the refactor**
- *Given* the fixture store,
- *When* `search_analogs("^NSEI", 10, 4673, store_dir)` returns the full pool
  (`len == 4644`),
- *Then* for the first 3, middle 3 (indices 2321–2323), and last 3 items, plus
  every item the wrapper returns: `type(distance) is float` and `type(score) is
  float`; `type(close) is float` and `close` **exactly equals** the read-back
  store close at `τ`; `forward` has exactly 10 ISO-`str` dates ascending; each
  `open/high/low/close` satisfies `type(...) is float` and **exactly equals** the
  read-back store value for that row (bitwise, no 1-ulp drift) — the same
  contract 0003's T-006 pinned pre-refactor, now sampled across the pool.

**T-005 — 0003's frozen search anchors survive the refactored path**
- *Given* the fixture store at `L=10, K=10`,
- *When* the top-3 of `search_analogs` are inspected,
- *Then* they are exactly, distances within **1e-6**:
  `2019-05-14 → 0.570966011106`, `2020-03-20 → 0.659910750504`,
  `2018-05-24 → 0.668395481286`; `score ≈ 100/(1+distance)` within 1e-12; and
  `distance` is non-decreasing (order and tie-break untouched).

**T-006 — Wrapper anchors unchanged through the single-pass path**
- *Given* the fixture store at `L=10, K=10`,
- *When* `search_analogs_regime(...)` runs,
- *Then* the top in-regime analog is `2012-05-14 → distance 0.73704193241622`
  (±1e-6), `len(analogs) == 10`, and the regime block matches T-001 — proving the
  filter and its inputs are bit-identical to the 0005-era behavior.

---

## 3. Performance & Hygiene

**T-007 — Frozen perf bounds (best of 3, warm-up first)**
- *Given* the fixture store,
- *When* `search_analogs("^NSEI", 10, 4673, store)` and then
  `search_analogs_regime("^NSEI", 10, 10, store)` are each timed,
- *Then* each completes within **1.0 s** (baselines 2.332 s — pre-refactor code
  fails this by >2×; expected post-fix ≈ 0.1–0.4 s gives ≥2.5× headroom).

**T-008 — Determinism**
- *Given* the fixture store,
- *When* the wrapper and the full-pool call are each run twice,
- *Then* all four results are content-equal to their twins (the refactor changed
  no value, no order, no tie-break).

**T-009 — Hermetic and read-only**
- *Given* socket access monkeypatched to raise, and the store Parquet's sha256
  captured before the calls,
- *When* the wrapper and the full-pool call run (spy installed or not),
- *Then* both complete, the store sha256 is **unchanged**, and the spy pattern
  shows no hidden state — no network, no writes, no caching side effects.

---

## 4. Coverage Map (requirement §2 → scenarios)

| Requirement rule | Scenarios |
|---|---|
| Fix B: one `search_analogs(K=n)` per wrapper call, spy count = 1 (§2.1, §2.3) | T-001, T-002, T-003 |
| Validation order `store → window → K → bars → regime` preserved (§2.1) | T-002, T-003 |
| Fix A: payload bit-identity + builtin floats (§2.1, §0 freeze 4) | T-004, T-005, T-006 |
| Frozen 0003/0005 anchors re-pass through new paths (§2.4) | T-005, T-006 |
| Zero edits to prior evals — sha guard (§2.4) | §0 freeze 2 (autouse) |
| Perf bounds: wrapper ≤ 1.0 s, full pool ≤ 1.0 s (§2.3) | T-007 |
| Suite ≤ 30 s (§2.3) | Gate 4 verification output (not self-assertable) |
| Determinism, read-only, no deps (§2.4, §2.5, §3) | T-008, T-009 |

---

## 5. Gate 2 Sign-Off

- [x] **User approves** this test spec **including the five §0 interface freezes**
      → it is **IMMUTABLE**; Gate 3 (TDD: Red → Green in `tests/test_0006.py`)
      may begin. **(Approved 2026-10-06)**

**STOP:** No change to `src/pattern_search.py` or `src/regime.py` may be made
until the box above is checked by the user.

**Revision log:** *(none — authored after all baselines/pins came from the Gate 1
§2.2 profile probe; any future change must be a user-directed revision recorded
here, like 0003 R1/R2 and 0005 R1.)*
