# Gate 1 — Requirement Spec `0009-eod-nightly-job`

**Status:** `APPROVED — Gate 1 signed off 2026-10-07 (user); Gate 2 test spec in authoring`
**Date:** 2026-10-07
**Consumes:** specs `0001` (store), `0002` (fetcher), `0007` (snapshot) — all Gate 3 complete,
108 evals green; the three seams exist but nothing calls them in sequence.

---

## 1. User Value Rationale (DIRECT — no waiver needed)

- **Why a paying trader cares:** every tier's headline promise is *"Updates: Daily
  End-of-Day"* (BRD §2.2). Today the pipeline is three frozen functions that only a
  human runs by hand; `data/static/api/v1/^NSEI.json` is frozen at `last_date:
  2026-10-05`. The gap is already visible: the master ledger has a 2026-10-06 row
  (4,674 rows) while the Parquet store and snapshot still end at 2026-10-05 —
  fetch advanced, nothing rebuilt. Without an automated nightly run, the Free tier's "ask today's pattern"
  loop silently stops — the trader sees yesterday's regime and yesterday's analogs
  presented as today's.
- **Monetization link:** this is the heartbeat of BRD §4.2 ("compute after close,
  serve static JSON"). It converts specs 0001–0007 from a tested library into the
  product's daily value delivery, and it is the **cron-monitoring mitigation** that
  0002's ceiling and 0007's ceiling both explicitly promised ("mitigated today by cron
  monitoring last_master_date recency").
- **Phase fit:** BRD §7.2 Phase 1 = engine + dashboard on NIFTY 50. This spec closes
  the data-freshness half; the dashboard (spec 0008) consumes what this job refreshes.

---

## 2. What Is Needed (Scope)

### 2.1 Deliverable — one function + one runnable entry point

```
run_eod_job(symbol, start_date, end_date, parquet_dir, snapshot_dir, get=<real HTTP>) -> report: dict
```

- Composes **exactly two existing seams, zero re-implementation**:
  1. `refresh_store(symbol, start_date, parquet_dir, get=get, end_date=end_date)`
     (0002) → master ledger + full Parquet rewrite. The ledger path stays 0002's
     derived rule (`parquet_dir.parent / "eod" / "{symbol}.csv"`); the job adds no flag
     for it.
  2. `build_snapshot(symbol, parquet_dir, snapshot_dir)` (0007) → byte-deterministic
     `dtwmagic.api.v1` JSON.
- All parameters explicit, **no path defaults in the function** (0007 posture,
  frozen decision #8 there). `get` is the single network boundary and is injectable —
  hermetic evals, same rule as 0001/0002.
- `end_date=None` means "today", delegated unchanged to 0002.

A thin CLI wraps it so cron has a process to call:

```
python -m src.eod_job [--symbol ^NSEI] [--start-date 2007-09-17] [--end-date YYYY-MM-DD]
                      [--parquet-dir data/parquet] [--snapshot-dir data/static/api/v1]
```

- stdlib `argparse` only; defaults are the repo layout above; real HTTP (`_real_get`).
- Prints **one JSON line** (`json.dumps(report)`) to stdout — machine-parseable for
  cron logs, no logging framework.
- **Exit code 0 = `report["ok"]` true; 1 otherwise.** This is the contract a cron
  wrapper or human monitors.

### 2.2 Report shape (frozen for golden evals)

```json
{"symbol": "^NSEI",
 "end_date": "2026-10-07",
 "ok": false,
 "refresh": {"symbol": ..., "rows": ..., "first_date": ..., "last_date": ..., "parquet_path": ...} | null,
 "snapshot": {"symbol": ..., "path": ..., "bytes": ..., "last_date": ..., "windows": ..., "k": ...} | null,
 "error": "refresh: <message>" | "snapshot: <message>" | null}
```

- `refresh` / `snapshot` are the **verbatim manifests** of 0001/0002 and 0007
  respectively (keys unchanged); `null` = that stage did not run or failed.
- Failure policy (honesty contract):
  - `refresh` raises → `error` starts `"refresh: "`, `snapshot` stays `null`, the
    **previous snapshot file is left untouched** (a stale-but-valid artifact beats a
    deleted one), `ok: false`.
  - `refresh` succeeds, `build_snapshot` raises (e.g. store `< 252` rows → 0005's
    regime gate) → `error` starts `"snapshot: "`, `refresh` manifest kept, `ok: false`.
    The rewritten store stays on disk; the next run self-heals from the ledger.
  - Success → `ok: true`, both manifests present, `error: null`.

### 2.3 Scheduling (documented, not committed)

The spec ships a **crontab line as documentation** (in this file and the module
docstring), not a cron/systemd file:

```
30 17 * * 1-5 cd /path/to/dtwmagic && .venv/bin/python -m src.eod_job >> data/eod/job.log 2>&1
```

17:30 IST weekdays: NSE publishes `ind_close_all` after the 16:30 close; 0002's ≥1 s
pacing and 0007's ≲2 s build make the run finish well before 17:35.

### 2.4 Acceptance summary (for Gate 2 authoring; the test spec freezes the details)

All hermetic — `get` stubbed with committed fixtures, tmp dirs, no network:

- **No-op freshness run:** master seeded from the 0001 fixture CSV,
  `end_date = 2026-10-05` (== master last date) → **zero `get` calls**, `ok: true`,
  and the written snapshot is **byte-identical to 0007's pinned fixture**
  (sha256 `fa4c598c…b781897`, 63,791 bytes). A second identical run re-pins determinism.
- **Delta run:** master seeded from the 0001 fixture **minus its final row**
  (last date 2026-10-01), `end_date = 2026-10-05`, stub `get` returning
  `tests/fixtures/ind_close_all_20261005.csv` for 05-10-2026 and `None` for
  02/03/04-10-2026 → 02 is Gandhi Jayanti (a real NSE holiday) and 03/04 are the
  weekend, so all three 404-skip, 05 appends, full rewrite back to 4,673 rows,
  snapshot again byte-identical to the pin. Proves fetch → store → snapshot end to end.
  (The fixture itself has no 2026-10-02 row — verified — so both paths agree.)
- **Transport failure:** stub `get` raising `OSError` → `ok: false`,
  `error` starts `"refresh: "`, `snapshot: null`, a pre-existing snapshot file
  **byte-unchanged**.
- **Snapshot-stage failure:** master seeded with a single payload day (1 row → store
  `< 252` rows) → refresh manifest present, `error` starts `"snapshot: "`,
  `ok: false`.
- **Unknown symbol** (function and CLI) → `ok: false`, `error` names the symbol;
  CLI exits 1.
- **CLI exit codes:** offline success run (no-op args above) exits 0; unknown-symbol
  run exits 1; `--help` exits 0.
- Sanity (not an SLA): no-op run ≲ 3 s (store rewrite ≈1 s + snapshot ≈0.5 s);
  full suite (108 existing evals) stays green and unmodified (sha guards).
- **Pin provenance:** `/data/` is git-ignored output and 0007's sha pin is asserted
  against a store built in `tmp_path` from the committed fixture (`tests/test_0007.py`),
  so a real refresh changing `data/static/api/v1/^NSEI.json` bytes touches **no**
  frozen eval.

### 2.5 Dependencies

**None.** `argparse`, `json`, `sys` are stdlib; the job adds no package.

---

## 3. What Is NOT Needed (Negative Scope)

- **No cron/systemd file, no scheduler daemon, no watch loop, no container** — the
  crontab line is documentation (§2.3); scheduling infrastructure is the operator's.
- **No retry framework** — 0002's natural re-run posture stands: transient failure ⇒
  nonzero exit ⇒ next cron tick retries. No alerting, email, or Telegram (BRD §8.1.4
  bars broadcast channels anyway).
- **No multi-symbol batch, multiprocessing, or ≤90 s SLA** — single symbol per call
  (0001/0003/0007 posture); Phase-2 batching arrives with F-06 where 0007's rank-only
  seam exists.
- **No staleness/trading-calendar logic** — a holiday run legitimately fetches
  nothing and exits 0 (0002's 404-skip ceiling); freshness monitoring is
  `report.last_date` + exit code, observed externally.
- **No changes to 0001/0002/0003/0004/0005/0006/0007 seams, payloads, or files** —
  their frozen evals and sha guards are regression gates; this spec only *calls* them.
- **No dashboard/UI (spec 0008), no gzip/atomic-replace (0007 ceilings), no SQLite,
  no logging framework, no config file, no CLI beyond the flags in §2.1.**

---

## 4. Architecture Alignment (Kailash Nadh)

- Two function calls and a loop-free wrapper: the whole "pipeline" is composition,
  rung 6 (can it be one screen? it nearly is).
- Boring delivery: stdout JSON + exit code — the most monitorable interface that
  exists, with zero infrastructure.
- Pre-computation over live complexity (BRD §4.1): nothing here serves HTTP; the
  artifact remains a static file Nginx/CDN can hand out.

---

## 5. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is sequential single-symbol run; upgrade path is 0007's
  rank-only seam + multiprocessing when BRD §7.1's 2,000-stock <90 s budget is
  measured (Phase 2).`
- `# ponytail: ceiling is exit-code + last_date freshness monitoring; upgrade path
  is an NSE holiday calendar if a silent upstream stall becomes real (0002's
  ceiling, unchanged).`
- `# ponytail: ceiling is a ~1 h paced cold-start backfill before the first
  snapshot can build (store needs >= 252 rows for 0005's regime rank); upgrade
  path is seeding the master from an existing store export (0002's ceiling).`
- Inherited, unchanged: 0002's append-only master / 404-skip; 0007's plain
  open-write (no atomic swap), five fixed windows, `^NSEI` URL-unsafe filename.

---

## 6. Frozen Decisions (pre-Gate-1 session)

| # | Decision | Choice |
|---|---|---|
| 1 | Entry shape | **Function `run_eod_job(...)` + `python -m src.eod_job` CLI** — cron needs a process; tests need a function (0002 deferred exactly this wiring) |
| 2 | Composition | **`refresh_store` → `build_snapshot` only** — zero re-implementation, no new math |
| 3 | Report | **Frozen 6-key dict, verbatim sub-manifests, `error` prefixed `refresh:`/`snapshot:`** |
| 4 | Failure policy | **Stage-honest, never deletes a good snapshot, nonzero exit** — a stale artifact is data, a silent stale artifact is a bug |
| 5 | Scheduling | **Documented crontab line, no committed cron/systemd file** |
| 6 | Symbol scope | **Single symbol per call, default `^NSEI`** — multi-symbol loop is Phase 2 (negative scope) |
| 7 | Network | **`get` injectable end-to-end; committed fixtures only in evals** (0001/0002 hermetic rule) |
| 8 | Output location | **CLI defaults = repo layout** (`data/parquet`, `data/static/api/v1`); function keeps explicit args; `/data/` stays git-ignored |

---

## 7. Gate 1 Sign-Off

- [x] **User approves** this requirement spec (incl. the §2.1 entry shapes, §2.2
      report/failure contract, §2.4 acceptance set, and §6 frozen decisions) →
      agent may author Gate 2 test spec `specs/tests/0009-eod-nightly-job.md`.
      **(Approved 2026-10-07)**
- [x] **No new dependency** (§2.5) — nothing to approve. **(Approved 2026-10-07)**

**STOP:** No Gate 2 or Gate 3 work proceeds until the box above is checked by the user.
The Gate 2 test spec is **IMMUTABLE once approved**.
