# Gate 2 — Frozen Test Spec `0007-eod-snapshot`

**Status:** `PENDING USER FREEZE — authored 2026-10-06 (10 scenarios + six §0`
`interface freezes); every pin (file sha256, per-window anchors, slice-store`
`null-summary at all five windows) was probe-verified through the real seams`
`(0005 wrapper + 0004 reducer + frozen serialization) BEFORE authoring, per Gate 1`
`§4. This file becomes IMMUTABLE on approval and may never be edited to make`
`failing code pass. Only a user-directed revision may change it.`
**Date:** 2026-10-06
**Maps 1-to-1 to:** `specs/requirements/0007-eod-snapshot.md` (Gate 1, APPROVED
2026-10-06)
**Test file (Gate 3):** `tests/test_0007.py` (pytest)
**Import seam (frozen):** `from src.snapshot import build_snapshot`
(Gate 3 creates `src/snapshot.py` **only**; sources of specs 0001–0006 are
untouched, and this eval sha-pins all six prior test files — §0 freeze 4.)

---

## 0. Interface Freezes (clarifying details of the approved Gate 1)

1. **Module & constants:** the seam lives in `src/snapshot.py` with module-level
   `WINDOWS = (5, 10, 15, 30, 60)` and `K = 10` (Gate 1 §2.1 policy). Tests
   assert the *file's* window set and `k` — they do not import the constants
   (the artifact is the contract).
2. **Manifest (Gate 1 §2.1 returned “the manifest” unpinned — frozen here):**
   keys exactly `{"symbol", "path", "bytes", "last_date", "windows", "k"}`;
   `symbol` str; `path` str ending `f"{symbol}.json"`; `bytes` int equal to the
   file's size on disk; `last_date` str; `windows == [5, 10, 15, 30, 60]`;
   `k == 10`.
3. **Exact serialization (extends Gate 1 §2.4 to cross-platform byte-stability):**
   `open(path, "w", encoding="utf-8", newline="\n")`, then
   `json.dump(doc, fh, ensure_ascii=False)`, then `fh.write("\n")`. The trailing
   newline and `newline="\n"` (no CRLF translation on Windows) are load-bearing:
   the fixture file must hash to §0 freeze 4's sha.
