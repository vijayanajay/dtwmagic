# Gate 1 — Requirement Spec `0010-v2-query-block`

**Status:** `APPROVED — Gate 1 signed off 2026-10-07 (user: "approved"); Gate 2 test spec in authoring; Gate 3 not started.`
**Date:** 2026-10-07
**Consumes:** spec `0007-eod-snapshot` (composition seams + serialization recipe — its
`build_snapshot` and frozen v1 file stay byte-untouched), spec `0009-eod-nightly-job`
(the nightly producer whose snapshot stage gains the v2 write). **Deferred by:**
spec `0008-phase1-dashboard` §6 #8 (the v2 `query` block was explicitly flagged there
as the missing prerequisite for F-05's ghost overlay).
**Side:** Backend only (BRD §4.4 isolation) — produces JSON; renders nothing.

---

## 1. User Value Rationale (DIRECT — no waiver needed)

- **Why a paying trader cares:** F-05 (BRD feature table) is the product's flagship
  visual-audit feature — *"Overlays top 3–5 matched historical price trajectories
  directly on top of the live candle chart, labeled with exact historical dates"* —
  and it is the Free(top-1)/Pro(top-5) conversion driver. Spec 0008 shipped every
  other Phase-1 surface but had to defer F-05's live-chart projection (§6 #8) with
  this exact reason: **v1 carries no current-window prices.** Without them the page
  cannot (a) re-anchor each matched episode's raw historical forward path onto
  today's price (raw prices from 2012 are meaningless on a 2026 chart),
  (b) draw today's own last-L trajectory as the anchor under the ghosts, or
  (c) show any current-price context next to the historical stats.
- **The data already exists:** the query window (the last ≤60 sessions of OHLC) is
  in the store the nightly job has already read. This spec serializes ~60 rows the
  pipeline already holds — zero new compute, zero new data sources, ~3.5 KB per file.
