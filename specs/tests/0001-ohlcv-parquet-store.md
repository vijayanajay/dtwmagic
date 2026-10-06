# Gate 2 — Frozen Test Spec `0001-ohlcv-parquet-store`

**Status:** `FROZEN — approved by user 2026-10-06. This file is IMMUTABLE; it may
never be edited to make failing code pass. Only a user-directed revision may change it.`
**Date:** 2026-10-06
**Maps 1-to-1 to:** `specs/requirements/0001-ohlcv-parquet-store.md` (Gate 1, APPROVED)
**Test file (Gate 3):** `tests/test_0001.py` (pytest)
**Import seam (frozen):** `from src.ohlcv_store import build_store`
(Gate 3 creates empty `src/__init__.py` + `src/ohlcv_store.py`; no other modules exist
until later specs.)

---

## 0. Eval Conventions

- Runner: `python -m pytest tests/test_0001.py` from repo root (offline).
- Happy-path input: committed fixture `tests/fixtures/nifty50_daily_ohlcv.csv`
  (sha256 `25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e`).
  Any drift in that hash invalidates this eval.
- Malformed inputs: built **in-test** under pytest `tmp_path` from inline rows —
  no other committed fixtures.
- "Read-back" means `pandas.read_parquet(path)` after `build_store` returns.
- Every rejection scenario asserts **both** `pytest.raises(ValueError)` **and** a
  non-empty message containing the frozen keyword substring listed for that scenario
  (the "naming the failed rule" contract from the requirement spec).
- Frozen fixture facts: 4,673 data rows (4,674 lines incl. header), range
  2007-09-17 → 2026-10-05, 1,333 `volume == 0` rows, Saturday row at line 4263.

---

## 1. Happy Path (fixture → store)

**T-001 — Manifest contract**
- *Given* the committed fixture, `symbol="^NSEI"`, and a fresh `out_dir`,
- *When* `build_store` is called,
- *Then* the return value is a `dict` whose keys are **exactly**
  `{"symbol","rows","first_date","last_date","parquet_path"}` (no extras),
  with `symbol == "^NSEI"`, `rows == 4673` (int),
  `first_date == "2007-09-17"`, `last_date == "2026-10-05"`, and
  `parquet_path == str(out_dir / "^NSEI.parquet")`.

**T-002 — Output location & creation**
- *Given* an `out_dir` that does not exist yet,
- *When* `build_store` is called,
- *Then* the directory is created and the single output file
  `{out_dir}/{symbol}.parquet` exists; `symbol` is used verbatim (the `^` is kept).

**T-003 — Schema & types on read-back**
- *Given* a successful store build,
- *When* the Parquet is read back,
- *Then* columns are exactly `date, open, high, low, close, volume`; `date` is a
  date/timestamp dtype; `open,high,low,close` are `float64`; `volume` is `int64`;
  row count is 4673; dates are strictly ascending; there are **no nulls**.

**T-004 — Content equality (numerical pinning)**
- *Given* a successful store build,
- *When* read-back content is compared to the fixture,
- *Then* every cell equals the fixture value, including these pinned rows:
  - first row: `2007-09-17, 4518.45, 4549.05, 4482.85, 4494.65, 0`
  - Saturday row: `2025-02-01, 23528.6, 23632.45, 23318.3, 23482.15, 281000`
  - last row: `2026-10-05, 22532.4, 22621.8, 22397.1, 22555.75, 436700`

**T-005 — 2-decimal preservation**
- *Given* price `4518.45` in the input,
- *When* read back from Parquet,
- *Then* the value is exactly `4518.45` (no float32 downcast, no re-rounding drift).

**T-006 — Idempotent overwrite (content-deterministic)**
- *Given* a store already built from the fixture,
- *When* `build_store` is called again with the same inputs,
- *Then* it succeeds, replaces the file, and the read-back content is equal to the
  first run's. **Byte-identity of the Parquet file is explicitly NOT asserted.**