4. **Frozen pins (probe-verified, PROBE_EXIT=0, 2026-10-06):**
   - Fixture file: **sha256 `fa4c598cf59c2f65ad7284b451c786280735a909d8e84a604dd789634b781897`**,
     **63,791 bytes**; `bars = 4673`, `last_date = "2026-10-05"`.
   - Top-1 anchors (date → distance, ±1e-6): L=5 `2011-06-21 → 0.6545378884539143`;
     L=10 `2012-05-14 → 0.73704193241622`; L=15 `2016-01-12 → 1.1565867903174754`;
     L=30 `2011-05-24 → 2.2385831629584225`; L=60 `2012-06-04 → 4.612532697912032`
     (every window returns `n = 10` analogs, `summary.n = 10`).
   - Regime: `bearish-normal`, `p252 = 0.5476190476190477` (≤1e-15).
   - Slice store (rows ≤ 2009-06-04): `bars = 416`, `last_date = "2009-06-04"`,
     `bullish-normal`, `p252 = 0.3492063492063492`, and **all five** windows
     `analogs = []` with `summary = null` (probe-confirmed at L=5/15/30 too).
   - Prior evals sha-pinned (autouse, extends 0006's guard to include 0006):
     `test_0001 804a090d…99a09c`, `test_0002 9a5ba0cb…f1cfc`, `test_0003 0b3d1c56…90c06d`,
     `test_0004 78d61847…94730`, `test_0005 a3769489…94213`,
     `test_0006 08f764b5797ca08bd99939ea7c673da47e152a2ad9da1efb592b07a994c05c35`
     (full digests in the test file, as in 0006).
5. **Tolerances:** byte-sha and counts exact; distances ±1e-6; `p252` ≤1e-15;
   JSON round-trip comparisons are **exact `==`** (Python's float repr round-trips;
   dict key order does not affect `==`).
6. **Store construction:** session fixtures — main store via `build_store` from
   the sha-guarded 0001 fixture; slice store from fixture rows `date ≤ 2009-06-04`
   (0005's `slice_dir` pattern); tiny error stores via `make_rows`.

**Eval conventions:**
- Runner: `python -m pytest tests/test_0007.py` from repo root (offline).
- Autouse guards: fixture sha256 `25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e`
  **and** the §0 freeze-4 prior-eval table.
- Rejections assert **both** `pytest.raises(ValueError)` **and** the frozen keyword
  (`store` / `regime` — Gate 1 §2.5).
- "Store read-back" = `pandas.read_parquet`; JSON read via `json.load` (utf-8).

---

## 1. Document Contract (fixture store)

**T-001 — Schema contract**
- *Given* the session store and a tmp `out_dir`,
- *When* `build_snapshot("^NSEI", store_dir, out_dir)` runs and the file is loaded,
- *Then* the document's keys are, in order, exactly
  `["schema", "symbol", "bars", "last_date", "regime", "windows"]`;
  `schema == "dtwmagic.api.v1"`, `symbol == "^NSEI"`, `bars == 4673`,
  `last_date == "2026-10-05"`; `list(windows) == ["5", "10", "15", "30", "60"]`
  (insertion order); and each block's keys are exactly
  `{"L", "k", "analogs", "summary"}` with `block["L"] == int(key)` and `k == 10`.

**T-002 — Top-level regime equals 0005's output**
- *Given* the same file,
- *When* `regime` is compared with a direct `search_analogs_regime("^NSEI", 10, 10, store_dir)["regime"]`,
- *Then* they are exactly equal, with `cell == "bearish-normal"` and
  `p252` within 1e-15 of `0.5476190476190477`.

**T-003 — Window contents equal direct wrapper calls**
- *Given* the file and the store,
- *When* each window's `analogs` is compared with
  `search_analogs_regime("^NSEI", L, 10, store_dir)["analogs"]`,
- *Then* all five are exactly equal (`==`) — 0003's payload values survive the
  JSON round-trip bit-for-bit (floats repr-round-trip), and each list has
  length 10 with `distance` non-decreasing.

**T-004 — Summary equals a fresh reduction; horizon-key contract**
- *Given* the file,
- *When* each window's `summary` is compared with
  `json.loads(json.dumps(summarize_analogs(direct_analogs)))`,
- *Then* all five match exactly; additionally `summary["n"] == 10`,
  `summary["horizons"] == [1, 2, …, 10]` (ints — it is a JSON array), while
  `cone` / `positive_frequency` / `mae` / `mfe` are keyed by the **strings**
  `"1"…"10"` (0004's ceiling made the frozen consumer contract).

**T-005 — Frozen anchors (all five windows)**
- *Given* the file,
- *When* each window's top analog is inspected,
- *Then* top-1 is exactly, distances within 1e-6: L=5 `2011-06-21 → 0.6545378884539143`,
  L=10 `2012-05-14 → 0.73704193241622`, L=15 `2016-01-12 → 1.1565867903174754`,
  L=30 `2011-05-24 → 2.2385831629584225`, L=60 `2012-06-04 → 4.612532697912032`.

---

## 2. Determinism & Byte Contract

**T-006 — Pinned bytes and byte-identical reruns**
- *Given* the fixture store,
- *When* `build_snapshot` runs twice into the same tmp `out_dir`,
- *Then* the file's sha256 equals the §0 freeze-4 pin
  `fa4c598cf59c2f65ad7284b451c786280735a909d8e84a604dd789634b781897`
  with size `63,791` bytes, both runs are byte-identical, and the store
  Parquet's sha256 is unchanged (read-only over 0001's output).

---

## 3. Edge Path (slice store, last session 2009-06-04)

**T-007 — Zero-pool day ships null summaries, never crashes**
- *Given* the slice store (416 rows),
- *When* `build_snapshot("SLICE", slice_dir, out_dir)` runs,
- *Then* no exception; the manifest satisfies §0 freeze 2 with
  `last_date == "2009-06-04"`; the document has `bars == 416` and regime
  `{"trend": "bullish", "volatility": "normal", "cell": "bullish-normal",
  "p252": 0.3492063492063492}` (±1e-15); and **for all five windows**
  `analogs == []` and `summary is None` — 0004's `ValueError` on empty input is
  converted into data, exactly as Gate 1 §2.3 froze.

---

## 4. Hygiene, Errors, Performance

**T-008 — Hermetic, read-only, out_dir auto-created**
- *Given* socket access monkeypatched to raise, the store sha captured, and an
  `out_dir` path that does not exist (`tmp_path/"deep"/"nested"`),
- *When* `build_snapshot` runs,
- *Then* it completes, the nested directory tree is created, the file exists at
  `out_dir/f"{symbol}.json"`, and the store Parquet's sha256 is unchanged.

**T-009 — Manifest contract**
- *Given* a successful call (fixture store),
- *When* the return value is inspected,
- *Then* its keys are exactly `{"symbol", "path", "bytes", "last_date",
  "windows", "k"}`; `symbol == "^NSEI"`; `path` is a str ending
  `"^NSEI.json"` and exists; `bytes ==` the file's `os.path.getsize`;
  `last_date == "2026-10-05"`; `windows == [5, 10, 15, 30, 60]`; `k == 10`.

**T-010 — Errors and perf**
- *Given* (a) a `symbol` with no parquet file → `ValueError` containing `store`;
  (b) a valid 251-row inline store → `ValueError` containing `regime`
  (0005's pass-through, Gate 1 §2.5), and (c) the fixture store timed
  best-of-3 after a warm-up,
- *When* each is exercised,
- *Then* the two keywords match, and `build_snapshot` completes within **2.0 s**
  (expected ≈ 0.4–0.6 s: five ~71 ms wrapper calls + reductions — non-SLA, 0001
  posture).

---

## 5. Coverage Map (requirement §2 → scenarios)

| Requirement rule | Scenarios |
|---|---|
| Seam + constants effect (windows set, K) (§2.1) | T-001, T-009 |
| Frozen document schema (§2.2) | T-001, T-002 |
| Regime computed once, L-independent (§2.2) | T-002 |
| Contents = verbatim 0005/0004 outputs (§2.2) | T-003, T-004 |
| `summary: null` on empty; horizon-key strings (§2.3) | T-004, T-007 |
| Serialization freeze + byte determinism (§2.4) | T-006 |
| Error pass-through `store`/`regime`; out_dir creation (§2.5) | T-008, T-010 |
| No new deps — stdlib `json` (§2.6) | — (nothing to approve) |
| Hermetic, read-only, ≲2 s sanity (§2.7) | T-006, T-008, T-010 |
| Zero-edits golden regression over 0001–0006 (§3) | §0 freeze 4 (autouse) |
| Anchors, incl. probe commitments L=5/15/30 (§4) | T-005, T-007 |

---

## 6. Gate 2 Sign-Off

- [ ] **User approves** this test spec **including the six §0 interface freezes**
      → it becomes **IMMUTABLE**; Gate 3 (TDD: Red → Green in `tests/test_0007.py`)
      may begin.

**STOP:** No `src/snapshot.py` may be written until the box above is checked by
the user.

**Revision log:** *(none — authored after every pin was probe-verified (PROBE_EXIT=0);
any future change must be a user-directed revision recorded here, like 0003 R1/R2,
0005 R1.)*
