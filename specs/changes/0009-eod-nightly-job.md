# Gate 4 — Change & Decision Record `0009-eod-nightly-job`

**Date:** 2026-10-07
**Gates:** Gate 1 approved (2026-10-07) → Gate 2 frozen (2026-10-07, 10 scenarios +
six §0 freezes, all pins probe-verified across three probe rounds, final
PROBE_EXIT=0) → Gate 3 Red → Green complete.

---

## 1. Files Added / Modified

| File | Change |
|---|---|
| `specs/requirements/0009-eod-nightly-job.md` | Added — Gate 1 (approved) |
| `specs/tests/0009-eod-nightly-job.md` | Added — Gate 2 (FROZEN, 10 scenarios + six §0 freezes) |
| `tests/test_0009.py` | Added — the frozen eval T-001…T-010 (autouse sha guard now covers both fixtures + tests 0001–0007) |
| `src/eod_job.py` | Added — `run_eod_job(symbol, start_date, end_date, parquet_dir, snapshot_dir, get=_real_get)` + `python -m src.eod_job` CLI |
| `src/` files of specs 0001–0007 | **Untouched** — all their evals re-run green; sha-pinned by 0009's guard |

---

## 2. Architectural & Quantitative Decisions

1. **Composition only, one new source file.** `run_eod_job` calls 0002's
   `refresh_store` then 0007's `build_snapshot` — no re-implementation of fetch,
   validation, search, regime, or stats. Every value in the report is a frozen
   seam's manifest verbatim (pinned by T-001/T-005 deep key-set checks).
2. **The job resolves `end_date=None` itself** (§0 freeze 2): delegating `None`
   would make the report's `end_date` unknowable; resolving to
   `date.today().isoformat()` *before* delegating keeps the report a pure ISO str
   and the delegated call unchanged in behavior.
3. **Stage-honest failures, no exception escapes** (Gate 1 §2.2): each stage is
   `except Exception`; `error` carries the stage prefix `refresh:`/`snapshot:` +
   `str(exc)`; `ok == (error is None)`; a refresh failure never attempts the
   snapshot stage. The wrapper is the only place error-to-report conversion
   happens, so exit-code monitoring is a single `0 if ok else 1`.
4. **A failing run never touches a good artifact** (T-004/T-005): the fetch
   precedes any store rewrite (probe: exactly 1 `get` call, store bytes
   unchanged), and `build_snapshot` raises before opening the output file — the
   job adds no deletion or partial-write logic of its own; it simply doesn't
   write on failure.
5. **CLI = argparse + one JSON line + exit code** (§0 freeze 4): the most
   monitorable interface with zero infrastructure (Kailash Nadh rung 3); no
   logging framework, no cron file — the crontab line lives in the module
   docstring as documentation (Gate 1 §2.3), pinned by T-008(c).
6. **Probe-before-freeze held, and caught a real error.** Round 2 disproved the
   draft T-003 claim "delta read-back equals fixture exactly": the store differs
   in exactly one cell — `volume` on 2026-10-05 (`412554239` NSE vs `436700`
   yfinance, 0002 §5's documented drift). The frozen spec pins that cell
   explicitly (§0 freeze 5) instead of a claim the data contradicted. The
   snapshot sha pin survived because volume never enters the document.
7. **Probe-discovered gate attribution:** a 1-row store fails at 0003's `bars`
   gate (`bars: store has 1 rows; window 5 needs >= 20`), not 0005's `regime`
   gate — Gate 1 cited `< 252 rows` as the condition; Gate 2 pinned which gate
   reports it for the probed case.
8. **RED honesty:** all 10 evals failed at RED against the stub
   (`NotImplementedError` / empty CLI stdout) — the full new-behavior set; the
   sha guard passed even at RED, proving no prior eval was touched to get there.

---

## 3. Known Limits & Ceilings (in `src/eod_job.py` docstring)

- Sequential single-symbol run — Phase 2's 2,000-stock <90 s needs 0007's
  rank-only seam + multiprocessing.
- Freshness monitoring = exit code + `report.last_date`, watched externally;
  no NSE holiday calendar (0002's ceiling, unchanged) — a silent upstream stall
  is only visible to whoever reads the cron log.
- ~1 h paced cold-start backfill before the first snapshot can build (store
  needs ≥ 252 rows for 0005's rolling-252 rank) — 0002's ceiling.
- Inherited unchanged: 0002's append-only master / 404-skip; 0007's plain
  open-write (no atomic swap), five fixed windows, `^NSEI` URL-unsafe filename,
  no gzip.
- No retry loop — a transient failure is exit 1 and the next cron tick retries
  (0002's natural-retry posture).
- `python -m src.eod_job` with default flags runs **live network** against
  `data/` — never invoked during Gate 3; hermetic tests pass tmp dirs and
  zero-network args by construction.

---

## 4. Verification Output (Gate 3)

```
RED:   10 failed in 1.94s                        RED_EXIT=1  (stub src/eod_job.py)
GREEN: 10 passed in 11.92s                       GREEN_EXIT=0
Full suite (0001..0009): 118 passed in 24.65s    FULL_EXIT=0

Pins confirmed live by the eval on first GREEN:
  T-001 report keys in order [symbol,end_date,ok,refresh,snapshot,error];
        refresh manifest 5 keys, rows 4673, first 2007-09-17, last 2026-10-05;
        snapshot manifest 6 keys, bytes 63791, windows [5,10,15,30,60], k 10;
        snapshot sha256 fa4c598cf59c2f65ad7284b451c786280735a909d8e84a604dd789634b781897
        (0007's pin, reproduced through the 0002 refresh path); zero get calls
  T-002 byte-identical rerun, reports ==
  T-003 delta calls [02102026,03102026,04102026,05102026]; rows 4673;
        exactly one volume cell differs (2026-10-05 -> 412554239), OHLC+dates exact
  T-004 boom: error "refresh: ..." with 1 call, store bytes unchanged,
        prior snapshot sha unchanged
  T-005 snapshot-stage: error exactly
        "snapshot: bars: store has 1 rows; window 5 needs >= 20",
        refresh manifest present (rows 1), prior snapshot sha unchanged
  T-006 exact "refresh: unknown symbol: '__NOPE__' (known: ['^NSEI'])", 0 calls
  T-007/T-008 CLI subprocess: rc 0 / rc 1 / --help rc 0, one JSON line each,
        crontab line "30 17 * * 1-5" present in src/eod_job.py docstring
  T-009 socket-guarded run completes; store read-back == fixture content
  T-010 no-op run best-of-3 <= 3.0s (probe measured 0.64s)
  sha guard: both fixtures + tests 0001..0007 all match — zero frozen evals edited
  boundary: git status = 4 new files at Gate 3 close (5 with this record);
            no tracked file modified
```

No test file or test spec was edited to achieve green; the autouse sha guard in
`tests/test_0009.py` proves it mechanically on every subsequent run.
