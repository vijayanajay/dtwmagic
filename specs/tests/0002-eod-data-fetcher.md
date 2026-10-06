# Gate 2 — Frozen Test Spec `0002-eod-data-fetcher`

**Status:** `FROZEN — approved by user 2026-10-06 (15 scenarios + four §0 interface
freezes). This file is IMMUTABLE; it may never be edited to make failing code pass.
Only a user-directed revision may change it.`
**Date:** 2026-10-06
**Maps 1-to-1 to:** `specs/requirements/0002-eod-data-fetcher.md` (Gate 1, APPROVED)
**Test file (Gate 3):** `tests/test_0002.py` (pytest)
**Import seam (frozen):** `from src.eod_fetch import fetch_eod_index, refresh_store`
(Gate 3 creates `src/eod_fetch.py`; spec 0001's `src/ohlcv_store.py` stays untouched.)

---

## 0. Interface Freezes (clarifying details of the approved Gate 1)

These four points are implied but not fully pinned by Gate 1; freezing them here makes
the eval deterministic. **They are surfaced for explicit approval with this spec:**

1. **`get` contract:** `get(url)` returns `bytes` on HTTP 200 and **`None` on 404**
   (non-trading day ⇒ no file ⇒ skip). The default real implementation may raise on
   transport errors — the caller re-runs (natural retry, per Gate 1 §3).
2. **`refresh_store` signature** gains an optional trailing `end_date`:
   `refresh_store(symbol, start_date, out_dir, get=<real>, end_date=None)` where
   `None` means *today* (Gate 1 §2.6 scenarios reference `end_date`; tests always pass
   it explicitly so no eval depends on the wall clock).
3. **Master ledger path:** `{out_dir.parent}/eod/{symbol}.csv` — with the production
   `out_dir = data/parquet` this is exactly Gate 1's `data/eod/{symbol}.csv`; in tests
   it lands under `tmp_path`, keeping the repo clean.
4. **Date parameters** are ISO `YYYY-MM-DD` strings on both seams; the master CSV uses
   the same six-column header as the 0001 fixture (`date,open,high,low,close,volume`)
   so `build_store` reads it directly.

**Eval conventions:**
- Runner: `python -m pytest tests/test_0002.py` from repo root. **No network, ever** —
  every test injects a stub `get`; T-014 proves it with sockets blocked.
- Fixtures (autouse sha256 guard, drift invalidates the eval):
  - `tests/fixtures/ind_close_all_20261005.csv` — sha256
    `f0b8004e9bc79b11cff3c939cb42cdeb4a31b71ebd03942b98b57f44fa3bc9ba` (168 lines,
    all indices; `Nifty 50` OHLCV values from its row: date `05-10-2026`,
    open `22532.4`, high `22621.8`, low `22397.1`, close `22555.75`, volume
    `412554239` — the row also carries Points Change / Change(%) / turnover /
    P-E columns, which the mapper drops).
  - `tests/fixtures/nifty50_daily_ohlcv.csv` (0001) — sha256
    `25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e`.
- Small multi-day payloads are built inline in tests (header + chosen `Nifty 50` rows).
- Rejection scenarios assert `pytest.raises(ValueError)` **and** the frozen keyword
  substring in the message: `symbol` / `row` / `html` / (delegated) `price`.

---

## 1. `fetch_eod_index` (mapping, iteration, errors)

**T-001 — Canonical mapping from the real payload**
- *Given* `get` returning the committed 05-10-2026 payload for any URL,
- *When* `fetch_eod_index("Nifty 50", "2026-10-05", "2026-10-05", get=stub)`,
- *Then* the frame has columns exactly `date,open,high,low,close,volume`; **one** row
  (the 166-row file is filtered by index name); `date == "2026-10-05"` (DD-MM-YYYY →
  ISO); `open=22532.4, high=22621.8, low=22397.1, close=22555.75`;
  `volume == 412554239` as `int64`; OHLC `float64`; ascending order.

**T-002 — Exact archive URL construction**
- *Given* a recording stub `get`,
- *When* fetching the date `2026-10-05`,
- *Then* it receives exactly
  `https://nsearchives.nseindia.com/content/indices/ind_close_all_05102026.csv`
  (DDMMYYYY), once.

**T-003 — Multi-day iteration with non-trading gaps**
- *Given* a stub serving distinct inline payloads for `01102026`/`02102026`, the real
  payload for `05102026`, and `None` for Sat/Sun (`03102026`, `04102026`),
- *When* fetching `2026-10-01` → `2026-10-05`,
- *Then* 5 requests are made (one per calendar day — no trading calendar), `None`
  days are skipped without error, and the frame holds 3 rows ascending by date with
  values from each day's body (not from the URL).

**T-004 — Empty range edge**
- *When* fetching with `start_date > end_date` (e.g. `2026-10-06` → `2026-10-05`),
- *Then* it returns a **0-row** frame with the exact six columns — no crash, no
  requests.

**T-005 — 200 response without the requested index**
- *Given* a 200 body containing other indices but no `Nifty 50` row,
- *When* `fetch_eod_index("Nifty 50", ...)`,
- *Then* `ValueError` whose message contains `row`.

**T-006 — HTML error/bot page served with 200**
- *Given* a 200 body starting with `<html`,
- *When* fetching,
- *Then* `ValueError` whose message contains `html`.

---

## 2. `refresh_store` (ledger, delta fetch, full rewrite, composition)

**T-007 — Cold start end-to-end**
- *Given* no master and no store, `out_dir = tmp/store`, and the real payload stub,
- *When* `refresh_store("^NSEI", "2026-10-05", tmp/store, get=stub, end_date="2026-10-05")`,
- *Then* manifest keys are **exactly** `{"symbol","rows","first_date","last_date",
  "parquet_path"}` with `symbol=="^NSEI"`, `rows==1`,
  `first_date==last_date=="2026-10-05"`,
  `parquet_path==str(tmp/"store"/"^NSEI.parquet")`; the Parquet exists; **and** the
  master ledger exists at the frozen path `tmp/eod/^NSEI.csv` containing the mapped row.

**T-008 — Parquet content matches the source body (composition with 0001)**
- *Given* T-007's store,
- *When* the Parquet is read back,
- *Then* `date` is Arrow date32/timestamp; OHLC `float64`, `volume` `int64`; the single
  row equals `2026-10-05 | 22532.4 | 22621.8 | 22397.1 | 22555.75 | 412554239`.

**T-009 — Unknown symbol rejected before any request**
- *Given* a recording stub,
- *When* `refresh_store("XXNOPE", ...)`,
- *Then* `ValueError` whose message contains `symbol`, and **`get` was never called**.

**T-010 — Nightly delta: exactly the missing days, store otherwise untouched**
- *Given* a master + store ending `2026-10-05` (built from the real payload),
- *When* a run with `end_date="2026-10-07"` and a stub returning `None` for
  2026-10-06/07,
- *Then* `get` is called **exactly 2 times** (dates after the master only — history is
  never re-fetched), the manifest still reports `first_date=="2007-09-17"`-style
  continuity (here: `first_date=="2026-10-05"`, `rows==1`), and read-back store content
  is equal to before the run.

**T-011 — Catch-up after an outage, append-only and duplicate-free**
- *Given* a master ending `2026-09-30` (single prior row from an inline payload),
- *When* a run with `end_date="2026-10-05"`, stub serving payloads for 01/02/05-10 and
  `None` for the weekend,
- *Then* 5 requests fire (Oct 1–5), the master holds **4 rows** (1 seed + 3 fetched
  payloads; Oct 3–4 = weekend `None`), dates strictly ascending and unique, the
  pre-existing 2026-09-30 row is unchanged (append-only), and the rewritten Parquet
  has 4 rows.

**T-012 — Idempotent rerun issues zero requests**
- *Given* T-011's completed state,
- *When* the identical run repeats with a recording stub,
- *Then* `get` is called **0 times**, master row count is unchanged, and read-back
  Parquet content equals the previous run's.

**T-013 — Validation is delegated to 0001, not duplicated**
- *Given* a master pre-seeded with a row whose `close=0`,
- *When* `refresh_store` runs (stub may return `None`),
- *Then* `ValueError` whose message contains `price` — raised by 0001's
  `build_store`, proving composition over re-implementation.

**T-014 — Hermetic (no network)**
- *Given* socket access monkeypatched to raise,
- *When* a full cold-start `refresh_store` with the payload stub runs,
- *Then* it completes successfully.

**T-015 — Performance sanity (non-SLA)**
- *Given* an existing master,
- *When* the nightly-path sequence (2 stub requests + full rewrite) runs,
- *Then* wall-clock `< 5.0 s` (encodes Gate 1's "≲2 requests + rewrite ≲5 s" sanity).

---

## 3. Coverage Map (requirement §2 → scenarios)

| Requirement rule | Scenarios |
|---|---|
| Source URL + pacing boundary (`get` seam) | T-002, T-003, T-010, T-012 |
| DD-MM-YYYY → ISO, column mapping, drop metrics | T-001 |
| Index-name filter, symbol map `{"^NSEI": "Nifty 50"}` | T-001, T-009 |
| Missing row / HTML body errors | T-005, T-006 |
| Master ledger + delta fetch + 404 skip (§2.3) | T-010, T-011, T-012 |
| Full rewrite via `build_store`, 5-key manifest | T-007, T-008, T-010 |
| Validation delegated to 0001 | T-013 |
| Hermetic evals (no network) | T-014 (all tests inject `get`) |
| ≲2 requests + ≲5 s nightly sanity | T-010, T-015 |
| Frozen fixtures (both sha256 guards) | autouse guard on every test |

---

## 4. Gate 2 Sign-Off

- [x] **User approves** this test spec **including the four §0 interface freezes** →
      it becomes **IMMUTABLE**; Gate 3 (Red → Green in `tests/test_0002.py`) begins.
      **(Approved 2026-10-06)**

**STOP:** No code in `src/eod_fetch.py` may be written until the box above is checked.

**Revision log:**
- **R1 (2026-10-06, user-directed, applied before any Gate 3 code existed):** T-011
  row-count arithmetic corrected `5 rows` → `4 rows` (1 seed + 3 payloads; weekend =
  `None`). Scenario structure and all other assertions unchanged.
