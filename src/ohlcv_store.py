"""OHLCV CSV -> validated Parquet store (spec 0001).

# ponytail: ceiling is full-file rewrite per symbol; upgrade path is
# incremental append when the 2,000-symbol batch becomes real.
# ponytail: ceiling is fixture-pre-adjusted; upgrade path is fetcher-applied
# split/bonus adjustment when equities land in spec 0002.
"""
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["date", "open", "high", "low", "close", "volume"]
PRICES = ["open", "high", "low", "close"]


def build_store(csv_path, symbol, out_dir):
    """Validate OHLCV CSV and write {out_dir}/{symbol}.parquet; return manifest dict."""
    df = pd.read_csv(csv_path)

    if set(df.columns) != set(COLUMNS):
        missing = sorted(set(COLUMNS) - set(df.columns))
        extra = sorted(set(df.columns) - set(COLUMNS))
        raise ValueError(
            f"column mismatch: missing={missing} extra={extra} "
            f"(required exactly: {','.join(COLUMNS)})"
        )
    df = df[COLUMNS]

    if len(df) == 0:
        raise ValueError("empty input: CSV has header but no data rows")

    if df.isna().any().any():
        bad = [c for c in COLUMNS if df[c].isna().any()]
        raise ValueError(f"null value(s) present in column(s): {', '.join(bad)}")

    parsed = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"unparseable date value(s): {df.loc[parsed.isna(), 'date'].tolist()}")

    if parsed.duplicated().any():
        dups = sorted(set(df.loc[parsed.duplicated(), "date"]))
        raise ValueError(f"duplicate date(s) found: {dups}")

    vol = df["volume"]
    if not pd.api.types.is_integer_dtype(vol):
        if not np.all(np.mod(vol.to_numpy(dtype="float64"), 1) == 0):
            raise ValueError("volume must be integer values (fractional volume found)")
    if (vol < 0).any():
        raise ValueError("volume must be >= 0 (negative volume found)")

    prices = df[PRICES].astype("float64")
    if (prices <= 0).any().any():
        raise ValueError("price must be > 0 for open/high/low/close")
    if (prices["high"] < prices[["open", "close"]].max(axis=1)).any():
        raise ValueError("high must be >= max(open, close)")
    if (prices["low"] > prices[["open", "close"]].min(axis=1)).any():
        raise ValueError("low must be <= min(open, close)")

    df = df.assign(_d=parsed).sort_values("_d", kind="stable").reset_index(drop=True)
    out = pd.DataFrame(
        {
            "date": df["_d"].dt.date,
            "open": df["open"].astype("float64"),
            "high": df["high"].astype("float64"),
            "low": df["low"].astype("float64"),
            "close": df["close"].astype("float64"),
            "volume": df["volume"].astype("int64"),
        }
    )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{symbol}.parquet"
    out.to_parquet(path, index=False)

    return {
        "symbol": symbol,
        "rows": int(len(out)),
        "first_date": out["date"].iloc[0].isoformat(),
        "last_date": out["date"].iloc[-1].isoformat(),
        "parquet_path": str(path),
    }
