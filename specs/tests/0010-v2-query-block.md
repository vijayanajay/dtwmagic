# Gate 2 — Test Spec `0010-v2-query-block`

**Status:** `FROZEN — approved by user 2026-10-07 ("Approve the Gate 2 freeze for spec 0010"); 10 scenarios + six §0 interface freezes; all pins probe-verified (PROBE_EXIT=0 / PROBE_B_EXIT=0); Gate 3 started. (Revision R1 applied 2026-10-07: T-009 frontend pin flipped to the post-switch state + test_0008 guard re-pin, user-directed via spec 0011 Gate 1 §2.9 — see Revision log.)`
**Date:** 2026-10-07
**Maps 1-to-1 to:** `specs/requirements/0010-v2-query-block.md` (Gate 1 approved
2026-10-07). Eval file: `tests/test_0010.py`.
**Probe posture:** every pin below was measured by running the real seams
(fixture store via `build_store` + `build_snapshot` + a §2.2-faithful v2
construction) **before** this spec was authored — `PROBE_EXIT=0` (content,
errors, determinism) and `PROBE_B_EXIT=0` (dual-build timing), 2026-10-07.
Probe cross-validated 0009's frozen v1 pin: the v1 fixture file re-hashed to
`fa4c598c…` / 63,791 bytes.

---

## 0. Interface Freezes (clarifying details of the approved Gate 1)

1. **Guard table (autouse):** both fixture shas **and all nine prior eval files**
   (`test_0001` … `test_0009`) — the established posture (0007 froze 6, 0009
   froze 7, 0008 froze 9). Full digests live in the test file. Fixture drift OR
   any prior-eval edit invalidates this eval.
   - `nifty50_daily_ohlcv.csv` = `25657e31…f7a93e`
   - `ind_close_all_20261005.csv` = `f0b8004e…bc9ba`
   - `test_0008.py` = `b90993e2…6cb68` (first time this digest is recorded),
     `test_0009.py` = `f693240c…bc7ec5`, `test_0001..0007` as pinned in 0009 §0.
