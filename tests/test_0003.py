"""Frozen eval for spec 0003 — Gate 2: specs/tests/0003-pattern-search-core.md.

IMMUTABLE: T-001..T-019 are transcribed from the frozen test spec (incl. R1).
Never edit to make failing code pass; fix src/pattern_search.py instead.
"""
import datetime
import hashlib
import socket
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.ohlcv_store import build_store
from src.pattern_search import search_analogs

FIXTURE = Path("tests/fixtures/nifty50_daily_ohlcv.csv")
FIXTURE_SHA256 = "25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e"
EPS = 1e-8


@pytest.fixture(autouse=True)
def fixture_hash_guard():
    """Gate 2 §0: fixture drift invalidates the eval."""
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert digest == FIXTURE_SHA256, f"fixture drift: {digest}"
    yield


@pytest.fixture(scope="session")
def store_dir(tmp_path_factory):
    """Gate 2 §0 freeze 4: main store built once per session via 0001's seam."""
    out = tmp_path_factory.mktemp("store0003")
    build_store(FIXTURE, "^NSEI", out)
    return out


def read_store(store_dir, symbol="^NSEI"):
    return pd.read_parquet(Path(store_dir) / f"{symbol}.parquet")


def iso_dates(df):
    return pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").tolist()


def ref_search(df, L, K):
    """Literal reference (Gate 2 §0 freeze 3): read-back closes, ddof=0, eps=1e-8."""
    closes = df["close"].to_numpy("float64")
    dates = iso_dates(df)
    n = len(closes)
    q0 = n - L

    def z(w):
        r = w / w[0] - 1.0
        mu = r.mean()
        sigma = np.sqrt(((r - mu) ** 2).mean())
        return (r - mu) / (sigma + EPS)

    zq = z(closes[q0 : q0 + L])
    out = []
    for s in range(0, n - 2 * L - 10 + 1):
        d = float(np.sqrt(((z(closes[s : s + L]) - zq) ** 2).sum()))
        out.append((d, dates[s + L - 1], s))
    out.sort(key=lambda t: (t[0], t[1]))
    return out[:K], n - 2 * L - 9


def make_store(tmp_path, closes, symbol="TINY"):
    """In-test tiny store: constant open=high=low=close (valid per 0001 rules)."""
    dates = [
        (datetime.date(2024, 1, 1) + datetime.timedelta(days=i)).isoformat()
        for i in range(len(closes))
    ]
    lines = ["date,open,high,low,close,volume"]
    lines += [f"{d},{v},{v},{v},{v},0" for d, v in zip(dates, closes)]
    csv = tmp_path / "in.csv"
    csv.write_text("\n".join(lines) + "\n")
    out = tmp_path / "store"
    build_store(csv, symbol, out)
    return out


# --- Section 1: happy path (fixture store, L=10, K=10) ---


def test_t001_payload_contract(store_dir):
    res = search_analogs("^NSEI", 10, 10, store_dir)
    assert isinstance(res, list)
    assert len(res) <= 10
    prev = float("-inf")
    for item in res:
        assert isinstance(item, dict)
        assert set(item) == {"date", "distance", "score", "close", "forward"}  # R2
        datetime.date.fromisoformat(item["date"])
        assert isinstance(item["distance"], float)
        assert isinstance(item["score"], float)
        assert isinstance(item["close"], float)
        fwd = item["forward"]
        assert isinstance(fwd, list) and len(fwd) == 10
        fwd_dates = []
        for row in fwd:
            assert set(row) == {"date", "open", "high", "low", "close"}
            datetime.date.fromisoformat(row["date"])
            for key in ("open", "high", "low", "close"):
                assert isinstance(row[key], float)
            fwd_dates.append(row["date"])
        assert fwd_dates == sorted(fwd_dates)
        assert len(set(fwd_dates)) == 10
        assert item["distance"] >= prev
        prev = item["distance"]


def test_t002_score_identity(store_dir):
    for item in search_analogs("^NSEI", 10, 10, store_dir):
        assert item["score"] == pytest.approx(
            100.0 / (1.0 + item["distance"]), rel=1e-12
        )


