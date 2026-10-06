"""NSE ind_close_all EOD fetcher -> master ledger -> Parquet store (spec 0002).

Composes spec 0001's build_store; validation is delegated, never duplicated.

# ponytail: ceiling is 404-skip (no trading calendar); upgrade path is a NSE
# holiday calendar plus cron monitoring of master recency.
# ponytail: ceiling is append-only master (no restatement correction); upgrade
# path is nightly full re-key when NSE revises published files.
"""
from __future__ import annotations

import http.cookiejar
import io
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.ohlcv_store import build_store

COLUMNS = ["date", "open", "high", "low", "close", "volume"]
SYMBOL_TO_INDEX = {"^NSEI": "Nifty 50"}
ARCHIVE_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{d}.csv"
WARMUP_URL = "https://nsearchives.nseindia.com/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
MIN_INTERVAL_S = 1.0  # NSE pacing: >= 1 request/second

_opener: urllib.request.OpenerDirector | None = None
_last_request_at = 0.0


def _real_get(url: str) -> bytes | None:
    """Warmed, paced session. bytes on 200, None on 404. Raises on transport errors
    (caller re-runs — natural retry per spec 0002 §3)."""
    global _opener, _last_request_at
    if _opener is None:
        cj = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        _opener.addheaders = [("User-Agent", USER_AGENT),
                              ("Referer", "https://www.nseindia.com/")]
        try:
            _opener.open(WARMUP_URL, timeout=15)  # cookie warmup (NSE is bot-gated)
        except urllib.error.HTTPError:
            # NSE's root answers 404 to script clients but still sets the session
            # cookies; a failed warmup must not kill the fetch.
            pass
    wait = MIN_INTERVAL_S - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()
    try:
        with _opener.open(url, timeout=15) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _d(iso: str) -> date:
    return date.fromisoformat(iso)


def _iso(d: date) -> str:
    return d.isoformat()


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def _map_body(body: bytes, index_name: str) -> pd.DataFrame:
    if body.lstrip()[:5].lower().startswith(b"<html"):
        raise ValueError("html response: bot/error page served with HTTP 200")
    try:
        raw = pd.read_csv(io.BytesIO(body))
    except Exception as exc:  # non-CSV 200 body
        raise ValueError(f"html or non-CSV response: {exc}") from exc
    sub = raw[raw["Index Name"] == index_name]
    if len(sub) == 0:
        raise ValueError(f"row missing: index {index_name!r} not present in response")
    return pd.DataFrame(
        {
            "date": pd.to_datetime(sub["Index Date"], format="%d-%m-%Y")
            .dt.strftime("%Y-%m-%d"),
            "open": sub["Open Index Value"].astype("float64"),
            "high": sub["High Index Value"].astype("float64"),
            "low": sub["Low Index Value"].astype("float64"),
            "close": sub["Closing Index Value"].astype("float64"),
            "volume": sub["Volume"].astype("int64"),
        }
    )[COLUMNS]


def fetch_eod_index(index_name: str, start_date: str, end_date: str,
                    get=_real_get) -> pd.DataFrame:
    """One ind_close_all request per calendar day in [start, end]; None = skip."""
    start, end = _d(start_date), _d(end_date)
    if start > end:
        return _empty()
    frames = []
    day = start
    while day <= end:
        body = get(ARCHIVE_URL.format(d=day.strftime("%d%m%Y")))
        if body is not None:
            frames.append(_map_body(body, index_name))
        day += timedelta(days=1)
    if not frames:
        return _empty()
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values("date", kind="stable").reset_index(drop=True)


def refresh_store(symbol: str, start_date: str, out_dir,
                  get=_real_get, end_date: str | None = None) -> dict:
    """Delta-fetch missing sessions into the master ledger, then full-rewrite the store."""
    if symbol not in SYMBOL_TO_INDEX:
        raise ValueError(f"unknown symbol: {symbol!r} (known: {sorted(SYMBOL_TO_INDEX)})")
    index_name = SYMBOL_TO_INDEX[symbol]
    out_dir = Path(out_dir)
    master = out_dir.parent / "eod" / f"{symbol}.csv"
    end = _d(end_date) if end_date else date.today()

    if master.exists():
        ledger = pd.read_csv(master, dtype={"date": str})
        first_missing = _d(str(ledger["date"].iloc[-1])) + timedelta(days=1)
    else:
        ledger = None
        first_missing = _d(start_date)

    new = fetch_eod_index(index_name, _iso(first_missing), _iso(end), get=get)
    if len(new):
        if ledger is None:
            ledger = new
        else:
            ledger = pd.concat([ledger[COLUMNS], new[COLUMNS]], ignore_index=True)
        master.parent.mkdir(parents=True, exist_ok=True)
        ledger.to_csv(master, index=False)

    # Full rewrite every run (spec 0002 §2.3): Parquet is derived, never merged.
    return build_store(master, symbol, out_dir)