**T-007 — Fixture quirk acceptance**
- *Given* the committed fixture,
- *When* `build_store` is called,
- *Then* it succeeds with: the Saturday session row `2025-02-01` present, and all
  1,333 `volume == 0` rows stored as `0` (never coerced to null) — proving zero
  volume is valid data and weekday-only validation is **not** applied.

**T-008 — Hermetic (no network)**
- *Given* socket access monkeypatched to raise on any use,
- *When* `build_store` is called with the fixture,
- *Then* it completes successfully (offline guarantee).

**T-009 — Performance sanity (non-SLA)**
- *Given* the committed fixture,
- *When* `build_store` runs,
- *Then* wall-clock time is `< 5.0 s` (generous bound encoding the requirement's
  "≲1 s sanity, not an SLA"; a breach fails the eval but the target is ≲1 s).

---

## 2. Rejection Cases (each: `pytest.raises(ValueError)` + frozen keyword)

Malformed CSVs are inline in `tmp_path`, minimal (2–3 rows) unless stated.

**T-010 — Missing required column:** drop `volume` → message contains `column`.
**T-011 — Extra column:** add `adj_close` → message contains `column`.
**T-012 — Wrong-case column header:** `Date` instead of `date` → message contains `column`.
**T-013 — Duplicate dates:** same date twice → message contains `duplicate`.
**T-014 — Null value:** empty `close` cell → message contains `null`.
**T-015 — Non-positive price:** `close=0` (and variant `open=-1`) → message contains `price`.
**T-016 — High below body:** `high < max(open, close)` → message contains `high`.
**T-017 — Low above body:** `low > min(open, close)` → message contains `low`.
**T-018 — Negative volume:** `volume=-1` → message contains `volume`.
**T-019 — Fractional volume:** `volume=100.5` → message contains `volume`.
**T-020 — Empty input:** header only, zero data rows → message contains `empty`.
**T-021 — Unparseable date:** `2024-13-40` or `not-a-date` → message contains `date`.

---

## 3. Normalization (must NOT raise)

**T-022 — Unsorted input is sorted**
- *Given* valid rows in descending date order,
- *When* `build_store` is called,
- *Then* it succeeds; output rows are ascending; `first_date`/`last_date` reflect the
  sorted range (i.e. are swapped relative to input order).

**T-023 — Boundary acceptance**
- *Given* a valid minimal CSV where `high == max(open, close)`,
  `low == min(open, close)`, and `volume == 0`,
- *When* `build_store` is called,
- *Then* it succeeds (equality at the OHLC boundaries and zero volume are valid).

---

## 4. Coverage Map (requirement §2.1 → scenarios)

| Requirement rule | Scenarios |
|---|---|
| Seam + manifest keys | T-001 |
| Output path/dir creation | T-002 |
| Arrow schema (date32/float64/int64), order, no nulls | T-003, T-005 |
| Content equality / determinism | T-004, T-006 |
| Columns exact/lowercase | T-010, T-011, T-012 |
| Date parseable, unique, sorted | T-021, T-013, T-022 |
| No nulls | T-014 |
| Price > 0 / OHLC sanity | T-015, T-016, T-017, T-023 |
| Volume int ≥ 0, zero valid | T-018, T-019, T-007, T-023 |
| Empty input rejected | T-020 |
| Fixture quirks (Saturday, zero-vol) | T-007, T-023 |
| Offline / hermetic | T-008 |
| ≲1 s sanity (non-SLA) | T-009 |
| Overwrite semantics | T-006 |

---

## 5. Gate 2 Sign-Off

- [x] **User approves** this test spec → it becomes **IMMUTABLE**; Gate 3 (TDD:
      Red → Green in `tests/test_0001.py`) may begin. **(Approved 2026-10-06)**
- [x] **User approves** `pytest` as the test runner (not yet installed; stdlib
      `unittest` is the fallback per the Ponytail ladder if denied). **(Approved 2026-10-06)**

**Status after sign-off:** Gate 2 complete and frozen. Gate 3 authorized (Red → Green
in `tests/test_0001.py`).