def test_t003_eligibility_rule(store_dir):
    df = read_store(store_dir)
    L = 10
    n = len(df)
    q0 = n - L
    dates = iso_dates(df)
    index_of = {d: i for i, d in enumerate(dates)}
    _, pool = ref_search(df, L, 10)
    assert pool == n - 2 * L - 9 == 4644
    res = search_analogs("^NSEI", L, 10, store_dir)
    for item in res:
        i = index_of[item["date"]]
        s = i - L + 1
        assert 0 <= s <= n - 2 * L - 10
        assert i + 10 < q0  # forward path strictly before the query window
        assert item["date"] < dates[q0]  # the query is never its own analog


def test_t004_reference_crosscheck(store_dir):
    df = read_store(store_dir)
    ref, _ = ref_search(df, 10, 10)
    res = search_analogs("^NSEI", 10, 10, store_dir)
    assert len(res) == len(ref) == 10
    for got, (d, date, _s) in zip(res, ref):
        assert got["date"] == date
        assert got["distance"] == pytest.approx(d, abs=1e-9)


def test_t005_frozen_anchors(store_dir):
    res = search_analogs("^NSEI", 10, 10, store_dir)
    expected = [
        ("2019-05-14", 0.570966011106),
        ("2020-03-20", 0.659910750504),
        ("2018-05-24", 0.668395481286),
    ]
    for item, (date, dist) in zip(res, expected):
        assert item["date"] == date
        assert item["distance"] == pytest.approx(dist, abs=1e-6)


def test_t006_forward_matches_store(store_dir):
    df = read_store(store_dir)
    dates = iso_dates(df)
    index_of = {d: i for i, d in enumerate(dates)}
    top = search_analogs("^NSEI", 10, 10, store_dir)[0]
    i = index_of[top["date"]]
    assert top["close"] == float(df["close"].iloc[i])  # R2 baseline = store close at tau
    fwd = df.iloc[i + 1 : i + 11]
    assert len(fwd) == 10
    for k, row in enumerate(top["forward"]):
        j = i + 1 + k
        assert row["date"] == dates[j]
        assert "volume" not in row
        assert row["open"] == float(fwd["open"].iloc[k])
        assert row["high"] == float(fwd["high"].iloc[k])
        assert row["low"] == float(fwd["low"].iloc[k])
        assert row["close"] == float(fwd["close"].iloc[k])


def test_t007_determinism(store_dir):
    first = search_analogs("^NSEI", 10, 10, store_dir)
    second = search_analogs("^NSEI", 10, 10, store_dir)
    assert first == second


def test_t008_k_is_cap(store_dir):
    r10 = search_analogs("^NSEI", 10, 10, store_dir)
    r3 = search_analogs("^NSEI", 10, 3, store_dir)
    r1 = search_analogs("^NSEI", 10, 1, store_dir)
    assert r3 == r10[:3]
    assert r1 == r10[:1]


