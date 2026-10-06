"""Frozen Gate 2 eval for spec 0002 (specs/tests/0002-eod-data-fetcher.md).

IMMUTABLE (see revision log R1): fix broken code, never these tests.
Runner: python -m pytest tests/test_0002.py  (offline — every test injects `get`)
"""
from __future__ import annotations

import hashlib
import re
import socket as _socket
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.eod_fetch import fetch_eod_index, refresh_store

FIXDIR = Path(__file__).resolve().parent / "fixtures"
PAYLOAD_PATH = FIXDIR / "ind_close_all_20261005.csv"
STORE0_PATH = FIXDIR / "nifty50_daily_ohlcv.csv"
SHA_PAYLOAD = "f0b8004e9bc79b11cff3c939cb42cdeb4a31b71ebd03942b98b57f44fa3bc9ba"
SHA_STORE0 = "25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e"
COLUMNS = ["date", "open", "high", "low", "close", "volume"]
PAYLOAD = PAYLOAD_PATH.read_bytes()

NSE_HEADER = (
    "Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,"
    "Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield"
)
EXACT_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_05102026.csv"


@pytest.fixture(autouse=True)
def _fixture_integrity():
    # Eval convention: fixture drift invalidates this eval.
    assert hashlib.sha256(PAYLOAD_PATH.read_bytes()).hexdigest() == SHA_PAYLOAD
    assert hashlib.sha256(STORE0_PATH.read_bytes()).hexdigest() == SHA_STORE0


class Recorder:
    """Stub `get`: bytes per DDMMYYYY route, None otherwise; records every call."""

    def __init__(self, routes: dict[str, bytes | None] | None = None):
        self.routes = routes or {}
        self.calls: list[str] = []

    def __call__(self, url: str):
        self.calls.append(url)
        m = re.search(r"ind_close_all_(\d{8})\.csv", url)
        return self.routes.get(m.group(1)) if m else None


def nifty_row(dmy: str, o: float, h: float, lo: float, c: float, v: int) -> str:
    return f"Nifty 50,{dmy},{o},{h},{lo},{c},1.0,.1,{v},10.0,20.0,3.0,1.0"


def index_csv(rows: list[str]) -> bytes:
    return (NSE_HEADER + "\n" + "\n".join(rows) + "\n").encode("utf-8")


def iso_to_dmy(iso: str) -> str:
    d = date.fromisoformat(iso)
    return d.strftime("%d%m%Y")


# ------------------------------------------------- fetch_eod_index

def test_t001_canonical_mapping():
    rec = Recorder({"05102026": PAYLOAD})
    df = fetch_eod_index("Nifty 50", "2026-10-05", "2026-10-05", get=rec)
    assert list(df.columns) == COLUMNS
    assert len(df) == 1, "166-index file must be filtered to a single row"
    assert df["date"].iloc[0] == "2026-10-05"  # DD-MM-YYYY -> ISO
    assert df["open"].iloc[0] == 22532.4
    assert df["high"].iloc[0] == 22621.8
    assert df["low"].iloc[0] == 22397.1
    assert df["close"].iloc[0] == 22555.75
    assert df["volume"].iloc[0] == 412554239
    assert df["volume"].dtype == "int64", df["volume"].dtype
    for c in ["open", "high", "low", "close"]:
        assert df[c].dtype == "float64", (c, df[c].dtype)
    dts = pd.to_datetime(df["date"])
    assert dts.is_unique and dts.is_monotonic_increasing


def test_t002_exact_archive_url():
    rec = Recorder({"05102026": PAYLOAD})
    fetch_eod_index("Nifty 50", "2026-10-05", "2026-10-05", get=rec)
    assert rec.calls == [EXACT_URL], rec.calls


def test_t003_multi_day_iteration_with_gaps():
    rec = Recorder({
        "01102026": index_csv([nifty_row("01-10-2026", 100, 101, 99, 100.5, 1111)]),
        "02102026": index_csv([nifty_row("02-10-2026", 200, 202, 199, 201.5, 2222)]),
        "05102026": PAYLOAD,
        "03102026": None,  # Saturday
        "04102026": None,  # Sunday
    })
    df = fetch_eod_index("Nifty 50", "2026-10-01", "2026-10-05", get=rec)
    assert len(rec.calls) == 5, "one calendar-day request per day, no trading calendar"
    assert len(df) == 3
    assert list(df["date"]) == ["2026-10-01", "2026-10-02", "2026-10-05"]
    assert df["open"].tolist() == [100.0, 200.0, 22532.4]  # values from bodies
    assert df["close"].tolist() == [100.5, 201.5, 22555.75]


