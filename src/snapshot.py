"""EOD static-JSON snapshot builder (spec 0007, BRD 4.2): 0003+0004+0005 -> one file.

Composes the frozen seams: one query regime (0005, L-independent), per-window
in-regime analogs (0005/0003), and the outcome reducer (0004) — written as a
byte-deterministic document so the same store state always yields the same file.

# ponytail: ceiling is five fixed windows; upgrade path is the full 5..60 grid
# once a measured Phase-2 budget exists (file size x 56).
# ponytail: ceiling is plain open-write; upgrade path is os.replace atomic swap
# if a reader ever observes partial files.
# ponytail: ceiling is symbol in the filename (^ is URL-unsafe); upgrade path is
# a URL-alias map when the dashboard serves it.
# ponytail: ceiling is single-process per-symbol build; upgrade path is the
# rank-only seam (0006 section 6) + multiprocessing for BRD 4.1's 2000-stock <90s.
# ponytail: ceiling is no gzip; upgrade path is letting Nginx/CDN compress.
"""
import json
from pathlib import Path

import pandas as pd

from src.outcome_stats import summarize_analogs
from src.regime import search_analogs_regime

SCHEMA = "dtwmagic.api.v1"
WINDOWS = (5, 10, 15, 30, 60)
K = 10


def build_snapshot(symbol, parquet_dir, out_dir):
    """Write {out_dir}/{symbol}.json; return the manifest (Gate 1 2.1/2.2).

    Frozen serialization (0007 Gate 2 section 0 freeze 3): utf-8, newline="\\n",
    json.dump(..., ensure_ascii=False), trailing newline -> byte-deterministic.
    """
    store = Path(parquet_dir) / f"{symbol}.parquet"
    if not store.exists():
        raise ValueError(f"store not found for symbol {symbol!r}: {store}")
    df = pd.read_parquet(store)

    regime = None
    windows = {}
    for L in WINDOWS:
        res = search_analogs_regime(symbol, L, K, parquet_dir)
        if regime is None:
            regime = res["regime"]  # query-session state, L-independent (Gate 1 #5)
        analogs = res["analogs"]
        windows[str(L)] = {
            "L": L,
            "k": K,
            "analogs": analogs,
            # summarize_analogs([]) raises by contract; empty windows ship null
            # (Gate 1 2.3: zero-pool days are data, not errors).
            "summary": summarize_analogs(analogs) if analogs else None,
        }

    doc = {
        "schema": SCHEMA,
        "symbol": symbol,
        "bars": len(df),
        "last_date": str(pd.to_datetime(df["date"]).max().date()),
        "regime": regime,
        "windows": windows,
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{symbol}.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False)
        fh.write("\n")

    return {
        "symbol": symbol,
        "path": str(path),
        "bytes": path.stat().st_size,
        "last_date": doc["last_date"],
        "windows": list(WINDOWS),
        "k": K,
    }
