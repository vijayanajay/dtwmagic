# Gate 1 — Requirement Spec `0001-ohlcv-parquet-store`

**Status:** `APPROVED — Gate 1 signed off 2026-10-06 (user); Gate 2 test spec in authoring`
**Date:** 2026-10-06
**Preceded by:** Grilling session resolving spec-0001 shape (see §7 Frozen Decisions)

---

## 0. Gate 1 User-Value Flag (Explicit Waiver)

> **FLAGGED:** This is an **infrastructure prerequisite spec with no direct trader-facing
> value.** Under the Gate 1 rule ("if no end-user value, flag and discard"), it would
> normally be discarded. It is retained under an **explicit one-time waiver granted by
> the user during the pre-Gate-1 grilling session**, recorded here so the waiver is
> visible in the spec rather than silently ignored.
>
> **Justification for the waiver:** No priced feature (F-01 … F-07) can exist without a
> validated historical store. Every subsequent spec (0002 fetcher, 0003 search slice)
> consumes the seam defined here; defining it first prevents rework of frozen golden
> evals.

---

## 1. User Value Rationale (Indirect — Waived)

- **Direct value:** None. No screen, metric, or search result is produced.
- **Indirect value:** It is the mandatory foundation for the Free-tier NIFTY 50 search
  (BRD §2.2) and the whole Phase 1 pipeline (BRD §7.2). A paying trader benefits only
  through specs 0002+.

---

## 2. What Is Needed (Scope)

### 2.1 Deliverable

A **transform-only** data layer that converts a committed sample OHLCV CSV into a
validated, split-adjusted Parquet store:

1. **Public seam — one pure function** (frozen for golden evals):

   ```
   build_store(csv_path, symbol, out_dir) -> manifest: dict
   ```

   - `csv_path`: path to an OHLCV CSV in the fixture schema (§4).
   - `symbol`: identifier used for the output file name (e.g. `^NSEI`).
   - `out_dir`: directory for the store; the function creates it if missing.
   - Returns exactly these manifest keys (names frozen):

     ```
     {"symbol", "rows", "first_date", "last_date", "parquet_path"}
     ```

     - `rows`: int, data row count (header excluded)
     - `first_date` / `last_date`: ISO `YYYY-MM-DD` strings
     - `parquet_path`: string path of the written file

2. **Validation contract** — every violation raises `ValueError` naming the failed rule:
   - Required columns exactly `date,open,high,low,close,volume` (lowercase).
   - `date` parseable as ISO `YYYY-MM-DD`, **unique** (duplicates → error),
     sorted ascending by the transform (silent normalization, not an error).
   - No nulls anywhere.
   - Prices: `> 0`; `high >= max(open, close)`; `low <= min(open, close)`.
   - `volume`: integer `>= 0`. **`volume == 0` is VALID data** (see §4 quirk b) and must
     never be treated as null.
   - Empty input (0 data rows) → `ValueError`.

3. **Output contract:**
   - Single file `"{out_dir}/{symbol}.parquet"` (e.g. `data/parquet/^NSEI.parquet`).
   - Arrow schema: `date` → `date32`; `open,high,low,close` → `float64`
     (2-dp values preserved as-is); `volume` → `int64`.
   - Row order: ascending by `date`.
   - Re-running with the same input **overwrites** and yields identical *content*
     (read-back equality). Byte-identity of the file is explicitly NOT required.
   - Generated `data/` output is never committed (git-ignored).

### 2.2 Fixture (committed, hermetic — created alongside this spec)

`tests/fixtures/nifty50_daily_ohlcv.csv`

| Property | Value |
|---|---|
| Source | yfinance `^NSEI`, `auto_adjust=True`, one-time fetch 2026-10-06 |
| Rows | 4,673 |
| Range | 2007-09-17 → 2026-10-05 (fetch-day still-forming session excluded) |
| Columns | `date,open,high,low,close,volume` |
| Prices | rounded to 2 dp, float; `volume` int64 |
| Size | 230,969 bytes |
| sha256 | `25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e` |

Fixture quirks (frozen facts, NOT defects):
- **(a)** `2025-02-01` is a **Saturday** — the real NSE Union Budget special session.
  Validation must NOT assert weekday-only dates.
- **(b)** 1,333 rows (2007-09-17 → 2024-07-03, sparse) have `volume == 0` — index
  aggregate volume was unreported. Zero volume is valid, non-null data.