- **Compliance link:** the overlay is pure descriptive-past display (BRD §8.2D /
  F-05's *"visual historical audit"*); adding historical OHLC to a historical-search
  artifact introduces no predictive claim.

---

## 2. What Is Needed (Scope)

### 2.1 Public seam — one function (frozen for golden evals)

```
build_snapshot_v2(symbol, parquet_dir, out_dir) -> dict   # the manifest
```

- All three arguments required, **no defaults** — same call shape as 0007.
- Manifest keys **identical to 0007's**: `{symbol, path, bytes, last_date, windows, k}`
  (pointing at the **v2** file it wrote).
- Writes exactly one file: `{out_dir}/{symbol}.json`, creating `out_dir` (with
  parents) if missing. Full rewrite every run (same derived-state posture as 0001/0007).
- Imports `WINDOWS`/`K` from `src.snapshot` (single source of truth — a future
  window-set change cannot desynchronize v1 and v2) and reuses 0005's wrapper /
  0004's reducer exactly as `build_snapshot` does. **`src/snapshot.py` itself is
  not modified.**

### 2.2 Output document (frozen schema)

```jsonc
{
  "schema": "dtwmagic.api.v2",
  "symbol": "^NSEI",
  "bars": 4675,
  "last_date": "2026-10-07",
  "regime": { "trend": "bearish", "volatility": "normal",
              "cell": "bearish-normal", "p252": 0.5436507936507936 },
  "windows": { "5": {…}, "10": {…}, "15": {…}, "30": {…}, "60": {…} },
  "query": {
    "L": 60,
    "candles": [
      { "date": "2026-07-14", "open": …, "high": …, "low": …, "close": … },
      /* … exactly 60 rows, oldest → newest, last row's date == last_date … */
    ]
  }
}
```

- **Top-level key order is exactly the list above** — v1's prefix order is
  preserved and `query` is appended (the v2 file reads as "the v1 document plus
  one block").
- **For the same store state, `symbol`/`bars`/`last_date`/`regime`/`windows`
  deep-equal the v1 document's** — only the `schema` string and the `query` block
  differ between the two files.
- **Candle row shape is `forward`'s row shape exactly** (dict, insertion order
  `date/open/high/low/close`, ISO date string, store floats verbatim) — the
  frontend reuses one row renderer for historical forwards and today's window.
- **`candles` = the store's last `min(60, len(df))` rows**, `L: 60` recorded for
  self-description. 60 = `max(WINDOWS)`, so for every offered window the query
  pattern is simply `candles.slice(-L)` — no per-window duplication (payload
  stays one block, ~3.5 KB, not five overlapping copies).
- No volume column (F-07's Elite scope), no derived indicators, no returns —
  raw historical OHLC only; all math stays the frontend's/display's concern.

### 2.3 Semantics pinned by real edge cases

- **Zero-pool days:** the `query` block ships **unconditionally** — it is store
  state, not regime state. On the 416-row slice store (0007 §4) the v2 document
  carries 60 candles alongside `summary: null` windows; valid, not an error.
- **Short store:** `candles` degrades to `min(60, len(df))` — no new failure mode;
  whatever minimum the windows require remains 0005's validation, unchanged.
- **Freshness:** `last_date` remains the only freshness stamp; `candles[-1].date`
  equals it by construction. No `generated_at`, no wall-clock, no randomness.

### 2.4 Serialization & determinism (frozen)

- Identical recipe to 0007 §2.4: `json.dump(doc, fh, ensure_ascii=False)` +
  trailing `"\n"`, utf-8, **no `indent`, no `sort_keys`** — insertion order gives
  the §2.2 key order and byte-stable output. The same store state yields a
  **byte-identical** v2 file across runs (Gate 2 pins the fixture file's sha256
  after a probe round).

### 2.5 Error contract

Identical to 0007 §2.5 — `build_snapshot_v2` fails exactly where and how
`build_snapshot` fails (same seams underneath):

| Condition | Behavior |
|---|---|
| Store missing | `ValueError`, keyword `store` |
| Store < 252 rows / unclassifiable query | `ValueError`, keyword `regime` |
| `out_dir` missing | **created** (`mkdir(parents=True, exist_ok=True)`) |
| I/O failure while writing | plain `OSError` propagates |

### 2.6 Nightly wiring — the only edit to an existing file (`src/eod_job.py`)

```python
try:
    man = build_snapshot(symbol, parquet_dir, snapshot_dir)          # v1, unchanged
    build_snapshot_v2(symbol, parquet_dir,
                      Path(snapshot_dir).parent / "v2")              # v2, new
    report["snapshot"] = man                                         # only after BOTH succeed
except Exception as exc:
    report["error"] = f"snapshot: {exc}"
    return report
```

- **The report contract is frozen and stays frozen:** exactly 6 keys
  (`symbol, end_date, ok, refresh, snapshot, error`), `snapshot` = the v1 manifest
  verbatim (its pinned file sha never moves), error prefix stays `snapshot: `.
- **v2 path is derived, not flagged:** `Path(snapshot_dir).parent / "v2"` →
  prod default `data/static/api/v1` → **`data/static/api/v2/{symbol}.json`**
  (BRD §4.4's versioned path convention). No new CLI flags; the documented
  crontab line (`30 17 * * 1-5 … python -m src.eod_job`) is unchanged — one
  command still refreshes everything.
- **Stage-honesty preserved for every frozen failure path:** any failure in either
  build → `snapshot: None` + `error` + `ok: False` (exactly what T-005 asserts);
  a v2 failure never touches the prior good v1 file (deterministic rewrite, no
  deletion anywhere).
- **Zero edits to `tests/test_0007.py`, `tests/test_0008.py`, `tests/test_0009.py`
  or any frozen spec doc** — this is a hard constraint, not a preference:
  `test_0008`'s autouse guard pins `test_0009.py`'s sha, and both pin
  `test_0001..0007`, so touching any prior eval cascades revisions across three
  frozen specs. The §2.6 shape above is designed so **all 128 existing evals stay
  green unmodified** (re-verified at Gate 3).

### 2.7 Dependencies

**None new** — stdlib `json` + already-installed pandas/pyarrow.

### 2.8 Hermetic evals & performance

- New eval `tests/test_0010.py`: hermetic fixture store into `tmp_path`, socket
  guard on, store Parquet bytes unchanged after the run. Autouse guard pins both
  fixture shas **and all nine prior eval files** (`test_0001..test_0009`), the
  established posture (0007 froze 6, 0009 froze 7, 0008 froze 9).
- **Performance budget:** the snapshot stage now runs the search pipeline twice.
  Frozen probe targets before Gate 2 freeze: whole `run_eod_job` no-op best-of-3
  **≤ 2.5 s** while `test_t010`'s frozen `best ≤ 3.0 s` (probe 0.64 s) must stay
  green; payload grows ~3.5 KB (63.9 KB → ≲68 KB). **If dual-build ever pushed
  T-010 over its limit, the fix is a single-pass builder writing both files —
  never a test edit.**

---

## 3. What Is NOT Needed (Negative Scope)

- **No frontend changes of any kind** — `data/static/index.html` still fetches
  v1 and keeps working; specs 0001–0009 code (except the §2.6 eod_job stage) and
  all prior test files are untouched. **Rendering the ghost overlay is a separate
  frontend spec (0011) under BRD §4.4 isolation** — backend never embeds HTML/JS,
  frontend never imports Python.
- **No retirement or rewrite of v1** — v1 stays byte-frozen because 0007's golden
  eval, 0009's snapshot-sha pins, and the live dashboard all consume it. The
  in-place "supersede" variant (bump `build_snapshot` itself, move `api/v1`,
  re-pin shas) is **explicitly rejected** — see §7 #1.
- **No analog-side window prices** (the *matched episodes'* preceding L-bar
  trajectories) — that would mutate 0003's frozen analog item keys
  (`date/distance/score/close/forward`) and 0007's deep-equality pins; the full
  BRD §6 Layer-2 twin-sparkline *pattern geometry* is deferred (§6 ceiling).
- **No volume, no indicators, no derived returns** in the query block (F-07 later).
- **No changes to 0003/0004/0005 math, payloads, or files** — their frozen evals
  are regression gates.
- **No new dependencies, no new CLI flags, no scheduler/cron changes, no
  multi-symbol batch, no intraday/live data, no SQLite, no gzip, no
  atomic-replace choreography** (0007's inherited ceilings).

---

## 4. Acceptance Summary (for Gate 2 authoring; the test spec freezes the details)

- **Schema:** v2 doc top-level keys exactly
  `["schema","symbol","bars","last_date","regime","windows","query"]`;
  `schema == "dtwmagic.api.v2"`; v2 `windows`/`regime`/`bars`/`last_date`
  deep-equal a same-store v1 `build_snapshot` document.
- **Query block:** `L == 60 == max(WINDOWS)`; `len(candles) == 60` (fixture);
  candle keys exactly `["date","open","high","low","close"]` in that insertion
  order; last candle's `date == last_date`; candle values deep-equal the store's
  tail rows — **last-candle close and a mid-window candle are probe-pinned before
  Gate 2 freeze.**
- **Determinism:** two v2 builds on the same store are byte-identical; the
  fixture v2 file sha256 is **probe-pinned before freeze**; a changed store
  changes the file.
- **Edge store:** the 416-row slice store yields 60 candles + its zero-pool
  windows without raising.
- **Wiring:** `run_eod_job` still reports exactly the 6 frozen keys; the v1 file
  still hashes to 0009's frozen `fa4c598c…` pin; the v2 file appears at the
  sibling `v2/` dir with the §2.2 content; T-001..T-010 **all pass without a
  single byte of edit** (probe-verified before Gate 2 freeze).
- **Suite:** all 128 existing evals green and unmodified; new eval adds its own
  ~8–10 scenarios.
- **Perf/hermetic:** T-010 frozen threshold still green (dual-build time
  probed); no network; store bytes unchanged.

---

## 5. Architecture Alignment (Kailash Nadh)

- **Additive over destructive:** one new ~40-line function + one 4-line change in
  an existing stage — versus a schema migration that would re-pin three frozen
  evals. Smallest diff that delivers the trader-visible feature.
- **Composition only:** same 0005 wrapper + 0004 reducer calls as v1; the query
  block is a `df.tail()` serialization, not new computation (rung 3: pandas
  already has it).
- **§4.4 honored literally:** *"Schema changes require an explicit API version
  bump (e.g. v1 → v2) approved through Gate 1"* — that approval is this document;
  the versioned path `api/v2/` is where the bumped payload lands.
- **Pre-computation unchanged:** the nightly batch pays ~2× the (sub-second)
  snapshot cost once; serving stays a static file read at $0 egress.

---

## 6. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is the v2 manifest being written but not reported in
  eod_job's 6-key report; upgrade path is a 7th "snapshot_v2" key under a
  user-directed 0009 test-spec revision, if ops ever needs to watch it.`
- `# ponytail: ceiling is running the search pipeline twice per night (v1+v2);
  upgrade path is a single-pass builder emitting both files if T-010's 3.0s
  budget is ever felt.`
- `# ponytail: ceiling is today's window only — no analog-side pattern prices,
  so twin-sparkline geometry (BRD §6 Layer 2) compares forward paths only;
  upgrade path is a v3 block + user-approved 0003/0007 pin revision.`
- `# ponytail: ceiling is fixed 60 candles; upgrade path is deriving the count
  from the full 5..60 grid decision (0007 §6) or a longer anchoring history.`
- `# ponytail: ceiling is the derived sibling path (snapshot_dir/../v2);
  upgrade path is an explicit --snapshot-v2-dir flag if a split layout ever
  deploys.`
- Inherited (0007): plain open-write (no atomic swap), no gzip, `^` in filename,
  single-process build.

---

## 7. Frozen Decisions (pre-Gate-1 session; approval of this spec approves all eight)

| # | Decision | Choice |
|---|---|---|
| 1 | Versioning strategy | **Additive dual-write: byte-frozen v1 + new v2 file** — honors §4.4's bump while keeping every 0007/0008/0009 pin and guard green with zero test edits. In-place supersede (mutating `build_snapshot`, moving `api/v1`, re-pinning shas) **rejected**: it cascades sha-guard revisions across three frozen specs (0008 pins 0009's eval sha). 0008 §6 #8 noted the supersede cost; additive delivers the same trader-visible outcome without paying it |
| 2 | Schema & path | `"dtwmagic.api.v2"`; file at `data/static/api/v2/{symbol}.json` (§4.4 convention); v1 keeps `api/v1/` for the live dashboard until the frontend spec switches |
| 3 | Query shape | `query: {"L": 60, "candles": [{date,open,high,low,close} × 60]}` — reuses `forward`'s row shape; one block, sliced `(-L)` per window; no volume |
| 4 | Placement | Top-level `query` **appended after `windows`** — v1's key prefix preserved byte-for-byte within the shared portion |
| 5 | Seam | `build_snapshot_v2(symbol, parquet_dir, out_dir) -> manifest`, no defaults; `WINDOWS`/`K` imported from `src.snapshot`; `src/snapshot.py` unmodified |
| 6 | Nightly wiring | Same eod_job snapshot stage writes both files; report stays **exactly 6 keys** with the v1 manifest under `snapshot`; v2 dir derived as `Path(snapshot_dir).parent / "v2"`; manifest assigned only after both builds succeed; no new CLI flags |
| 7 | Isolation | **Backend-only spec** — no UI copy, no HTML/CSS/JS (§8.2D risk = none: no user-facing strings); ghost-overlay rendering deferred to frontend spec 0011 |
| 8 | Determinism | v2 byte-identical reruns under the 0007 serialization recipe; fixture sha probed and pinned at Gate 2; `last_date` is the freshness stamp (no `generated_at`) |

---

## 8. Gate 1 Sign-Off

- [x] **User approves** this requirement spec (incl. the §2.2 v2 schema, §2.6
      eod_job dual-write with its frozen report contract, and the §7 decisions —
      **especially #1 additive-vs-supersede and #6 derived v2 path**) → agent may
      author Gate 2 test spec `specs/tests/0010-v2-query-block.md`. **(Approved
      2026-10-07)**
- [x] **No new dependency requested** (§2.7) — nothing to approve. **(Approved
      2026-10-07)**

**STOP:** No Gate 2 or Gate 3 work proceeds until the boxes above are checked by
the user. The test spec is **IMMUTABLE once approved**; Gate 3 (code) still
requires that separate approval.
