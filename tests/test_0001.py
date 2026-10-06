"""Frozen Gate 2 eval for spec 0001 (specs/tests/0001-ohlcv-parquet-store.md).

IMMUTABLE: fix broken code, never these tests.
Runner: python -m pytest tests/test_0001.py  (offline)
"""
from __future__ import annotations

import hashlib
import socket as _socket
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.ohlcv_store import build_store

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "nifty50_daily_ohlcv.csv"
FIXTURE_SHA256 = "25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e"
COLUMNS = ["date", "open", "high", "low", "close", "volume"]
SYMBOL = "^NSEI"
HEADER = "date,open,high,low,close,volume"


@pytest.fixture(autouse=True)
def _fixture_integrity():
    # Eval convention: fixture drift invalidates this eval.
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA256, (
        "fixture sha256 drifted — this frozen eval is invalid"
    )


def _iso(v):
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = out["date"].map(_iso)
    return out.reset_index(drop=True)


def _write(tmp_path, rows: str, header: str = HEADER, name: str = "case.csv") -> Path:
    p = tmp_path / name
    p.write_text(header + "\n" + rows, encoding="utf-8")
    return p


def _rejects(csv_path, tmp_path, keyword: str) -> None:
    with pytest.raises(ValueError) as exc:
        build_store(csv_path, SYMBOL, tmp_path / "out")
    msg = str(exc.value)
    assert msg.strip(), "ValueError message must be non-empty"
    assert keyword in msg.lower(), f"expected {keyword!r} in message {msg!r}"


# ---------------------------------------------------------------- happy path

def test_t001_manifest_contract(tmp_path):
    m = build_store(FIXTURE, SYMBOL, tmp_path / "store")
    assert isinstance(m, dict)
    assert set(m.keys()) == {"symbol", "rows", "first_date", "last_date", "parquet_path"}
    assert len(m) == 5
    assert m["symbol"] == SYMBOL
    assert isinstance(m["rows"], int) and m["rows"] == 4673
    assert m["first_date"] == "2007-09-17"
    assert m["last_date"] == "2026-10-05"
    assert m["parquet_path"] == str(tmp_path / "store" / "^NSEI.parquet")


def test_t002_output_location_and_creation(tmp_path):
    out_dir = tmp_path / "does" / "not" / "exist"
    assert not out_dir.exists()
    m = build_store(FIXTURE, SYMBOL, out_dir)
    assert out_dir.is_dir()
    path = out_dir / "^NSEI.parquet"
    assert path.is_file()
    assert m["parquet_path"] == str(path)
    assert path.name == "^NSEI.parquet"  # symbol used verbatim


def test_t003_schema_types_on_readback(tmp_path):
    m = build_store(FIXTURE, SYMBOL, tmp_path / "store")
    got = pd.read_parquet(m["parquet_path"])
    assert list(got.columns) == COLUMNS
    dtyp = pq.read_schema(m["parquet_path"]).field("date").type
    assert pa.types.is_date(dtyp) or pa.types.is_timestamp(dtyp), f"date field is {dtyp}"
    for c in ["open", "high", "low", "close"]:
        assert got[c].dtype == "float64", (c, got[c].dtype)
    assert got["volume"].dtype == "int64", got["volume"].dtype
    assert len(got) == 4673
    dts = pd.to_datetime(got["date"])
    assert dts.is_unique and dts.is_monotonic_increasing, "dates must be strictly ascending"
    assert got.isna().sum().sum() == 0, "no nulls allowed"


def test_t004_content_equality_pinned_rows(tmp_path):
    m = build_store(FIXTURE, SYMBOL, tmp_path / "store")
    got = _norm(pd.read_parquet(m["parquet_path"]))
    want = _norm(pd.read_csv(FIXTURE))
    pd.testing.assert_frame_equal(got, want, check_dtype=False)
    assert list(got.columns) == COLUMNS
    assert got.iloc[0].tolist() == ["2007-09-17", 4518.45, 4549.05, 4482.85, 4494.65, 0]
    sat = got.loc[got["date"] == "2025-02-01"].iloc[0].tolist()
    assert sat == ["2025-02-01", 23528.6, 23632.45, 23318.3, 23482.15, 281000]
    assert got.iloc[-1].tolist() == ["2026-10-05", 22532.4, 22621.8, 22397.1, 22555.75, 436700]


def test_t005_two_decimal_preservation(tmp_path):
    m = build_store(FIXTURE, SYMBOL, tmp_path / "store")
    got = _norm(pd.read_parquet(m["parquet_path"]))
    v = got.loc[got["date"] == "2007-09-17", "open"].iloc[0]
    assert v == 4518.45, f"expected exact 4518.45, got {v!r}"


def test_t006_idempotent_overwrite(tmp_path):
    out_dir = tmp_path / "store"
    build_store(FIXTURE, SYMBOL, out_dir)
    first = _norm(pd.read_parquet(out_dir / "^NSEI.parquet"))
    m2 = build_store(FIXTURE, SYMBOL, out_dir)
    second = _norm(pd.read_parquet(m2["parquet_path"]))
    pd.testing.assert_frame_equal(first, second, check_dtype=False)


def test_t007_quirk_acceptance(tmp_path):
    m = build_store(FIXTURE, SYMBOL, tmp_path / "store")
    got = _norm(pd.read_parquet(m["parquet_path"]))
    assert "2025-02-01" in set(got["date"]), "Saturday Budget session must be kept"
    assert int((got["volume"] == 0).sum()) == 1333, "zero-volume rows must be kept"
    assert got["volume"].isna().sum() == 0, "zero volume must never become null"