def test_t009_hermetic_and_readonly(store_dir, monkeypatch):
    path = Path(store_dir) / "^NSEI.parquet"
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    def no_socket(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", no_socket)
    search_analogs("^NSEI", 10, 10, store_dir)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_t010_performance_sanity(store_dir):
    t0 = time.perf_counter()
    search_analogs("^NSEI", 10, 10, store_dir)
    assert time.perf_counter() - t0 < 5.0


# --- Section 2: parameterization ---


def test_t011_long_window_L60(store_dir):
    df = read_store(store_dir)
    L = 60
    n = len(df)
    q0 = n - L
    ref, pool = ref_search(df, L, 10)
    assert pool == n - 2 * L - 9 == 4544  # R1 arithmetic
    res = search_analogs("^NSEI", L, 10, store_dir)
    assert len(res) == 10
    assert res[0]["date"] == "2018-10-29"
    assert res[0]["distance"] == pytest.approx(2.581337345431, abs=1e-6)
    index_of = {d: i for i, d in enumerate(iso_dates(df))}
    for item in res:
        assert len(item["forward"]) == 10
        assert index_of[item["date"]] + 10 < q0
    for got, (d, date, _s) in zip(res, ref):
        assert got["date"] == date
        assert got["distance"] == pytest.approx(d, abs=1e-9)


def test_t012_boundary_window_L5(store_dir):
    df = read_store(store_dir)
    L = 5
    n = len(df)
    q0 = n - L
    _, pool = ref_search(df, L, 10)
    assert pool == n - 2 * L - 9 == 4654
    res = search_analogs("^NSEI", L, 10, store_dir)
    # contract of T-001 holds
    assert isinstance(res, list) and len(res) <= 10
    prev = float("-inf")
    for item in res:
        assert set(item) == {"date", "distance", "score", "close", "forward"}  # R2
        assert len(item["forward"]) == 10
        assert item["distance"] >= prev
        prev = item["distance"]
    assert res[0]["date"] == "2018-09-25"
    assert res[0]["distance"] == pytest.approx(0.164200033042, abs=1e-6)
    # eligibility rule with q0 = n - 5
    index_of = {d: i for i, d in enumerate(iso_dates(df))}
    for item in res:
        assert index_of[item["date"]] + 10 < q0


# --- Section 3: edge pools (tiny in-test stores, L=10) ---


def test_t013_short_pool_returns_all(tmp_path):
    closes = np.round(
        100 * np.cumprod(1 + np.random.default_rng(3).uniform(-0.01, 0.01, 30)), 2
    )
    out = make_store(tmp_path, closes)
    res = search_analogs("TINY", 10, 10, out)
    assert len(res) == 1  # whole pool; K is a cap
    item = res[0]
    assert len(item["forward"]) == 10
    dates = iso_dates(read_store(out, "TINY"))
    i = dates.index(item["date"])
    assert i + 10 < 30 - 10  # all 10 forward bars strictly before q0 = 20


def test_t014_empty_pool_rejected(tmp_path):
    closes = np.round(
        100 * np.cumprod(1 + np.random.default_rng(4).uniform(-0.01, 0.01, 29)), 2
    )
    out = make_store(tmp_path, closes)
    with pytest.raises(ValueError, match="bars"):
        search_analogs("TINY", 10, 10, out)


# --- Section 4: rejections ---


def test_t015_missing_store(store_dir):
    with pytest.raises(ValueError, match="store"):
        search_analogs("NOPE", 10, 10, store_dir)


def test_t016_window_bounds(store_dir):
    with pytest.raises(ValueError, match="window"):
        search_analogs("^NSEI", 4, 10, store_dir)
    with pytest.raises(ValueError, match="window"):
        search_analogs("^NSEI", 61, 10, store_dir)


def test_t017_window_types(store_dir):
    with pytest.raises(ValueError, match="window"):
        search_analogs("^NSEI", 10.5, 10, store_dir)
    with pytest.raises(ValueError, match="window"):
        search_analogs("^NSEI", True, 10, store_dir)


def test_t018_k_validation(store_dir):
    for bad in (0, -1, 1.5, True):
        with pytest.raises(ValueError, match="K"):
            search_analogs("^NSEI", 10, bad, store_dir)


# --- Section 5: deterministic ordering ---


def test_t019_exact_tie_earlier_date(tmp_path):
    rng = np.random.default_rng(7)
    closes = np.round(100 * np.cumprod(1 + rng.uniform(-0.01, 0.01, 40)), 2)
    closes[0:10] = 100.0  # flat window 1 -> sigma=0 -> zero vector
    closes[10:20] = 50.0  # flat window 2 -> sigma=0 -> zero vector
    out = make_store(tmp_path, closes)
    res = search_analogs("TINY", 10, 11, out)
    assert len(res) == 11  # full pool of 11
    order = [item["date"] for item in res]
    assert "2024-01-10" in order and "2024-01-20" in order
    by_date = {item["date"]: item for item in res}
    d_early = by_date["2024-01-10"]["distance"]
    d_late = by_date["2024-01-20"]["distance"]
    assert d_early == d_late  # exact tie
    assert d_early == pytest.approx(3.1622748239264022, abs=1e-9)
    # adjacent, earlier date first — the (distance, date) sort key
    assert order.index("2024-01-10") + 1 == order.index("2024-01-20")