def test_t004_empty_range_edge():
    rec = Recorder()
    df = fetch_eod_index("Nifty 50", "2026-10-06", "2026-10-05", get=rec)
    assert list(df.columns) == COLUMNS
    assert len(df) == 0
    assert rec.calls == [], "empty range must issue no requests"


def test_t005_missing_index_row():
    body = index_csv(["Other Index,05-10-2026,1,2,0.5,1.5,0.1,.1,10,1.0,1.0,1.0,1.0"])
    rec = Recorder({"05102026": body})
    with pytest.raises(ValueError) as exc:
        fetch_eod_index("Nifty 50", "2026-10-05", "2026-10-05", get=rec)
    assert str(exc.value).strip()
    assert "row" in str(exc.value).lower()


def test_t006_html_body_with_200():
    rec = Recorder({"05102026": b"<html><body>Access denied</body></html>"})
    with pytest.raises(ValueError) as exc:
        fetch_eod_index("Nifty 50", "2026-10-05", "2026-10-05", get=rec)
    assert str(exc.value).strip()
    assert "html" in str(exc.value).lower()


# ------------------------------------------------- refresh_store

def test_t007_cold_start_end_to_end(tmp_path):
    out_dir = tmp_path / "store"
    rec = Recorder({"05102026": PAYLOAD})
    m = refresh_store("^NSEI", "2026-10-05", out_dir, get=rec, end_date="2026-10-05")
    assert isinstance(m, dict)
    assert set(m.keys()) == {"symbol", "rows", "first_date", "last_date", "parquet_path"}
    assert len(m) == 5
    assert m["symbol"] == "^NSEI"
    assert isinstance(m["rows"], int) and m["rows"] == 1
    assert m["first_date"] == m["last_date"] == "2026-10-05"
    assert m["parquet_path"] == str(out_dir / "^NSEI.parquet")
    assert (out_dir / "^NSEI.parquet").is_file()
    # frozen master path rule: {out_dir.parent}/eod/{symbol}.csv
    master = tmp_path / "eod" / "^NSEI.csv"
    assert master.is_file(), f"master missing at {master}"
    text = master.read_text(encoding="utf-8")
    assert text.splitlines()[0] == ",".join(COLUMNS)
    assert "2026-10-05" in text and "22555.75" in text


def test_t008_parquet_content_matches_body(tmp_path):
    out_dir = tmp_path / "store"
    rec = Recorder({"05102026": PAYLOAD})
    m = refresh_store("^NSEI", "2026-10-05", out_dir, get=rec, end_date="2026-10-05")
    got = pd.read_parquet(m["parquet_path"])
    dtyp = pq.read_schema(m["parquet_path"]).field("date").type
    assert pa.types.is_date(dtyp) or pa.types.is_timestamp(dtyp), f"date field {dtyp}"
    assert list(got.columns) == COLUMNS
    for c in ["open", "high", "low", "close"]:
        assert got[c].dtype == "float64", (c, got[c].dtype)
    assert got["volume"].dtype == "int64", got["volume"].dtype
    assert len(got) == 1
    row = got.iloc[0]
    assert str(row["date"])[:10] == "2026-10-05"
    assert (row["open"], row["high"], row["low"], row["close"]) == (
        22532.4, 22621.8, 22397.1, 22555.75)
    assert row["volume"] == 412554239


def test_t009_unknown_symbol_rejected_before_request(tmp_path):
    rec = Recorder()
    with pytest.raises(ValueError) as exc:
        refresh_store("XXNOPE", "2026-10-05", tmp_path / "s", get=rec, end_date="2026-10-05")
    assert str(exc.value).strip()
    assert "symbol" in str(exc.value).lower()
    assert rec.calls == [], "no request may fire for an unknown symbol"


def test_t010_nightly_delta_two_requests_untouched_store(tmp_path):
    out_dir = tmp_path / "store"
    seed = Recorder({"05102026": PAYLOAD})
    m0 = refresh_store("^NSEI", "2026-10-05", out_dir, get=seed, end_date="2026-10-05")
    before = pd.read_parquet(m0["parquet_path"])
    rec = Recorder({})  # Oct 6 and Oct 7 both 404 -> None
    m1 = refresh_store("^NSEI", "2026-10-05", out_dir, get=rec, end_date="2026-10-07")
    assert len(rec.calls) == 2, rec.calls
    assert rec.calls == [
        "https://nsearchives.nseindia.com/content/indices/ind_close_all_06102026.csv",
        "https://nsearchives.nseindia.com/content/indices/ind_close_all_07102026.csv",
    ], "history must never be re-fetched"
    assert m1["first_date"] == "2026-10-05"
    assert m1["rows"] == 1
    after = pd.read_parquet(m1["parquet_path"])
    pd.testing.assert_frame_equal(before, after)