2. **v2 document contract (Gate 1 §2.2):** top-level key order exactly
   `["schema","symbol","bars","last_date","regime","windows","query"]`;
   `schema == "dtwmagic.api.v2"`; `query` keys exactly `["L","candles"]` with
   `L == 60 == max(WINDOWS)`; each candle keys exactly
   `["date","open","high","low","close"]` (insertion order); ISO date strings;
   for the same store, `symbol/bars/last_date/regime/windows` **deep-equal** the
   v1 document — only `schema` and `query` differ (Gate 1 §2.2, §7 #3/#4).
3. **Content pins (fixture store, probe-verified):**
   - **v2 file:** sha256 `4994e3ff8c1c2723630e9321a182ea61b4d8b01cc10cef5fc07e7737cc97c88f`,
     **69,457 bytes**; determinism = two builds byte-identical.
   - **v1 file unchanged:** sha256 `fa4c598cf59c2f65ad7284b451c786280735a909d8e84a604dd789634b781897`,
     **63,791 bytes** (0009 §0 freeze 5 re-confirmed).
   - `bars == 4673`, `last_date == "2026-10-05"`, `len(candles) == 60`.
   - `candles[0] == {"date":"2026-07-10","open":24124.7,"high":24228.45,"low":24120.35,"close":24206.9}`
   - `candles[50] == {"date":"2026-09-21","open":23330.2,"high":23466.8,"low":23314.8,"close":23414.3}`
   - `candles[59] == {"date":"2026-10-05","open":22532.4,"high":22621.8,"low":22397.1,"close":22555.75}`
     (its `date == last_date` by Gate 1 §2.3).
   - **Slice store** (fixture rows ≤ 2009-06-04 → 416 rows, `SLICE`):
     `bars == 416`, `last_date == "2009-06-04"`, 60 candles,
     `candles[0] == {"date":"2009-03-03","open":2672.15,"high":2688.5,"low":2611.55,"close":2622.4}`,
     last candle date `2009-06-04`, **all five `summary` values `None`**,
     regime block present, no exception (Gate 1 §2.3).
4. **eod_job wiring (Gate 1 §2.6):** report key order stays exactly
   `[symbol, end_date, ok, refresh, snapshot, error]`; `snapshot` = the v1
   manifest (6 keys `{symbol,path,bytes,last_date,windows,k}`, `windows ==
   [5,10,15,30,60]`, `k == 10`) pointing at the **v1** file whose sha is the
   freeze-3 v1 pin; v2 file written at **`Path(snapshot_dir).parent / "v2" /
   f"{symbol}.json"`** (evals pass `tmp/api` → `tmp/v2/^NSEI.json`) and hashes
   to the freeze-3 v2 pin (refresh-built store is frame-equal to `build_store`
   per 0009 T-009 → same bytes); error strings byte-exact:
   `"snapshot: bars: store has 1 rows; window 5 needs >= 20"` (reused 0009 pin)
   and `"refresh: unknown symbol: '__NOPE__' (known: ['^NSEI'])"`; manifest
   assigned only after **both** builds succeed (any stage failure → `snapshot`
   is `None`); **no new CLI flags**; crontab docstring `30 17 * * 1-5` unchanged.
5. **Error contract (Gate 1 §2.5, probe-verified messages):**
   missing store → `ValueError` matching `store` ("store not found for symbol …");
   251-row store → `ValueError` matching `regime` ("regime: query session not
   classifiable; store has 251 rows, needs >= 252 …"); `out_dir` (even nested,
   missing) is created; I/O errors propagate as `OSError`.
6. **Tolerances & conventions:** byte-sha exact (no tolerance); floats exact
   under JSON round-trip; dates `"%Y-%m-%d"` strings; hermetic socket guard;
   performance: 0009's frozen `test_t010` bound **best-of-3 ≤ 3.0 s stays in
   force** (probe: faithful dual-build stage 1.029 s → est. full run ≈ 1.15 s);
   isolation: `data/static/index.html` references `./api/v2/` and
   **not** `api/v1` (R1 flip — spec 0011 Gate 1 §2.9 executed the frontend
   switch this freeze always said "belongs to spec 0011").

---

## 1. Scenarios (T-001 … T-010)

### T-001 — v2 schema & shared-part equality
- **Given** the fixture store built via `build_store` (no network).
- **When** `build_snapshot_v2("^NSEI", store, out)` is called.
- **Then** top-level keys are exactly the freeze-2 order with
  `schema == "dtwmagic.api.v2"`, and `symbol/bars/last_date/regime/windows`
  deep-equal a `build_snapshot` v1 document built from the same store in the
  same test.

### T-002 — query block shape & value pins
- **Given** the same fixture store.
- **When** the v2 file is `json.load`-ed.
- **Then** `query` keys are `["L","candles"]`, `L == 60`, `len(candles) == 60`,
  every candle has exactly `date/open/high/low/close` in that order, and
  `candles[0]`, `candles[50]`, `candles[59]` equal the freeze-3 dicts verbatim;
  `candles[59]["date"] == last_date == "2026-10-05"`; `bars == 4673`.

### T-003 — store-tail fidelity, manifest, read-only store
- **Given** the fixture store; its parquet sha is recorded before the call.
- **When** `build_snapshot_v2` runs.
- **Then** `candles` deep-equal the store's last 60 rows (dates via
  `strftime("%Y-%m-%d")`, prices as floats) — computed independently in the
  test from `pd.read_parquet`; the manifest satisfies the freeze-4 6-key shape
  with `bytes == file size`, `windows == [5,10,15,30,60]`, `k == 10`,
  `path` endswith `{symbol}.json` under `out`; the store parquet sha is
  unchanged.

### T-004 — byte determinism & file pins
- **Given** the fixture store.
- **When** `build_snapshot_v2` runs twice into fresh out dirs.
- **Then** both files are byte-identical and hash to the freeze-3 v2 sha
  (`…97c88f`) with size 69,457; a *different* store (slice, T-005) yields a
  different file; serialization is the frozen recipe (trailing newline, no
  indent) — raw bytes end with `}\n`.

### T-005 — zero-pool slice store
- **Given** the `SLICE` store (fixture rows ≤ 2009-06-04, 416 rows).
- **When** `build_snapshot_v2("SLICE", slice_dir, out)` is called.
- **Then** no exception; `bars == 416`, `last_date == "2009-06-04"`, all five
  windows have `analogs == []` and `summary == None`, the regime block is
  present, `schema` is v2, and the query block matches the freeze-3 slice pins
  (60 candles, first `2009-03-03`, last date `2009-06-04`).

### T-006 — error contract & out_dir creation
- **Given** a missing symbol and a 251-row `TINY` store.
- **When** `build_snapshot_v2` is called for each, and for a valid store into a
  deep missing `out` path.
- **Then** `ValueError` matching `store` for the missing store, `ValueError`
  matching `regime` for `TINY` (freeze 5 messages), and the deep `out` is
  created with a valid v2 file whose `path` points into it (Gate 1 §2.5).