def test_t008_hermetic_no_network(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("network access attempted")

    monkeypatch.setattr(_socket, "socket", boom)
    monkeypatch.setattr(_socket, "create_connection", boom)
    m = build_store(FIXTURE, SYMBOL, tmp_path / "store")
    assert m["rows"] == 4673


def test_t009_performance_sanity(tmp_path):
    t0 = time.perf_counter()
    build_store(FIXTURE, SYMBOL, tmp_path / "store")
    dt = time.perf_counter() - t0
    assert dt < 5.0, f"build_store took {dt:.2f}s (target ~1s, bound 5s)"


# ------------------------------------------------------------- rejections

def test_t010_missing_column(tmp_path):
    p = _write(
        tmp_path,
        "2024-01-01,100.0,105.0,99.0,104.0\n2024-01-02,104.0,106.0,103.0,105.0\n",
        header="date,open,high,low,close",
        name="missing_volume.csv",
    )
    _rejects(p, tmp_path, "column")


def test_t011_extra_column(tmp_path):
    p = _write(
        tmp_path,
        "2024-01-01,100.0,105.0,99.0,104.0,1000,1.0\n2024-01-02,104.0,106.0,103.0,105.0,1200,1.0\n",
        header="date,open,high,low,close,volume,adj_close",
        name="extra_col.csv",
    )
    _rejects(p, tmp_path, "column")


def test_t012_wrong_case_column_header(tmp_path):
    p = _write(
        tmp_path,
        "2024-01-01,100.0,105.0,99.0,104.0,1000\n",
        header="Date,open,high,low,close,volume",
        name="wrong_case.csv",
    )
    _rejects(p, tmp_path, "column")


def test_t013_duplicate_dates(tmp_path):
    p = _write(
        tmp_path,
        "2024-01-01,100.0,105.0,99.0,104.0,1000\n2024-01-01,104.0,106.0,103.0,105.0,1200\n",
        name="dup.csv",
    )
    _rejects(p, tmp_path, "duplicate")


def test_t014_null_value(tmp_path):
    p = _write(
        tmp_path,
        "2024-01-01,100.0,105.0,99.0,,1000\n2024-01-02,104.0,106.0,103.0,105.0,1200\n",
        name="null.csv",
    )
    _rejects(p, tmp_path, "null")


def test_t015_non_positive_price(tmp_path):
    p1 = _write(tmp_path, "2024-01-01,100.0,105.0,99.0,0.0,1000\n", name="zero_close.csv")
    _rejects(p1, tmp_path, "price")
    p2 = _write(tmp_path, "2024-01-01,-1.0,105.0,99.0,104.0,1000\n", name="neg_open.csv")
    _rejects(p2, tmp_path, "price")


def test_t016_high_below_body(tmp_path):
    p = _write(tmp_path, "2024-01-03,100.0,102.0,99.0,104.0,1000\n", name="high.csv")
    _rejects(p, tmp_path, "high")


def test_t017_low_above_body(tmp_path):
    p = _write(tmp_path, "2024-01-04,100.0,101.0,98.0,96.0,1000\n", name="low.csv")
    _rejects(p, tmp_path, "low")


def test_t018_negative_volume(tmp_path):
    p = _write(tmp_path, "2024-01-01,100.0,105.0,99.0,104.0,-1\n", name="neg_vol.csv")
    _rejects(p, tmp_path, "volume")


def test_t019_fractional_volume(tmp_path):
    p = _write(tmp_path, "2024-01-01,100.0,105.0,99.0,104.0,100.5\n", name="frac_vol.csv")
    _rejects(p, tmp_path, "volume")


def test_t020_empty_input(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text(HEADER + "\n", encoding="utf-8")
    _rejects(p, tmp_path, "empty")


def test_t021_unparseable_date(tmp_path):
    p1 = _write(tmp_path, "not-a-date,100.0,105.0,99.0,104.0,1000\n", name="bad_date1.csv")
    _rejects(p1, tmp_path, "date")
    p2 = _write(tmp_path, "2024-13-40,100.0,105.0,99.0,104.0,1000\n", name="bad_date2.csv")
    _rejects(p2, tmp_path, "date")


# ---------------------------------------------------------- normalization

def test_t022_unsorted_input_sorted(tmp_path):
    p = _write(
        tmp_path,
        "2024-01-02,104.0,106.0,103.0,105.0,1200\n2024-01-01,100.0,105.0,99.0,104.0,1000\n",
        name="descending.csv",
    )
    m = build_store(p, SYMBOL, tmp_path / "store")
    assert m["first_date"] == "2024-01-01"
    assert m["last_date"] == "2024-01-02"
    got = _norm(pd.read_parquet(m["parquet_path"]))
    assert list(got["date"]) == ["2024-01-01", "2024-01-02"]


def test_t023_boundary_acceptance(tmp_path):
    p = _write(tmp_path, "2024-01-05,100.0,100.0,100.0,100.0,0\n", name="boundary.csv")
    m = build_store(p, SYMBOL, tmp_path / "store")
    got = _norm(pd.read_parquet(m["parquet_path"]))
    assert m["rows"] == 1
    assert int(got["volume"].iloc[0]) == 0
    assert list(got["date"]) == ["2024-01-05"]
