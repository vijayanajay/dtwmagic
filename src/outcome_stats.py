"""T+1..T+10 outcome cone + observed MAE/MFE reducers over 0003's analogs (spec 0004).

Consumes the R2 payload (date/distance/score/close/forward) verbatim; pure — no I/O.

# ponytail: ceiling is linear-interpolation quantiles on small n (Free tier K=3);
# upgrade path is a min-sample guard or bootstrap interval at tiering time.
# ponytail: ceiling is unweighted across analogs; upgrade path is
# distance/score-weighted aggregates if near-duplicates dominate.
# ponytail: ceiling is horizon cap T+10 (0003 payload bound); upgrade path is
# T+20 forward paths in 0003 plus this horizons list.
"""
import math

import numpy as np

HORIZONS = range(1, 11)
QUANTILES = (("p10", 0.10), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p90", 0.90))


def summarize_analogs(analogs):
    """Aggregate 0003's analog list into historical outcome stats (Gate 1 2.2-2.3)."""
    if not isinstance(analogs, list) or len(analogs) == 0:
        raise ValueError(
            f"analogs must be a non-empty list (got "
            f"{type(analogs).__name__}, n={len(analogs) if isinstance(analogs, list) else '-'})"
        )

    rows = []
    for i, a in enumerate(analogs):
        if not isinstance(a, dict):
            raise ValueError(f"analog at index {i} must be a dict (got {type(a).__name__})")
        if "close" not in a:
            raise ValueError(f"analog at index {i} missing close (p_tau baseline)")
        p = a["close"]
        if (
            isinstance(p, bool)
            or not isinstance(p, (int, float, np.floating, np.integer))
            or not math.isfinite(p)
            or p <= 0
        ):
            raise ValueError(f"close must be finite and > 0 (got {p!r})")
        fwd = a.get("forward")
        if not isinstance(fwd, list) or len(fwd) < 10:
            got = len(fwd) if isinstance(fwd, list) else type(fwd).__name__
            raise ValueError(f"forward must be a list of >= 10 bars (got {got})")
        rows.append((float(p), fwd))

    n = len(rows)
    out = {
        "n": n,
        "horizons": list(HORIZONS),
        "cone": {},
        "positive_frequency": {},
        "mae": {},
        "mfe": {},
    }
    for h in HORIZONS:
        R, M, F = [], [], []
        for p, fwd in rows:
            R.append(fwd[h - 1]["close"] / p - 1)
            M.append(min(fwd[j]["low"] / p - 1 for j in range(h)))
            F.append(max(fwd[j]["high"] / p - 1 for j in range(h)))
        out["cone"][h] = {
            k: float(np.quantile(R, q, method="linear")) for k, q in QUANTILES
        }
        out["positive_frequency"][h] = sum(1 for v in R if v > 0) / n
        out["mae"][h] = {
            "p80": float(-np.quantile([-v for v in M], 0.80, method="linear"))
        }
        out["mfe"][h] = {"p50": float(np.quantile(F, 0.50, method="linear"))}
    return out
