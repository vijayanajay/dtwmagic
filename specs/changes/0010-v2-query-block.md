# Gate 4 — Change & Decision Record `0010-v2-query-block`

**Date:** 2026-10-07
**Outcome:** all 4 gates complete. **Zero test-spec revisions** (R0 — the frozen
eval passed exactly as approved; no freeze was touched after sign-off).

---

## 1. Files added / modified

| File | Change |
|---|---|
| `specs/requirements/0010-v2-query-block.md` | **new** — Gate 1 (286 lines, approved 2026-10-07) |
| `specs/tests/0010-v2-query-block.md` | **new** — Gate 2 FROZEN (196 lines, 10 scenarios, six §0 freezes, approved 2026-10-07) |
| `src/snapshot_v2.py` | **new** (99 lines) — `build_snapshot_v2(symbol, parquet_dir, out_dir)` per Gate 1 §2.1 |
| `tests/test_0010.py` | **new** (376 lines) — frozen eval T-001..T-010 + 11-entry guard table |
| `src/eod_job.py` | **modified** (+10/−2) — §2.6 dual-write in the snapshot stage; docstring updated; crontab line untouched |
| `specs/changes/0010-v2-query-block.md` | **new** — this record |

**Untouched by design:** `src/snapshot.py` (v1 byte-frozen), all prior test
files and frozen specs (sha-guarded), `data/static/index.html` (frontend switch
belongs to spec 0011).

---

## 2. Architectural & quantitative decisions (and why)

1. **Additive v1 + v2 (Gate 1 §7 #1)** — the decisive constraint discovered
   during Gate 1 authoring: `test_0008`'s autouse guard pins `test_0009.py`'s
   sha and both pin `test_0001..0007`, so an in-place v1→v2 supersede would have
   cascaded re-pin revisions across three frozen specs. Additive dual-write
   delivers the §4.4 bump with **zero test edits**; verified by the guard table
   itself (freeze 1) passing.
2. **Report contract frozen at 6 keys (§2.6)** — `snapshot` still reports the
   v1 manifest with its 0009-pinned sha; the v2 manifest is written but not
   reported (ceiling: a 7th key would need a user-directed 0009 revision).
   Manifest is assigned only after **both** builds succeed, preserving every
   frozen failure-path assertion (`snapshot is None` + exact error strings).
3. **Derived path `Path(snapshot_dir).parent / "v2"`** — no new CLI flags; the
   crontab line and CLI surface are byte-stable; prod default lands at
   `data/static/api/v2/{symbol}.json` (§4.4 convention).
4. **`query = {"L": 60, "candles": [60 × forward-row dicts]}`** — one block
   sliced `(-L)` per window instead of five overlapping copies (~3.5 KB, not
   ~14 KB); candle rows reuse `forward`'s exact dict shape so the future
   frontend reuses one row renderer; `L` is the constant `max(WINDOWS)` (60),
   matching the probe (short-store branch `min(60, n)` is unreachable on
   success since L=60's window needs ≥ 130 rows).
5. **Probe-before-freeze paid off twice:** the probe cross-validated 0009's
   frozen v1 pin (`fa4c598c…`/63,791 B) proving it sat on the same seams, and
   the first timing probe *understated* dual-build cost (it reused v1's search
   pass) — `PROBE_B` re-measured a faithful double search: **1.029 s**, est.
   full run ≈ 1.15 s against T-010's frozen 3.0 s bound.
6. **Guard table grew to 11 entries** (2 fixtures + `test_0001..0009`) —
   recording `test_0008.py`'s sha (`b90993e2…`) for the first time anywhere.

---

## 3. Known limits & ceilings (inherited from Gate 1 §6)

- v2 manifest not surfaced in the report (upgrade: 7th key under 0009 R1).
- Nightly runs the search pipeline twice (~2× snapshot cost, still ≪ budget).
- No analog-side pattern prices → twin-sparkline geometry is forward-path-only
  (upgrade: v3 block + user-approved 0003/0007 pin revision).
- Fixed 60 candles; no volume (F-07 later); derived sibling path (no flag).
- Frontend still consumes v1 — `api/v2/` has no consumer until spec 0011.

---

## 4. Verification output (Gate 3 evidence)

- **RED:** `pytest tests/test_0010.py -q` → `9 failed, 1 passed in 12.60s`,
  `EXIT=1` (behavioral failures against the `NotImplementedError` stub; T-010
  was expected-green pre-wiring — it times the still-v1-only stage, and was
  re-proven after wiring by the GREEN run).
- **GREEN (first run):** → `10 passed in 15.88s`, `EXIT=0`.
- **Full suite:** → `138 passed in 59.56s`, `EXIT=0` (128 prior + 10 new;
  all prior evals unmodified — guard table green).
- **Live production run:** `python -m src.eod_job` → `JOB_EXIT=0`,
  `ok: true`, refresh 4,675 rows `last_date 2026-10-07`; v1
  `data/static/api/v1/^NSEI.json` **sha `519d72af…` — byte-identical to its
  pre-change state** (wiring did not disturb the live v1 artifact); v2
  `data/static/api/v2/^NSEI.json` created, 69,536 B, sha `2bceeb03…`.
- **Live payload sanity:** top keys exactly the freeze-2 order, schema
  `dtwmagic.api.v2`, `L=60`, 60 candles, last candle `2026-10-07` ==
  `last_date`, candle key order `date/open/high/low/close` → `V2_LIVE_OK`,
  `CHECK_EXIT=0`.
- **Isolation:** T-009 asserts `index.html` still references `./api/v1/` with
  no `api/v2` — frontend untouched (spec 0011's seam).
