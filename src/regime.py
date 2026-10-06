"""Regime conditioning filter for historical analog search (spec 0005, BRD F-02).

Hard candidate-pool filter per BRD §5.3: only windows whose regime cell equals the
query session's cell are eligible; score/distance stay 0003's pure values.

# ponytail: ceiling is per-call regime recomputation + full-pool filtering;
# upgrade path is a precomputed regime column / nightly batch (BRD 4.2) when the
# 2,000-stock screener lands.
# ponytail: ceiling is query regime = store's last session only; upgrade path is
# Pro custom regime filters (BRD 2.2).
# ponytail: ceiling is fixed 252-day rank window and fixed 3x3 grid; upgrade path
# is configurable percentile lookback if users demand regime sensitivity.
# ponytail: ceiling is two Parquet reads per call (0003's + regime's); upgrade
# path is a shared-dataframe seam, which would touch 0003's frozen signature.
# ponytail: ceiling is filter-after-full-ranking; upgrade path is a
# regime-indexed candidate structure if the batch pipeline shows real cost.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.pattern_search import search_analogs


def _classify(df):
    """Literal Gate 1 2.2 classification -> (cells, p252) for every session.

    Cells are "trend-volatility" strings, None while the rolling-252 rank is
    undefined (first 251 sessions). Probe-pinned definitions.
    """
    h = df["high"].to_numpy("float64")
    l = df["low"].to_numpy("float64")
    c = df["close"].to_numpy("float64")
    cs = pd.Series(c)
    e50 = cs.ewm(span=50, adjust=True).mean().to_numpy()
    e200 = cs.ewm(span=200, adjust=True).mean().to_numpy()
    trend = np.where((c > e50) & (e50 > e200), "bullish",
             np.where((c < e50) & (e50 < e200), "bearish", "neutral"))
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    tr[0] = h[0] - l[0]
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    p = pd.Series(atr / c).rolling(252).rank(pct=True).to_numpy()
    vol = np.where(np.isnan(p), None,
                   np.where(p <= 1 / 3, "low", np.where(p <= 2 / 3, "normal", "high")))
    cells = [None if v is None else f"{t}-{v}" for t, v in zip(trend, vol)]
    return cells, p


def search_analogs_regime(symbol, L, K, parquet_dir):
    """Return {"regime": ..., "analogs": [...]} for the store's last L closes.

    0003's search hard-filtered to the query session's regime cell (BRD 5.3).
    Strict: the in-regime pool may be < K or empty (analogs then []); regime
    never enters distance/score; validation order store -> window -> K -> bars
    -> regime (0003's four checks pass through verbatim).
    """
    path = Path(parquet_dir) / f"{symbol}.parquet"
    if not path.exists():
        raise ValueError(f"store not found for symbol {symbol!r}: {path}")
    # window & K mirror 0003's frozen rules/messages verbatim so the single pool
    # call below can carry `bars` — one computation per call (spec 0006 Fix B),
    # frozen validation order store -> window -> K -> bars -> regime preserved.
    if isinstance(L, bool) or not isinstance(L, (int, np.integer)) or not (5 <= L <= 60):
        raise ValueError(f"window must be an int in 5..60 (got {L!r})")
    if isinstance(K, bool) or not isinstance(K, (int, np.integer)) or K < 1:
        raise ValueError(f"K must be an int >= 1 (got {K!r})")
    df = pd.read_parquet(path)
    n = len(df)
    full = search_analogs(symbol, L, n, parquet_dir)  # raises `bars`; the ONE computation
    if n - 1 < 251:
        raise ValueError(
            f"regime: query session not classifiable; store has {n} rows, "
            f"needs >= 252 for the rolling-252 rank window"
        )
    cells, p = _classify(df)
    qcell = cells[-1]
    trend, volatility = qcell.split("-", 1)
    dates = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").to_numpy()
    i_of = {str(d): i for i, d in enumerate(dates)}
    kept = [
        it for it in full
        if cells[i_of[it["date"]]] is not None and cells[i_of[it["date"]]] == qcell
    ]
    return {
        "regime": {"trend": trend, "volatility": volatility,
                   "cell": qcell, "p252": float(p[-1])},
        "analogs": kept[:K],  # filter-then-cap (frozen: K caps AFTER the filter)
    }
