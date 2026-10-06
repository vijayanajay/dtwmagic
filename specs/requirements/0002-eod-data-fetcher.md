# Gate 1 — Requirement Spec `0002-eod-data-fetcher`

**Status:** `APPROVED — Gate 1 signed off 2026-10-06 (user, incl. §2.3 reconciliation); Gate 2 test spec in authoring`
**Date:** 2026-10-06
**Consumes:** spec `0001-ohlcv-parquet-store` (Gate 3 complete, all 23 evals passing)

---

## 1. User Value Rationale (DIRECT — no waiver needed)

- **Why a paying trader cares:** the Free tier promises *"Updates: Daily End-of-Day"*
  (BRD §2.2). Without a live fetcher the store is frozen at the fixture date and every
  search runs against stale data — the product's core daily loop ("has today's pattern
  occurred before?") dies. Fresh EOD data is the difference between a research tool and
  a museum piece.
- **Monetization link:** EOD freshness underpins every tier (Free daily NIFTY 50 →
  Pro/E screener runs); BRD §4.2 makes the nightly EOD batch the system's heartbeat.

---

## 2. What Is Needed (Scope)

### 2.1 Source (frozen by user decision — evidence-based)

| Probe (2026-10-06, this machine) | Result |
|---|---|
| `nsearchives.nseindia.com/content/indices/ind_close_all_05102026.csv` | **200 OK**, 17,473 bytes — works with cookie warmup + browser UA + referer |
| Legacy path `content/ind/...` and `archives.nseindia.com` variants | 404 (dead) |
| Row `Nifty 50` OHLC vs 0001 fixture (05-10-2026) | **exact match**: 22532.4 / 22621.8 / 22397.1 / 22555.75 |

- **Official NSE index EOD file, `ind_close_all_{DDMMYYYY}.csv`, is the sole source**
  for spec 0002. One file contains **all indices** (166 Nifty rows in the sample), so a
  single request serves any index later.
- Access requirements (part of the contract): HTTP session warmed up on
  `nsearchives.nseindia.com`, browser User-Agent, `Referer: https://www.nseindia.com/`,
  **≥ 1 request/second pacing**, one file per trading day.
- Schema of source row: `Index Name, Index Date (DD-MM-YYYY), Open/High/Low/Closing
  Index Value, Points Change, Change(%), Volume, Turnover, P/E, P/B, Div Yield`.
  **Only OHLC + Date + Volume are used**; metrics columns dropped.

### 2.2 Public seams (frozen for golden evals)

```
fetch_eod_index(index_name, start_date, end_date, get=<real HTTP>) -> pd.DataFrame
refresh_store(symbol, start_date, out_dir, get=<real HTTP>) -> manifest: dict
```

- `get(url) -> bytes` is the **single network boundary**; it defaults to the real
  session implementation. Golden evals pass a stub reading committed payloads —
  **no network in any test** (same hermetic rule as 0001).
- `fetch_eod_index` returns columns exactly `date,open,high,low,close,volume`,
  ISO dates, ascending, `volume` int64 — i.e. **0001's fixture schema**, so the frame
  feeds `build_store` directly (validation is reused, never duplicated).
- `symbol "^NSEI"` maps to `Index Name == "Nifty 50"` via a small frozen dict
  `{"^NSEI": "Nifty 50"}`; store file remains `data/parquet/^NSEI.parquet` (0001 seam
  untouched). Unknown symbol → `ValueError` naming `symbol`.
- `refresh_store` returns **exactly 0001's five manifest keys** (no new keys).

### 2.3 Update strategy (user decision: full refetch + rewrite — reconciled)

**The tension, stated openly:** NSE publishes **one day per file**, so a literal
"re-download 19 years every run" means ~4,673 paced requests per night — infeasible
(NSE rate-limits; BRD §7.1 wants ≤90 s batches). Reconciliation:

1. **Local master ledger** `data/eod/{symbol}.csv` (append-only, git-ignored under
   `/data/`) accumulates fetched sessions — the only fetched state kept.
2. **Delta fetch:** each run requests only files for days after the master's last date
   up to `end_date`. Non-trading days publish no file → 404 → skipped (holidays need
   no calendar). A week-long outage self-heals on the next run by catching up.
3. **Full rewrite always:** master ledger → `build_store(...)` (0001) → Parquet,
   complete overwrite, content-deterministic. **No merge/append logic ever touches
   the Parquet** — that is what the user's "full rewrite" decision rules out.
4. **Cold start:** when master is absent, the loop starts from `start_date`
   (backfill ≈ 4,673 files × ≥1 s pacing ≈ **~1 h one-time, resumable** — it stops and
   restarts from wherever the master got to).

### 2.4 Validation & correctness