def _seed_master_0930(tmp_path, out_dir):
    seed = Recorder({"30092026": index_csv([nifty_row("30-09-2026", 10, 11, 9, 10.5, 100)])})
    refresh_store("^NSEI", "2026-09-30", out_dir, get=seed, end_date="2026-09-30")
    return tmp_path / "eod" / "^NSEI.csv"


def test_t011_catchup_append_only(tmp_path):
    out_dir = tmp_path / "store"
    master = _seed_master_0930(tmp_path, out_dir)
    assert len(pd.read_csv(master)) == 1
    prior_row = pd.read_csv(master).iloc[0].to_dict()
    rec = Recorder({
        "01102026": index_csv([nifty_row("01-10-2026", 100, 101, 99, 100.5, 1111)]),
        "02102026": index_csv([nifty_row("02-10-2026", 200, 202, 199, 201.5, 2222)]),
        "05102026": PAYLOAD,
        # 03102026 / 04102026 absent -> weekend None
    })
    m = refresh_store("^NSEI", "2026-09-30", out_dir, get=rec, end_date="2026-10-05")
    assert len(rec.calls) == 5, "Oct 1-5 calendar days"
    led = pd.read_csv(master)
    assert len(led) == 4, "1 seed + 3 payloads (R1); weekend = None"
    dts = pd.to_datetime(led["date"])
    assert dts.is_unique and dts.is_monotonic_increasing
    seed_now = led[led["date"] == "2026-09-30"].iloc[0].to_dict()
    for k in COLUMNS:
        assert seed_now[k] == prior_row[k], f"seed row changed at {k}"
    parquet = pd.read_parquet(m["parquet_path"])
    assert len(parquet) == 4
    assert m["rows"] == 4


def test_t012_idempotent_rerun_zero_requests(tmp_path):
    out_dir = tmp_path / "store"
    master = _seed_master_0930(tmp_path, out_dir)
    first_rec = Recorder({
        "01102026": index_csv([nifty_row("01-10-2026", 100, 101, 99, 100.5, 1111)]),
        "02102026": index_csv([nifty_row("02-10-2026", 200, 202, 199, 201.5, 2222)]),
        "05102026": PAYLOAD,
    })
    m1 = refresh_store("^NSEI", "2026-09-30", out_dir, get=first_rec, end_date="2026-10-05")
    before_master = master.read_bytes()
    before = pd.read_parquet(m1["parquet_path"])
    rerun = Recorder({})
    m2 = refresh_store("^NSEI", "2026-09-30", out_dir, get=rerun, end_date="2026-10-05")
    assert rerun.calls == [], f"expected 0 requests, got {rerun.calls}"
    assert master.read_bytes() == before_master
    assert len(pd.read_csv(master)) == 4
    after = pd.read_parquet(m2["parquet_path"])
    pd.testing.assert_frame_equal(before, after)


def test_t013_validation_delegated_to_0001(tmp_path):
    master = tmp_path / "eod" / "^NSEI.csv"
    master.parent.mkdir(parents=True)
    master.write_text(
        "date,open,high,low,close,volume\n2026-09-30,100.0,101.0,99.0,0.0,1000\n",
        encoding="utf-8",
    )
    rec = Recorder({})
    with pytest.raises(ValueError) as exc:
        refresh_store("^NSEI", "2026-09-30", tmp_path / "store", get=rec, end_date="2026-09-30")
    assert str(exc.value).strip()
    assert "price" in str(exc.value).lower()


def test_t014_hermetic_no_network(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("network access attempted")

    monkeypatch.setattr(_socket, "socket", boom)
    monkeypatch.setattr(_socket, "create_connection", boom)
    rec = Recorder({"05102026": PAYLOAD})
    m = refresh_store("^NSEI", "2026-10-05", tmp_path / "store", get=rec, end_date="2026-10-05")
    assert m["rows"] == 1


def test_t015_performance_sanity(tmp_path):
    out_dir = tmp_path / "store"
    seed = Recorder({"05102026": PAYLOAD})
    refresh_store("^NSEI", "2026-10-05", out_dir, get=seed, end_date="2026-10-05")
    rec = Recorder({})  # nightly path: 2 requests (both None) + full rewrite
    t0 = time.perf_counter()
    refresh_store("^NSEI", "2026-10-05", out_dir, get=rec, end_date="2026-10-07")
    dt = time.perf_counter() - t0
    assert len(rec.calls) == 2
    assert dt < 5.0, f"nightly path took {dt:.2f}s (target ~2s, bound 5s)"
