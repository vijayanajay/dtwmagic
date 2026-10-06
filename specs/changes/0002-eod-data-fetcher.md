# Gate 4 — Change & Decision Record `0002-eod-data-fetcher`

**Date:** 2026-10-06
**Gates:** Gate 1 approved (incl. §2.3 reconciliation) → Gate 2 frozen with four
interface freezes + revision R1 → Gate 3 Red → Green complete.

---

## 1. Files Added / Modified

| File | Change |
|---|---|
| `specs/requirements/0002-eod-data-fetcher.md` | Added — Gate 1 (approved) |
| `specs/tests/0002-eod-data-fetcher.md` | Added — Gate 2 (FROZEN, 15 scenarios, revision R1) |
| `tests/test_0002.py` | Added — the frozen eval T-001…T-015 |
| `src/eod_fetch.py` | Added — `fetch_eod_index` + `refresh_store` |
| `tests/fixtures/ind_close_all_20261005.csv` | Added — real NSE payload (sha256 pinned) |
| `src/ohlcv_store.py` | **Untouched** (0001 evals re-run green regardless) |

---

## 2. Architectural & Quantitative Decisions

1. **Delta fetch → append-only master CSV → always-full Parquet rewrite** (Gate 1
   §2.3 reconciliation): nightly cost is ~1–2 requests instead of ~4,673; the Parquet
   is derived state, so "full rewrite" holds while no merge logic ever touches it.
   Non-trading days = 404 = skip, so no trading calendar is needed.
2. **`get` is the only network boundary** (`bytes` | `None`) — hermetic evals stub it;
   the real implementation encapsulates warmup, browser UA + referer, and ≥1 s pacing.
3. **Composition over re-implementation:** all validation is delegated to 0001's
   `build_store` (proven by T-013 injecting a bad ledger row); row mapping
   DD-MM-YYYY → ISO and Nifty-name filtering are the only new transforms.
4. **Symbol map `{"^NSEI": "Nifty 50"}`** rejected unknowns *before* any request
   (T-009), keeping the store file name stable for spec 0001/0003 consumers.
5. **Revision R1 (user-directed, pre-code):** T-011's row arithmetic corrected
   `5 → 4` — a frozen-spec bug found by re-reading scenarios before writing code, not
   a test relaxed to pass.

---

## 3. Known Limits & Ceilings

- 404-skip conflates "holiday" with "path change" — mitigated by caller monitoring of
  master recency; holiday calendar is the documented upgrade path.
- Cold-start backfill ~1 h paced, resumable via the master.
- Append-only master: no restatement correction.
- Production volume = NSE aggregate; 0001's yfinance fixture volume differs (flagged
  in Gate 1 §5; fixture stays test-only).
- Real `get` is outside the hermetic eval by design — covered by the live smoke below.

---

## 4. Verification Output (Gate 3)

```
RED:   15 failed in 6.12s                    RED_EXIT=1   (stub src/eod_fetch.py)
GREEN: 15 passed in 3.10s                    GREEN_EXIT=0 (implementation)
Full suite (0001 + 0002): 38 passed          ALL_EXIT=0
Live smoke (real NSE, default get, 1 req): PASS — 2026-10-05 row
  22532.4 / 22621.8 / 22397.1 / 22555.75 / vol 412554239, live_exit=0
  (found + fixed a real bug: NSE root answers 404 to scripts while still
   setting session cookies — warmup now tolerates it; tests untouched)
Final suite after fix: 38 passed             FINAL_EXIT=0
```

**Bug found by live smoke, not by eval:** the warmup request died on NSE's scripted
404 root response before any file request. Fixed in `_real_get` (catch `HTTPError`
during warmup); no test, assertion, or fixture was changed to achieve green.
