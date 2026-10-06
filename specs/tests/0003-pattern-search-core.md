# Gate 2 — Frozen Test Spec `0003-pattern-search-core`

**Status:** `FROZEN — approved by user 2026-10-06 (19 scenarios + five §0 interface
freezes), including user-directed revision R1 (applied before any Gate 3 code
existed) and revision R2 (payload close key, 2026-10-06, pre-0004). This file is
IMMUTABLE; it may never be edited to make failing code pass. Only a user-directed
revision may change it.`
**Date:** 2026-10-06
**Maps 1-to-1 to:** `specs/requirements/0003-pattern-search-core.md` (Gate 1, APPROVED
2026-10-06, incl. §2.3 disjointness tightening)
**Test file (Gate 3):** `tests/test_0003.py` (pytest)
**Import seam (frozen):** `from src.pattern_search import search_analogs`
(Gate 3 creates `src/pattern_search.py`; `src/ohlcv_store.py` and `src/eod_fetch.py`
stay untouched. Tests also import `from src.ohlcv_store import build_store` to
construct stores in-test.)

---

## 0. Interface Freezes (clarifying details of the approved Gate 1)

These points are implied but not fully pinned by Gate 1; freezing them here makes the
eval deterministic. **They are surfaced for explicit approval with this spec:**

1. **Type strictness:** `L` and `K` must be `int` **excluding `bool`** (Python's
   `isinstance(True, int)` trap): `10.5`, `True`, `0`, `-1`, `4`, `61` are all rejected
   with the frozen keyword (`window` / `K`). `symbol` is a `str`; `parquet_dir`
   accepts `str` **or** `pathlib.Path`.
2. **Numeric tolerances:** reference cross-check |Δdistance| ≤ `1e-9` abs; score
   identity `score == 100/(1+distance)` within `1e-12` rel; pinned anchors (§1 T-005,
   §2) within `1e-6` abs.
3. **Reference implementation:** an independent **literal Python loop** written inside
   the test file itself — reads the store with `pandas.read_parquet` (**the read-back
   closes are the reference input**, never the source CSV), enumerates eligible starts,
   normalizes, computes `sqrt` of the summed squared diffs, sorts by `(distance, date)`.
   It must **not** import any helper from `src/`. Population std (**`ddof=0`**),
   `eps = 1e-8` — the sample-std (`ddof=1`) variant produces different distances and
   must fail the anchors.
   **Note (observed, load-bearing):** pandas' default `read_csv` float parser is **not
   correctly rounded** (1-ulp drift observed on this machine), so any in-test store
   scenario that requires *exact* float equality must be built from short decimal
   literals (e.g. constant closes), not from computed full-precision floats.
4. **Store construction:** the main store is built **once per session** via
   `build_store` from the 0001 fixture into `tmp_path_factory` (hermetic, no network).
   Tiny edge-case stores are generated in-test as valid inline CSVs under `tmp_path`
   and built through the same `build_store` seam (composition, never hand-written
   Parquet).
5. **Frozen facts (fixture n = 4,673, last row 2026-10-05):** eligible pool
   `n − 2L − 9` → L=5: **4654**, L=10: **4644**, L=60: **4544**; query start index
   `q0 = n − L`.

**Eval conventions:**
- Runner: `python -m pytest tests/test_0003.py` from repo root (offline).
- Happy-path store: committed fixture `tests/fixtures/nifty50_daily_ohlcv.csv`
  (sha256 `25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e` —
  same file as 0001/0002; **no new fixture is created for 0003**). Any drift in that
  hash invalidates this eval (autouse guard on every test).
- Every rejection scenario asserts **both** `pytest.raises(ValueError)` **and** a
  non-empty message containing the frozen keyword substring from requirement §2.5
  (`store` / `window` / `K` / `bars`).
- "Store read-back" means `pandas.read_parquet` of the built store.

---

## 1. Happy Path (fixture store, L=10, K=10)

**T-001 — Payload contract**
- *Given* the session store built from the fixture,
- *When* `search_analogs("^NSEI", 10, 10, store_dir)` is called,
- *Then* the result is a `list` of length ≤ 10; each element is a `dict` with keys
  **exactly** `{"date","distance","score","close","forward"}` (no extras; `close`
  added by Revision R2); `date` is an ISO
  `YYYY-MM-DD` string; `distance`, `score` and `close` are floats; `forward` is a list of
  **exactly 10** dicts with keys **exactly**
  `{"date","open","high","low","close"}`, dates strictly ascending ISO, prices floats;
  and `distance` is non-decreasing across the list.

