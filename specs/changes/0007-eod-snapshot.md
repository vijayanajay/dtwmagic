# Gate 4 — Change & Decision Record `0007-eod-snapshot`

**Date:** 2026-10-06
**Gates:** Gate 1 approved (2026-10-06) → Gate 2 frozen (2026-10-06, 10 scenarios +
six §0 freezes, all pins probe-verified first) → Gate 3 Red → Green complete.

---

## 1. Files Added / Modified

| File | Change |
|---|---|
| `specs/requirements/0007-eod-snapshot.md` | Added — Gate 1 (approved) |
| `specs/tests/0007-eod-snapshot.md` | Added — Gate 2 (FROZEN, 10 scenarios + six §0 freezes) |
| `tests/test_0007.py` | Added — the frozen eval T-001…T-010 (sha guard now covers tests 0001–0006) |
| `src/snapshot.py` | Added — `build_snapshot(symbol, parquet_dir, out_dir)` + module constants `WINDOWS`/`K`/`SCHEMA` |
| `src/` files of specs 0001–0006 | **Untouched** — all their evals re-run green; sha-pinned by 0007's guard |

---

## 2. Architectural & Quantitative Decisions

1. **Composition only, one new file.** `build_snapshot` reads the store once
   (for `bars`/`last_date`), calls 0005's wrapper five times (once per window),
   and 0004's reducer once per non-empty window. Zero re-implementation of
   search, regime, or stats — every value in the file is a frozen seam's output
   verbatim (proven by T-003/T-004 deep-equality against direct calls).
2. **Regime computed once, embedded top-level** (Gate 1 #5): probe asserted
   `res["regime"]` equality across all five L values — it is query-session state,
   not window state, so the document carries it once.
3. **`summary: null` converts a crash into data** (Gate 1 #4): 0004 raises on
   `[]` and the slice store is empty at **all five** windows (probe-confirmed,
   including the previously unprobed L=5/15/30). The batch survives rare-regime
   days; T-007 pins the behavior end-to-end.
4. **Byte-determinism is the contract** (Gate 1 #6 + Gate 2 §0 freezes 3/4): no
   wall-clock fields (`last_date` is freshness), frozen `json.dump` args with
   `newline="\n"` (CRLF would break the sha on Windows), insertion-ordered
   dicts. The fixture file's **sha256 `fa4c598c…b781897`, 63,791 bytes** pins the
   entire content — serialization, values, and structure — in one assertion;
   T-006 verified implementation reproduced the probe's bytes **on the first
   GREEN run** (probe → spec → code, three independent constructions agreeing).
5. **Probe-before-freeze held:** every literal in Gate 2 (five top-1 anchors,
   file sha/size, slice facts, `p252`s) came from a `PROBE_EXIT=0` run composing
   the real seams before any Gate 3 code existed — same posture as 0003's
   T-019 rebuild and 0005's dual-path probe.
6. **Manifest frozen in Gate 2 §0 #2** because Gate 1 left "the manifest"
   unpinned — surfaced as a freeze at approval rather than invented in code.
7. **Errors pass through 0005 unchanged** (T-010): `store` for a missing
   parquet, `regime` for a <252-row store; the constants make `window`/`K`/
   `bars` unreachable by construction.

---

## 3. Known Limits & Ceilings (in `src/snapshot.py` docstring)

- Five fixed windows `(5,10,15,30,60)` — upgrade: full 5..60 grid once a
  measured Phase-2 budget exists (file size × 56).
- Plain `open`-write (no `os.replace` atomic swap) — upgrade path if a reader
  ever observes a partial file.
- Symbol in filename (`^NSEI.json` — `^` is URL-unsafe) — upgrade: URL-alias map
  when the dashboard serves it (spec 0008 concern).
- Single-process, per-symbol build — Phase-2's BRD §4.1 2,000-stock <90 s needs
  0006 §6's rank-only seam + multiprocessing.
- No gzip (Nginx/CDN's job); no scheduler/cron/HTTP — the nightly *job* wiring
  stays deferred with 0002's ceiling.
- Inherited from 0004: unweighted aggregates, linear quantiles, T+10 cap;
  horizon keys arrive as strings to JSON consumers (explicit contract, T-004).

---

## 4. Verification Output (Gate 3)

```
RED:   10 failed in 1.35s                    RED_EXIT=1  (stub src/snapshot.py)
GREEN: 10 passed in 8.20s                    GREEN_EXIT=0
Full suite (0001..0007): 108 passed          FULL_EXIT=0  (14.41s)

Pins confirmed live by the eval on first GREEN:
  fixture snapshot sha256 fa4c598cf59c2f65ad7284b451c786280735a909d8e84a604dd789634b781897
                          size 63,791 bytes; reruns byte-identical
  top-1: L=5  2011-06-21/0.6545378884539143   L=10 2012-05-14/0.73704193241622
         L=15 2016-01-12/1.1565867903174754   L=30 2011-05-24/2.2385831629584225
         L=60 2012-06-04/4.612532697912032
  slice: 416 bars, bullish-normal, all five windows analogs=[] summary=null
  regime p252 0.5476190476190477 (fixture) / 0.3492063492063492 (slice)
  store sha unchanged; out_dir auto-created; socket-guarded
  perf: snapshot best-of-3 <= 2.0s bound (measured ~0.5s)
  sha guard: tests 0001..0006 all match — zero frozen evals edited
```

No test file or test spec was edited to achieve green; the autouse sha guard in
`tests/test_0007.py` proves it mechanically on every subsequent run.