- **(c)** An index has no splits/dividends, so the split-adjustment contract (§6) is
  trivially satisfied for this fixture; real adjustment logic only becomes necessary
  when equities arrive with the fetcher (spec 0002).

**Fixture rule:** tests read only this committed file — **no network access in any
golden eval**. The fixture is frozen data; regenerating or editing it invalidates
downstream test specs and requires a new spec revision.

### 2.3 Dependencies

| Package | Status | Verdict |
|---|---|---|
| `pandas` | installed (3.0.6 in `.venv`) | use |
| `numpy` | installed (2.4.6) | use |
| **`pyarrow`** | **NOT installed** | **REQUIRED — flagged for approval** |

`pyarrow` passes the dependency rule check: the stdlib cannot write Parquet and
`pandas.to_parquet` has no non-pyarrow engine, so no existing dependency or stdlib
module solves this. It is the single new dependency for spec 0001.

---

## 3. What Is NOT Needed (Negative Scope)

- **No data fetching:** no yfinance, no NSE bhavcopy, no network I/O of any kind
  (→ spec 0002).
- **No search logic:** no z-normalization, Euclidean distance, DTW, Top-K, regime
  classification, MAE/MFE, or forward returns (→ spec 0003+).
- **No SQLite / analogs.db**, no static JSON API snapshots, no HTTP endpoint, no CLI
  wrapper, no dashboard/UI.
- **No adjustment computation at transform time** — the store's contract is
  "split-adjusted in"; the fixture arrives pre-adjusted (see §6 ceiling).
- **No multi-symbol orchestration**, universe registry, or symbol sanitization beyond
  using `symbol` verbatim in the file name.
- **No incremental/append updates, no partitioning scheme** — one file per full rewrite.
- **No auth, billing, alerts, screener, exports, or dashboards** (Phases 2–3).

---

## 4. Acceptance Summary (for Gate 2 authoring; test spec freezes the details)

- Given the committed fixture, `build_store` returns the manifest with
  `rows == 4673`, `first_date == "2007-09-17"`, `last_date == "2026-10-05"`.
- Read-back of the Parquet equals the fixture content (types per §2.1.3).
- Each validation rule in §2.1.2 has a corresponding rejection case raising `ValueError`.
- The transform runs offline (no network) and completes the fixture in ≲ 1 second
  on the dev machine (sanity, not an SLA).

---

## 5. Architecture Alignment (Kailash Nadh)

- Boring stack only: pandas + pyarrow, one pure function, one flat file per symbol.
- Parquet chosen per BRD §4.1 ("Apache Parquet for raw OHLCV time-series").
- No cloud services, no queues, no framework.

---

## 6. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is fixture-pre-adjusted; upgrade path is fetcher-applied
  split/bonus adjustment when equities land in spec 0002.`
- `# ponytail: ceiling is full-file rewrite per symbol; upgrade path is
  incremental append when 2,000-symbol batch (BRD §7.1, ≤90s) becomes real.`
- `# ponytail: ceiling is content-deterministic Parquet; byte-identical output is
  not guaranteed across pyarrow versions.`

---

## 7. Frozen Decisions (from pre-Gate-1 grilling session)

| # | Decision | Choice |
|---|---|---|
| 1 | Spec 0001 shape | **Data layer first** (transform only) |
| 2 | User-value gate | **Flag as infra spec + explicit one-time waiver** |
| 3 | Fetching | **Out of scope** — live fetcher is spec 0002 |
| 4 | Public seam | **Python function → dict manifest** |
| 5 | Test data | **Fixture CSV only, hermetic golden evals** |
| 6 | Adjustment policy | **Split-adjusted store contract** (fixture pre-adjusted) |
| 7 | Search mechanics (deferred) | Euclidean only, no regime, in spec 0003; DTW + regime later |

---

## 8. Gate 1 Sign-Off

- [x] **User approves** this requirement spec → agent may author Gate 2 test spec
      `specs/tests/0001-ohlcv-parquet-store.md`. **(Approved 2026-10-06)**
- [x] **User approves** `pyarrow` as the one new dependency (§2.3). **(Approved 2026-10-06)**

**Status after sign-off:** Gate 1 complete. Gate 2 test spec may be authored; it is
**IMMUTABLE once the user approves it**, and Gate 3 (code) still requires that
separate approval.