### T-007 — nightly integration (success, both files, CLI)
- **Given** a seeded master ledger (fixture CSV), zero network (`calls == []`).
- **When** `run_eod_job(...)` runs with `snapshot_dir = tmp/api`.
- **Then** `ok is True`; report keys are exactly the freeze-4 order; the v1
  file hashes to the freeze-3 v1 pin (`fa4c598c…`, 63,791 B); **`tmp/v2/^NSEI.json`
  exists and hashes to the freeze-3 v2 pin**; `snapshot` manifest is the v1
  shape (freeze 4). CLI variant: `python -m src.eod_job` exits 0, prints exactly
  one JSON line, and the same two files exist under the given dirs.

### T-008 — stage honesty on failure (prior pins never touched)
- **Given** a first successful run (both files present, pins recorded).
- **When** a run fails at the snapshot stage (1-row store) and another fails at
  the refresh stage (fetch raises), plus an unknown-symbol run.
- **Then** each reports `ok is False`, `snapshot is None`, and the exact
  freeze-4 error strings; the previously written v1 **and** v2 files still hash
  to their freeze-3 pins; unknown-symbol run makes zero network calls.

### T-009 — hermetic, read-only, frontend isolation
- **Given** `socket.socket` monkeypatched to raise.
- **When** `run_eod_job` runs to success over the seeded ledger.
- **Then** no network was attempted; the store parquet bytes are unchanged
  after both builders; and `data/static/index.html` references
  `./api/v2/` with no `api/v1` occurrence (R1 flip — spec 0011 switched the
  frontend to the v2 seam; Gate 1 §7 #7 anticipated exactly this).

### T-010 — performance sanity (dual build within frozen budget)
- **Given** the seeded ledger and a warm-up run.
- **When** `run_eod_job` is timed 3× (best-of-3).
- **Then** best ≤ **3.0 s** (0009's frozen bound, unchanged — Gate 1 §2.8;
  probe estimate ≈ 1.15 s with the faithful dual-build stage at 1.029 s).

---

## 2. Traceability (Gate 1 clause → scenario/freeze)

| Gate 1 clause | Freeze / scenario |
|---|---|
| §2.1 seam + manifest shape | T-003, §0 freeze 4 |
| §2.2 schema, key order, row shape, shared-part equality | §0 freeze 2, T-001, T-002 |
| §2.3 edges (query unconditional, zero-pool, freshness) | §0 freeze 3 (slice pins), T-005 |
| §2.4 serialization & determinism | §0 freeze 3, T-004 |
| §2.5 error contract | §0 freeze 5, T-006 |
| §2.6 eod_job dual-write, frozen report, derived path, no new flags | §0 freeze 4, T-007, T-008 |
| §2.7 no new deps; §2.8 hermetic + perf | §0 freeze 1 (guards), §0 freeze 6, T-009, T-010 |
| §3 negative scope (no frontend edit, no v1 retirement) | §0 freeze 3 (v1 pin), §0 freeze 6, T-009 |
| §7 decisions #1–#8 | freezes 2/3/4/6 + T-001..T-010 as mapped above |
| Zero edits to 0001–0009 evals | §0 freeze 1 (autouse guard table) |

---

## 3. What this eval does NOT do

- **No frontend execution/JS** — `index.html` is text-checked only (0008's
  posture); rendering F-05 is spec 0011.
- **No network** — socket guard + recording `get` stub (0009's posture).
- **No edits to prior evals** — the guard table makes any such edit a failure,
  by design.
- **No content of its own beyond this contract** — it never re-derives search,
  regime, or stats math; it asserts documents, bytes, and wiring.

---

## 4. Gate 2 Sign-Off

- [x] **User approves** this test spec **including the six §0 interface freezes**
  (probe-verified pins in freeze 3; guard table in freeze 1) → file is **FROZEN
  and immutable**; agent may start Gate 3 (RED → GREEN in `tests/test_0010.py`).
  **(Approved 2026-10-07)**

**IMMUTABLE ONCE APPROVED:** a failing test means the *code* is fixed, never  this spec. Any post-freeze revision requires an explicit user directive and is
  logged in the Gate 4 record (precedent: spec 0008 R1).

**Revision log:**

- **R1 (2026-10-07, user-directed via spec 0011 Gate 1 §2.9):** T-009's frontend
  pin flips from "references ./api/v1/, no api/v2" to "references ./api/v2/,
  no api/v1", and `GUARD_SHAS["tests/test_0008.py"]` re-pins to that file's
  post-R2 digest `bafc6d0d…412a7fe` (0008's R2 changed its bytes). Reason:
  this freeze always named spec 0011 as the switch owner (§0 freeze 6 / Gate 1
  §7 #7); the isolation *intent* — the page consumes the JSON seam, never
  Python — is unchanged and still enforced by T-009's `ABSENT`-style checks in
  0008 and this eval's guard table. Cascade stops here: nothing pins
  test_0010.py. No backend pin, error string, sha, or scenario changed.
