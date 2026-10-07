# Gate 2 — Frozen Test Spec `0009-eod-nightly-job`

**Status:** `FROZEN — approved by user 2026-10-07 ("Approve the Gate 2 freeze for`
`spec 0009"); 10 scenarios + six §0 interface freezes; all pins probe-verified`
`(final PROBE_EXIT=0) before authoring. This file is IMMUTABLE; it may never be`
`edited to make failing code pass. Only a user-directed revision may change it.`
**Date:** 2026-10-07
**Maps 1-to-1 to:** `specs/requirements/0009-eod-nightly-job.md` (Gate 1, APPROVED
2026-10-07)
**Test file (Gate 3):** `tests/test_0009.py` (pytest)
**Import seam (frozen):** `from src.eod_job import run_eod_job`
(Gate 3 creates `src/eod_job.py` **only**; sources of specs 0001–0007 are untouched,
and this eval sha-pins all seven prior test files — §0 freeze 1.)

---

## 0. Interface Freezes (clarifying details of the approved Gate 1)

1. **File boundary + prior-eval pins (autouse, extends 0007's guard):**
   `test_0001 804a090d…99a09c`, `test_0002 9a5ba0cb…f1cfc`, `test_0003 0b3d1c56…90c06d`,
   `test_0004 78d61847…94730`, `test_0005 a3769489…94213`,
   `test_0006 08f764b5797ca08bd99939ea7c673da47e152a2ad9da1efb592b07a994c05c35`,
   `test_0007 e6295aa53c5aa300ade0ba64ec32b10335a2730fab0ea80ac6c5a742ba79867c`
   (full digests in the test file, as in 0007). Fixture shas re-pinned:
   `nifty50_daily_ohlcv.csv 25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e`,
   `ind_close_all_20261005.csv f0b8004e9bc79b11cff3c939cb42cdeb4a31b71ebd03942b98b57f44fa3bc9ba`.
2. **Function signature (Gate 1 §2.1, names/order frozen):**
   `run_eod_job(symbol, start_date, end_date, parquet_dir, snapshot_dir, get=...)`
   — six parameters in that order; `get` is keyword-usable and defaults to
   `src.eod_fetch._real_get`. `end_date=None` is resolved **by the job itself** to
   `date.today().isoformat()` *before* delegating, and the resolved string is what
   appears in the report (the report's `end_date` is always an ISO str).
3. **Report contract (Gate 1 §2.2, six keys frozen with insertion order):**
   keys exactly, in order, `["symbol", "end_date", "ok", "refresh", "snapshot",
   "error"]`; `symbol` str == the call's symbol; `ok` bool; `refresh` is the **verbatim**
   0001 manifest (keys `{"symbol","rows","first_date","last_date","parquet_path"}`)
   or `null`; `snapshot` is the **verbatim** 0007 manifest (keys
   `{"symbol","path","bytes","last_date","windows","k"}`) or `null`; `error` is
   `null` or a str starting exactly `"refresh: "` or `"snapshot: "` followed by
   `str(exc)`. Invariant: `ok == (error is None)`.
   Stage semantics: a refresh-stage exception means `snapshot is None` and the stage
   is never attempted; each stage is wrapped in `except Exception`
   (`KeyboardInterrupt`/`SystemExit` propagate); **no stage failure ever escapes
   `run_eod_job`**; an existing snapshot file is never deleted or partially
   overwritten by a failing run (the file on disk is only (re)written by a
   *successful* `build_snapshot` call).
4. **CLI contract (Gate 1 §2.1):** module `src/eod_job.py` runnable as
   `python -m src.eod_job` with flags exactly `--symbol` (default `^NSEI`),
   `--start-date` (default `2007-09-17`), `--end-date` (default none = today),
   `--parquet-dir` (default `data/parquet`), `--snapshot-dir` (default
   `data/static/api/v1`); stdout is **exactly one line** — `json.dumps(report)` —
   parsed by `json.loads(stdout.strip())`; exit code **0 iff `ok` else 1**;
   `--help` exits 0. The module docstring contains Gate 1 §2.3's crontab line
   `30 17 * * 1-5`.
5. **Pins (PROBE_EXIT=0, 2026-10-07 — composed the real `refresh_store` +
   `build_snapshot` seams before any Gate 3 code existed):**
   - Snapshot bytes: sha256 `fa4c598cf59c2f65ad7284b451c786280735a909d8e84a604dd789634b781897`,
     **63,791 bytes**, `last_date "2026-10-05"` (0007's pin, reproduced through the
     0002 refresh path — the CSV→Parquet round-trip is lossless, probe-confirmed).
   - No-op run: **zero `get` calls** (a raising stub never fired), refresh manifest
     `rows == 4673`, `first_date == "2007-09-17"`.
   - Delta run: `get` call dates exactly `["02102026", "03102026", "04102026",
     "05102026"]` (02 = Gandhi Jayanti holiday → None, 03/04 weekend → None,
     05 → fixture payload), then `rows == 4673` and the same snapshot pin.
   - Delta store vs fixture store: **exactly one differing cell** — `volume` on
     `2026-10-05` becomes `412554239` (NSE payload) instead of the fixture's yfinance
     `436700` (0002 §5's documented semantic drift); `date,open,high,low,close` are
     identical everywhere and all other volumes identical (probe-verified with
     `assert_frame_equal`). The snapshot pin still holds because volume never enters
     the document.
   - Snapshot-stage failure on a 1-row store: `ValueError` message exactly
     `bars: store has 1 rows; window 5 needs >= 20` (0003's `bars` gate fires before
     0005's `regime` gate — probe-discovered; Gate 1 §2.2 cited `< 252 rows` as the
     condition, this pins which gate reports it for the 1-row case).
   - Unknown symbol: `ValueError` message exactly
     `unknown symbol: '__NOPE__' (known: ['^NSEI'])` (0002's).
   - Transport: `get` raising `OSError("boom")` propagates out of `refresh_store`
     (so the job's `refresh:` stage must catch it); with a truncated master it is
     called **exactly once** (first missing day `02102026`) before failing, and the
     failure leaves the store file's bytes and the prior snapshot pin untouched
     (fetch precedes any store rewrite — probe-verified).
   - Perf: whole no-op run best-of-3 **0.64 s** on the dev machine.
6. **Tolerances & conventions:** byte-sha and call-count/date lists exact;
   manifests/report compared as exact `==`; timing bound **≤ 3.0 s** best-of-3 after
   a warm-up (probe 0.64 s — non-SLA, 0001 posture); runner
   `python -m pytest tests/test_0009.py` from repo root; "store read-back" =
   `pandas.read_parquet`; CLI tests are **hermetic by construction** (args chosen so
   zero network calls are possible: `end_date` ≤ master's last date, or failure
   raised before the first `get` — a subprocess cannot take a stub).

**Eval conventions:**
- Autouse guards: both fixture shas **and** the §0 freeze-1 seven-eval table.
- Master seeding = the 0001 fixture CSV copied (or row-trimmed) into
  `{tmp}/eod/^NSEI.csv`, mirroring 0002's derived ledger path
  (`parquet_dir.parent/eod`).
- "Snapshot file unchanged" = sha256 comparison of the file bytes before/after.

---

## 1. Success Paths

**T-001 — No-op freshness run: full report contract, zero network, pinned bytes**
- *Given* a tmp tree whose `{tmp}/eod/^NSEI.csv` is the 0001 fixture, and a `get`
  recorder (records URLs; would fail the test if any call arrives),
- *When* `run_eod_job("^NSEI", "2007-09-17", "2026-10-05", tmp/"parquet", tmp/"api",
  get=recorder)` runs,
- *Then* the report's keys are exactly, in order,
  `["symbol","end_date","ok","refresh","snapshot","error"]`; `ok is True`,
  `error is None`, `end_date == "2026-10-05"`; `refresh` keys exactly
  `{"symbol","rows","first_date","last_date","parquet_path"}` with
  `rows == 4673`, `first_date == "2007-09-17"`, `last_date == "2026-10-05"`,
  `symbol == "^NSEI"`; `snapshot` keys exactly
  `{"symbol","path","bytes","last_date","windows","k"}` with `bytes == 63791`,
  `last_date == "2026-10-05"`, `windows == [5,10,15,30,60]`, `k == 10`; the file at
  `snapshot["path"]` hashes to the §0 freeze-5 sha; and **`recorder` recorded zero
  calls**.

**T-002 — Byte determinism across identical runs**
- *Given* T-001's tree,
- *When* the same call runs a second time,
- *Then* the report `==` the first report exactly and the snapshot file is
  byte-identical (same sha, 63,791 bytes).

**T-003 — Delta run: fetch → store → snapshot end to end**
- *Given* `{tmp}/eod/^NSEI.csv` is the 0001 fixture **minus its final row**
  (last date 2026-10-01), and a stub `get` that records each URL's `ddmmyyyy` and
  returns the committed `ind_close_all_20261005.csv` bytes for `05102026` and
  `None` otherwise,
- *When* `run_eod_job("^NSEI", "2007-09-17", "2026-10-05", ...)` runs,
- *Then* `ok is True`; recorded call dates are exactly
  `["02102026","03102026","04102026","05102026"]`; `refresh["rows"] == 4673` and
  `refresh["last_date"] == "2026-10-05"`; the Parquet read-back equals the 0001
  fixture's content on `date,open,high,low,close` exactly and on `volume` for every
  row **except** `2026-10-05`, whose volume is exactly `412554239` (NSE payload over
  the fixture's yfinance `436700` — §0 freeze 5, 0002 §5's documented drift); and
  the snapshot file hashes to the §0 freeze-5 sha.

---

## 2. Failure Paths (stage-honest reporting)

**T-004 — Refresh-stage failure preserves the last good snapshot and store**
- *Given* a tree that first completed a successful no-op run (snapshot on disk =
  §0 pin), then had its master replaced by the fixture-minus-final-row version,
- *When* `run_eod_job` runs with `get` raising `OSError("boom")`,
- *Then* the report has `ok is False`, `refresh is None`, `snapshot is None`, and
  `error` starting exactly `"refresh: "` with `"boom"` in it; the snapshot file's
  sha is **unchanged** (still the §0 pin); the Parquet file's bytes are unchanged
  (the fetch raised before any store rewrite); and the stub was called exactly
  **once** (first missing day, before failing).

**T-005 — Snapshot-stage failure is reported, prior snapshot preserved**
- *Given* a tree that first completed a successful no-op run (snapshot = §0 pin),
  then had its master replaced by a **single-row** ledger built from the committed
  payload's Nifty 50 row for 2026-10-05,
- *When* `run_eod_job("^NSEI", "2007-09-17", "2026-10-05", ...)` runs,
- *Then* `ok is False`; `refresh` is the verbatim 0001 manifest with
  `rows == 1`, `first_date == last_date == "2026-10-05"` (the refresh stage
  *succeeded*); `snapshot is None`; `error ==`
  `"snapshot: bars: store has 1 rows; window 5 needs >= 20"` (exact, §0 freeze 5);
  the rewritten 1-row Parquet exists on disk; and the pre-existing snapshot file's
  sha is unchanged.

**T-006 — Unknown symbol fails before any network**
- *Given* a tmp tree and a recording `get`,
- *When* `run_eod_job("__NOPE__", "2007-09-17", "2026-10-05", ...)` runs,
- *Then* `ok is False`, `refresh is None`, `snapshot is None`, `error` equals
  `"refresh: unknown symbol: '__NOPE__' (known: ['^NSEI'])"` (exact, §0 freeze 5),
  and the recorder logged **zero** calls.

---

## 3. CLI (`python -m src.eod_job`)

**T-007 — CLI success: exit 0, one JSON line, pinned artifact**
- *Given* a tmp tree with the fixture-seeded master, run in a subprocess from the
  repo root with `--parquet-dir {tmp}/parquet --snapshot-dir {tmp}/api
  --end-date 2026-10-05` (zero-network by construction),
- *When* the process completes,
- *Then* the return code is **0**, `stdout.strip()` is a single line that
  `json.loads` to a report with `ok is True` and the §0 freeze-3 key order, and the
  written snapshot hashes to the §0 freeze-5 sha.

**T-008 — CLI failure exit, --help, and the documented crontab line**
- *Given* the same repo root,
- *When* (a) the CLI runs with `--symbol __NOPE__` (plus tmp dirs and
  `--end-date 2026-10-05`), (b) the CLI runs with `--help`, and (c) `src/eod_job.py`
  is read,
- *Then* (a) the return code is **1** and stdout is one JSON line with
  `ok is False` and `error` starting `"refresh: "`; (b) the return code is **0**;
  (c) the module docstring contains the crontab line `30 17 * * 1-5`.

---

## 4. Hygiene & Performance

**T-009 — Hermetic and read-only over 0001/0007 outputs**
- *Given* `socket.socket` monkeypatched to raise, a fixture-seeded master, and the
  fixture content captured pre-run,
- *When* the no-op run executes in-process,
- *Then* it completes with `ok is True` (no socket was needed), the Parquet
  read-back still equals the fixture content exactly (0001: content, not bytes, is
  the contract), and the snapshot file equals the §0 freeze-5 sha.

**T-010 — Performance sanity**
- *Given* a fixture-seeded tree warmed by one run,
- *When* the no-op run is timed best-of-3,
- *Then* it completes within **3.0 s** (probe measured 0.64 s; non-SLA, 0001
  posture).

---

## 5. Coverage Map (requirement §2 → scenarios)

| Requirement rule | Scenarios |
|---|---|
| `run_eod_job` seam composing the two frozen seams (§2.1) | T-001, T-003 |
| Explicit params, injectable `get`, `end_date=None`→today (§2.1) | §0 freeze 2 (signature), T-001 (explicit) |
| CLI flags/defaults, one JSON line, exit 0/1 (§2.1) | T-007, T-008 |
| Report 6-key shape, verbatim manifests (§2.2) | T-001, T-005, T-006 |
| Failure policy: stage-honest, never deletes good snapshot (§2.2) | T-004, T-005 |
| Documented crontab line, no cron file (§2.3) | T-008(c) |
| Acceptance: no-op / delta / transport / snapshot-stage / unknown symbol / CLI codes (§2.4) | T-001…T-008 |
| Pin provenance: `/data/` ignored, 0007 pin lives in tmp evals (§2.4) | T-007, T-009 (all runs in `tmp_path`) |
| No new dependency (§2.5) | — (nothing to approve) |
| Zero edits to 0001–0007 (§3 negative scope) | §0 freeze 1 (autouse sha guard) |
| Hermetic + no-op ≲3 s sanity (§2.4) | T-009, T-010 |

---

## 6. Gate 2 Sign-Off

- [x] **User approves** this test spec **including the six §0 interface freezes**
      → it is **IMMUTABLE**; Gate 3 (TDD: Red → Green in `tests/test_0009.py`,
      creating `src/eod_job.py` only) may begin. **(Approved 2026-10-07)**

**STOP:** No `src/eod_job.py` may be written until the box above is checked by the
user.

**Revision log:** *(none — authored after every pin was probe-verified across
three probe rounds (final PROBE_EXIT=0, 2026-10-07, composing the real 0002+0007
seams with no Gate 3 code present). Round 2 caught an unproven draft claim in
T-003 ("read-back equals fixture exactly") and replaced it with the
probe-verified volume-drift contract in §0 freeze 5 — the correction happened
before freeze, not after. Also: Gate 1 §6 row 3's "5-key" label was corrected to
"6-key" during authoring — the key set in Gate 1 §2.2 always had six keys; no
contract changed. Any future change to this file must be a user-directed revision
recorded here, like 0003 R1/R2, 0005 R1.)*