**T-002 — Score identity**
- *Given* T-001's result,
- *When* each item is checked,
- *Then* `score ≈ 100 / (1 + distance)` within `1e-12` relative for every item.

**T-003 — Eligibility rule (§2.3 strict disjointness)**
- *Given* T-001's result and the store's date index,
- *When* each item's `date` is mapped to its store index `i` (τ_k),
- *Then* window start `s = i − L + 1` satisfies `0 ≤ s ≤ n − 2L − 10`, the last
  forward bar `i + 10 < q0` (strictly before the query window's first bar), the
  reference enumerator finds exactly `n − 2L − 9 = 4644` eligible candidates, and
  **no result `date` falls inside the query window** (the query is never its own
  analog).

**T-004 — Independent reference cross-check**
- *Given* the in-test literal reference (§0 freeze 3) run at `L=10`,
- *When* its top-K ordering is compared with `search_analogs("^NSEI", 10, 10, ...)`,
- *Then* both lists carry the same `date` sequence in the same order and pairwise
  distances agree within `1e-9` absolute.

**T-005 — Frozen anchors (drift guard for the math convention)**
- *Given* the fixture store at `L=10, K=10`,
- *When* the top-3 results are inspected,
- *Then* they are exactly, in order, with distances within `1e-6`:
  1. `2019-05-14` → `distance = 0.570966011106`
  2. `2020-03-20` → `distance = 0.659910750504`
  3. `2018-05-24` → `distance = 0.668395481286`
  (These pins fail if the ε/population-std convention or the fixture changes.)

**T-006 — Forward path equals the store (composition with 0001)**
- *Given* the top-1 result of T-001 (date τ),
- *When* its `forward` list is compared with the store's rows `τ+1 … τ+10`,
- *Then* all 10 `date` values match exactly and each `open,high,low,close` equals the
  read-back store value (float64 precision); volume is absent from the payload.

**T-007 — Determinism**
- *Given* the same store,
- *When* `search_analogs("^NSEI", 10, 10, store_dir)` is called twice,
- *Then* both results are content-equal (same dates, distances, scores, forward rows).

**T-008 — K is a cap, not a repartition**
- *Given* the fixture store,
- *When* results for `K=10`, `K=3`, and `K=1` are compared,
- *Then* `K=3` equals the first 3 items of `K=10` exactly, `K=1` equals the first item,
  and no call errors.

**T-009 — Hermetic and read-only**
- *Given* socket access monkeypatched to raise on any use, and the store Parquet's
  sha256 captured before the call,
- *When* `search_analogs` runs on the fixture store,
- *Then* it completes successfully and the store file's sha256 is **unchanged**
  (no network, no writes).

**T-010 — Performance sanity (non-SLA)**
- *Given* the fixture store (n = 4,673),
- *When* a `L=10, K=10` call runs,
- *Then* wall-clock is `< 5.0 s` (generous bound encoding Gate 1's "≲1 s sanity, not
  an SLA"; reference probe measures ≈ 0.1 s).

---

## 2. Parameterization (window length L)

**T-011 — L=60 (long window)**
- *Given* the fixture store,
- *When* `search_analogs("^NSEI", 60, 10, store_dir)` runs,
- *Then* the reference enumerator finds `4544` eligible candidates (pool
  `n − 2L − 9 = 4544`), the top-1 result is date `2018-10-29` with
  `distance ≈ 2.581337345431` (±1e-6), every item still carries exactly 10 forward
  bars with `i + 10 < q0 = n − 60`, and ordering matches the in-test reference within
  `1e-9`.

**T-012 — L=5 (lower boundary)**
- *Given* the fixture store,
- *When* `search_analogs("^NSEI", 5, 10, store_dir)` runs,
- *Then* pool = `4654`, top-1 is date `2018-09-25` with `distance ≈ 0.164200033042`
  (±1e-6), contract of T-001 holds, and the eligibility rule holds with
  `q0 = n − 5`.

---

## 3. Edge Pools (tiny in-test stores, L=10)

**T-013 — Short pool returns everything, no error**
- *Given* a valid in-test store with **exactly 30 rows** (`2L + 10`),
- *When* `search_analogs(sym, 10, 10, tmp_store)` runs,
- *Then* it returns **exactly 1** item (the whole pool, `K` is a cap), with 10
  forward bars all strictly before `q0 = 20`, and no exception.

**T-014 — Empty pool rejected**
- *Given* a valid in-test store with **29 rows** (`< 2L + 10`),
- *When* `search_analogs(sym, 10, 10, tmp_store)` runs,
- *Then* `ValueError` whose message contains `bars`.

---

## 4. Rejections (each: `pytest.raises(ValueError)` + frozen keyword)

**T-015 — Missing store:** `symbol` with no `{parquet_dir}/{symbol}.parquet` file →
message contains `store`.
**T-016 — Window bounds:** `L=4` and `L=61` → message contains `window`.
**T-017 — Window types:** `L=10.5` (float) and `L=True` (bool) → message contains
`window`.
**T-018 — K values:** `K=0`, `K=-1`, `K=1.5`, `K=True` → message contains `K`.

---

## 5. Deterministic Ordering

**T-019 — Exact tie broken by earlier date (also pins the σ=0 flat-window rule)**
- *Given* a valid in-test store of 40 rows with daily ISO dates starting
  `2024-01-01`, closes: rows 0–9 constant `100.0`, rows 10–19 constant `50.0`
  (both short decimals → parse exactly), rows 20–39 varying non-flat prices;
  query = rows 30–39. The two flat windows sit at eligible starts `s=0` and `s=10`,
  both σ=0 → z-normalize to the all-zero vector → **exactly equal distances**,
- *When* `search_analogs(sym, 10, 11, tmp_store)` runs (K = full pool of 11),
- *Then* both tied dates `2024-01-10` and `2024-01-20` appear in the result, their
  `distance` values are exactly equal (`==`, probe: `3.1622748239264022`), they are
  adjacent in the list, and the **earlier `date` precedes the later one** — proving
  the `(distance, date)` sort key, not insertion order, plus the Gate 1 §2.2
  flat-window rule (σ=0 → zero vector, valid data).

---

## 6. Coverage Map (requirement §2 → scenarios)

| Requirement rule | Scenarios |
|---|---|
| Seam signature + list/dict return (§2.1) | T-001, T-008 |
| All four args, no defaults | T-008, T-016, T-018 |
| z-normalization math, population σ, ε=1e-8 (§2.2) | T-004, T-005, T-011, T-012 |
| Euclidean only / score `100/(1+d)` (§2.2) | T-002, T-004 |
| Eligibility: disjoint window+forward, pool formula (§2.3) | T-003, T-011, T-012, T-013, T-014 |
| Payload keys, 10 forward rows, no volume (§2.4) | T-001, T-006 |
| Ordering + tie-break (§2.4) | T-001, T-004, T-019 |
| Errors `store`/`window`/`K`/`bars`; short pool OK (§2.5) | T-014, T-015, T-016, T-017, T-018, T-013 |
| No new deps (§2.6) | — (pytest/pandas/pyarrow already installed) |
| Hermetic, fixture reuse, ≲1 s sanity (§2.7) | T-009, T-010 |
| Composition with 0001 store (§5) | T-006, T-009, T-013 |

---

## 7. Gate 2 Sign-Off

- [x] **User approves** this test spec **including the five §0 interface freezes** →
      it becomes **IMMUTABLE**; Gate 3 (TDD: Red → Green in `tests/test_0003.py`)
      may begin. **(Approved 2026-10-06)**

**STOP:** No code in `src/pattern_search.py` may be written until the box above is
checked by the user.

**Revision log:**
- **R1 (2026-10-06, user-directed, applied before any Gate 3 code existed):** T-011
  arithmetic typo corrected `4654 → 4544` → `4544` (4654 is T-012's L=5 pool; for
  L=60 the frozen formula `n − 2L − 9` gives 4544). Scenario structure and all other
  assertions unchanged.
- **R2 (2026-10-06, user-directed, precondition for spec 0004):** each result element
  gains the key `close` (p_tau — the analog's own last-session close, the baseline
  spec 0004's returns/MAE/MFE are relative to). T-001's exact key set and T-006
  (baseline equals the store's close at tau) updated to match; distances, ordering,
  eligibility, and every other assertion unchanged. All 19 evals re-ran green.