- Row mapping: `Index Date DD-MM-YYYY → ISO`, `Open/High/Low/Closing Index Value →
  open/high/low/close`, `Volume → volume` (real aggregate index volume, e.g.
  412,554,239 on 2026-10-05 — strictly better than the fixture's yfinance volume).
- Missing `Nifty 50` row in a 200 response → `ValueError` naming `row`.
- All downstream validation (columns, dates, OHLC sanity, volume, nulls) is **delegated
  to 0001's `build_store`** — already frozen and tested; 0002 adds none of it.
- A response body that is not parseable as CSV → `ValueError` naming `html` (HTML
  error/bot page served with 200).

### 2.5 Fixtures (committed alongside this spec)

- `tests/fixtures/ind_close_all_20261005.csv` — real NSE payload, 17,473 bytes,
  168 lines, sha256 `f0b8004e9bc79b11cff3c939cb42cdeb4a31b71ebd03942b98b57f44fa3bc9ba`.
- Plus the existing 0001 fixture for end-to-end composition tests.
- Frozen rule: evals stub `get()` with these files; real HTTP is never touched.

### 2.6 Acceptance summary (for Gate 2 authoring)

- Given stubbed `get`, `refresh_store("^NSEI", ...)` on a cold start with the sample
  payload → master CSV contains the mapped 2026-10-05 row; manifest keys exactly
  `{"symbol","rows","first_date","last_date","parquet_path"}`; Parquet readable,
  row OHLC equal to the payload's Nifty 50 row.
- Given an existing master ending 2026-10-05, a run with `end_date` covering only
  holidays (404s) → **zero new requests succeed, store unchanged, no error**.
- Nightly-path budget: **≲ 2 requests + full rewrite ≲ 5 s** (sanity, not SLA).

---

## 3. What Is NOT Needed (Negative Scope)

- **No CLI / scheduler / cron file** — function-only (user decision); wiring the
  nightly job is a later spec. Transient failures are handled by the caller simply
  re-running (natural retry; no retry framework here).
- **No yfinance, no Kite Connect, no equity `BhavCopy_*` securities files, no
  fallback chain** — source is NSE index file only (user decision).
- **No split/bonus adjustment logic** — indices have no splits; equity adjustment
  belongs to a future equity spec.
- **No 2,000-symbol batch, multiprocessing, or ≤90 s SLA enforcement** (BRD Phase 2).
- **No trading-calendar file**, no gap-report/monitoring, no alerts, no SQLite, no
  API/UI changes (0001 seam untouched).
- **No master-ledger compaction, restatement back-propagation, or de-duplication
  beyond "skip days already in the master".**

---

## 4. Architecture Alignment (Kailash Nadh)

- Flat CSV ledger + derived Parquet: two boring files, zero services.
- One injectable `get` boundary instead of a client class or library wrapper.
- Composes spec 0001 verbatim rather than reimplementing validation.
- Pacing > parallelism: ~1 req/s keeps us a polite, unblocked client on a free source.

---

## 5. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is 404-skip (no trading calendar); upgrade path is a NSE
  holiday calendar when an upstream path change could silently stall updates —
  mitigated today by cron monitoring last_master_date recency.`
- `# ponytail: ceiling is ~1 h paced backfill; upgrade path is seeding the master
  ledger from an existing store export.`
- `# ponytail: ceiling is append-only master (no restatement correction); upgrade
  path is nightly full re-key when NSE revises published files.`
- **Volume semantic drift:** production store will carry NSE aggregate volume while
  the 0001 fixture (yfinance) keeps 1,333 zero-volume days. The fixture remains
  **test data for 0001's eval only**; specs 0003+ must not assume fixture volume
  equals production volume.

---

## 6. Frozen Decisions (pre-Gate-1 evidence session)

| # | Decision | Choice |
|---|---|---|
| 1 | Data source | **NSE `ind_close_all` only** (user, over yfinance recommendation) |
| 2 | Update strategy | **Full refetch + rewrite** — reconciled as delta-fetch + full Parquet rewrite via master ledger (§2.3) |
| 3 | Entry point | **Function-only** — no CLI in 0002 |
| 4 | Hermetic evals | `get()` injectable; stubs read committed payloads; no network in tests |
| 5 | Seam style | Pure functions returning dicts, consistent with 0001 |

---

## 7. Gate 1 Sign-Off

- [x] **User approves** this requirement spec, including the §2.3 reconciliation of
      "full refetch + rewrite" with one-file-per-day reality → agent may author Gate 2
      test spec `specs/tests/0002-eod-data-fetcher.md`. **(Approved 2026-10-06)**

**STOP:** No Gate 2 or Gate 3 work proceeds until the box above is checked by the user.
