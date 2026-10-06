"""Z-Euclidean top-K historical analog search over the spec-0001 Parquet store (spec 0003).

# ponytail: ceiling is live single-symbol compute; upgrade path is nightly
# precompute + static JSON (BRD 4.2) when the 2,000-symbol batch arrives.
# ponytail: ceiling is close-channel Euclidean only; upgrade path is Sakoe-Chiba
# DTW refinement on top-50 candidates (BRD 4.3).
# ponytail: ceiling is no result caching; upgrade path is memoizing per (symbol, L)
# when a screener replays queries.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

EPS = 1e-8
MIN_L = 5
MAX_L = 60
FORWARD = 10


def search_analogs(symbol, L, K, parquet_dir):
    """Return up to K closest historical analogs for the store's last L closes.

    Each analog carries distance, score = 100/(1+distance), and its raw forward
    OHLC path T+1..T+10 (Gate 1 2.1-2.4).
    """
    if isinstance(L, bool) or not isinstance(L, (int, np.integer)) or not (
        MIN_L <= L <= MAX_L
    ):
        raise ValueError(f"window must be an int in {MIN_L}..{MAX_L} (got {L!r})")
    if isinstance(K, bool) or not isinstance(K, (int, np.integer)) or K < 1:
        raise ValueError(f"K must be an int >= 1 (got {K!r})")

    path = Path(parquet_dir) / f"{symbol}.parquet"
    if not path.exists():
        raise ValueError(f"store not found for symbol {symbol!r}: {path}")

    df = pd.read_parquet(path)
    closes = df["close"].to_numpy("float64")
    n = len(closes)
    s_max = n - 2 * L - 10  # Gate 1 2.3: window + forward path disjoint from query
    if s_max < 0:
        raise ValueError(f"bars: store has {n} rows; window {L} needs >= {2 * L + 10}")

    # z-normalize the query (the store's last L closes)
    q0 = n - L
    q = closes[q0 : q0 + L]
    qr = q / q[0] - 1.0
    qmu = qr.mean()
    qz = (qr - qmu) / (np.sqrt(((qr - qmu) ** 2).mean()) + EPS)

    # z-normalize every eligible candidate window (vectorized)
    wins = sliding_window_view(closes, L)[: s_max + 1]
    r = wins / wins[:, :1] - 1.0
    mu = r.mean(axis=1, keepdims=True)
    sigma = np.sqrt(((r - mu) ** 2).mean(axis=1, keepdims=True))
    z = (r - mu) / (sigma + EPS)
    dist = np.sqrt(((z - qz) ** 2).sum(axis=1))

    dates = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").to_numpy()
    cand = [(float(dist[i]), str(dates[i + L - 1]), int(i)) for i in range(s_max + 1)]
    cand.sort(key=lambda t: (t[0], t[1]))  # distance asc, exact ties -> earlier date

    out = []
    for d, date, s in cand[:K]:
        tau = s + L - 1
        fwd = df.iloc[tau + 1 : tau + 1 + FORWARD]
        out.append(
            {
                "date": date,
                "distance": d,
                "score": 100.0 / (1.0 + d),
                "forward": [
                    {
                        "date": str(dates[tau + 1 + k]),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                    }
                    for k, (_, row) in enumerate(fwd.iterrows())
                ],
            }
        )
    return out
