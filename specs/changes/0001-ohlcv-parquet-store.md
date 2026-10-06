# Gate 4 — Change & Decision Record `0001-ohlcv-parquet-store`

**Date:** 2026-10-06
**Gates:** Gate 1 approved (2026-10-06) → Gate 2 frozen (2026-10-06) → Gate 3
Red → Green complete (2026-10-06).

---

## 1. Files Added / Modified

| File | Change |
|---|---|
| `specs/requirements/0001-ohlcv-parquet-store.md` | Added — Gate 1 requirement spec (approved) |
| `specs/tests/0001-ohlcv-parquet-store.md` | Added — Gate 2 test spec (FROZEN, 23 scenarios) |
| `tests/test_0001.py` | Added — the frozen eval, T-001…T-023, verbatim from Gate 2 |
| `src/__init__.py` | Added — empty package marker for the frozen import seam |
| `src/ohlcv_store.py` | Added — `build_store(csv_path, symbol, out_dir)` implementation |
| `tests/fixtures/nifty50_daily_ohlcv.csv` | Added — frozen ^NSEI fixture (4,673 rows, sha256 pinned in both specs) |
| `.gitignore` | Modified — added `/data/` (generated store never committed) |
| `.venv` | `pyarrow 25.0.1`, `pytest 9.1.1` installed (both user-approved) |

---

## 2. Architectural & Quantitative Decisions

1. **Pure function, one file per symbol.** `build_store` validates → normalizes → writes
   `{out_dir}/{symbol}.parquet` and returns a 5-key manifest dict. No classes, no
   framework, no I/O beyond the CSV in and the Parquet out (Kailash Nadh rung 6).
2. **Validation order is load-bearing:** columns → empty → nulls → date parse →
   duplicates → volume → price → high → low. Each frozen rejection keyword
   (`column/empty/null/date/duplicate/volume/price/high/low`) must win over later
   rules for its minimal malformed CSV; e.g. `close=0` must report `price`, not the
   downstream `low`-vs-body rule that it also violates.
3. **`date32[day]` via Python `datetime.date` objects** — pandas→Arrow infers date32
   with zero schema plumbing; read-back yields date objects (eval accepts
   date *or* timestamp per frozen T-003, requirement mandates date32 — verified exact).
4. **Silent sort, loud duplicates.** Unsorted input is normalized (one stable sort);
   duplicate dates are rejected — merging them would invent policy about which session
   is real.
5. **`volume == 0` is data, not null** (fixture quirk b) and **weekday-only validation
   is banned** (fixture quirk a: real 2025-02-01 Saturday Budget session).
6. **Content-deterministic, not byte-deterministic** — overwrite reruns must read back
   equal; pyarrow byte-identity across versions is explicitly not asserted.
7. **Hermetic by construction** — tests read only the committed fixture; T-008 proves
   it by making any socket use raise.

---

## 3. Known Limits & Ceilings

- Full-file rewrite per symbol; incremental append only when the 2,000-symbol batch
  (BRD §7.1 ≤90s) becomes real.
- Fixture is pre-adjusted; real split/bonus adjustment logic lands with the fetcher
  (spec 0002).
- Single-symbol API (`symbol` used verbatim in filename); no universe registry.
- Performance bound is a 5s sanity (target ≲1s), not an SLA.

---

## 4. Verification Output (Gate 3)

```
RED:   23 failed in 1.73s          RED_EXIT=1   (stub src/ohlcv_store.py)
GREEN: 23 passed in 1.56s          GREEN_EXIT=0 (implementation)
FINAL: 23 passed in 1.28s          FINAL_EXIT=0 (rerun after .gitignore + record)

Contract checks (data/parquet/^NSEI.parquet, exit=0):
  PASS Arrow date32 (requirement exact)   date32[day]
  PASS manifest rows 4673
  PASS path data/parquet/^NSEI.parquet
  PASS git check-ignore: /data/ ignored

Gate 2 coverage check: 27/27 spec-content assertions PASS (T-001…T-023 complete,
IMMUTABLE banner, 1-to-1 map, import seam, sha256 pinned in both specs).
```

All 23 frozen scenarios pass. The test spec was not edited after freezing — only the
Status/§5 approval boxes were checked at sign-off, per protocol.
