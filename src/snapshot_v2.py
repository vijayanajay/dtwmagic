"""EOD static-JSON snapshot builder, v2 with the query block (spec 0010, BRD 4.4).

Composes the same frozen seams as src/snapshot.py (0003 search + 0004 reducer
over 0005's regime wrapper) and appends the top-level `query` block — the
store's last 60 raw OHLC rows — which F-05's ghost overlay anchors onto today's
price (spec 0008 section 6 item 8's deferral, resolved by Gate 1 approval).
The v1 document stays byte-frozen in src/snapshot.py (Gate 1 7 #1).

# ponytail: ceiling is a second full search pass per night (v1 + v2); upgrade
# path is a single-pass builder emitting both files if T-010's 3.0s is felt.
# ponytail: ceiling is fixed 60 candles = max(WINDOWS); upgrade path is the
# 5..60 grid decision (0007 section 6) or a longer anchoring history.
# ponytail: ceiling is no analog-side pattern prices (twin-sparkline geometry
# stays forward-path-only); upgrade path is a v3 block + 0003/0007 pin revision.
"""
import json
from pathlib import Path

import pandas as pd

from src.outcome_stats import summarize_analogs
from src.regime import search_analogs_regime
from src.snapshot import WINDOWS, K

SCHEMA = "dtwmagic.api.v2"
QUERY_BARS = 60  # Gate 1 2.2: max(WINDOWS); window L's pattern = candles[-L:]


def build_snapshot_v2(symbol, parquet_dir, out_dir):
    """Write {out_dir}/{symbol}.json (v2 doc); return the manifest (Gate 1 2.1).

    Frozen serialization (0007 recipe, Gate 1 2.4): utf-8, newline="\\n",
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
            regime = res["regime"]  # query-session state, L-independent (0007 #5)
        analogs = res["analogs"]
        windows[str(L)] = {
            "L": L,
            "k": K,
            "analogs": analogs,
            # summarize_analogs([]) raises by contract; empty windows ship null
            # (0007 Gate 1 2.3: zero-pool days are data, not errors).
            "summary": summarize_analogs(analogs) if analogs else None,
        }

    # query block: raw store tail in forward-row shape (0010 Gate 1 2.2).
    n = len(df)
    take = min(QUERY_BARS, n)
    tail = df.tail(take)
    dates = pd.to_datetime(tail["date"]).dt.strftime("%Y-%m-%d").tolist()
    opens = tail["open"].to_numpy("float64")
    highs = tail["high"].to_numpy("float64")
    lows = tail["low"].to_numpy("float64")
    closes = tail["close"].to_numpy("float64")
    candles = [
        {
            "date": dates[i],
            "open": float(opens[i]),
            "high": float(highs[i]),
            "low": float(lows[i]),
            "close": float(closes[i]),
        }
        for i in range(take)
    ]

    doc = {
        "schema": SCHEMA,
        "symbol": symbol,
        "bars": n,
        "last_date": str(pd.to_datetime(df["date"]).max().date()),
        "regime": regime,
        "windows": windows,
        "query": {"L": QUERY_BARS, "candles": candles},
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
