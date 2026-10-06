"""Frozen eval for spec 0006 — Gate 2: specs/tests/0006-search-latency.md.

IMMUTABLE: T-001..T-009 are transcribed from the frozen test spec (9 scenarios +
five §0 interface freezes, approved 2026-10-06).
Never edit to make failing code pass; fix src/pattern_search.py / src/regime.py.
"""
import hashlib
import socket
import time
from pathlib import Path

import pytest

import src.regime as regime_mod
from src.ohlcv_store import build_store
from src.pattern_search import search_analogs
from src.regime import search_analogs_regime

FIXTURE = Path("tests/fixtures/nifty50_daily_ohlcv.csv")
FIXTURE_SHA256 = "25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e"

# Gate 2 §0 freeze 2: the zero-edits golden regression, enforced per run.
FROZEN_EVALS = {
    "tests/test_0001.py": "804a090d4db3b1ce9e37a6f186e6fefaf1966b69078daf5d128820725f99a09c",
    "tests/test_0002.py": "9a5ba0cb6f88b6948c0b5a6c4cecfa2289cea583a5201065bf13f6e1927f1cfc",
    "tests/test_0003.py": "0b3d1c560a68f538a1800d3bab0fc55adca951f7e986531694809f5d6490c06d",
    "tests/test_0004.py": "78d6184716ac333460c01565bd9db83be3d18855ea27048925e984906ab94730",
    "tests/test_0005.py": "a3769489f4a9b75ab9b507a91822593579c658979f2ea33f68d60caf92a94213",
}


@pytest.fixture(autouse=True)
def guards():
    """Gate 2 §0: fixture drift OR prior-eval edits invalidate this eval."""
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert digest == FIXTURE_SHA256, f"fixture drift: {digest}"
    for path, sha in FROZEN_EVALS.items():
        d = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert d == sha, f"frozen eval edited: {path} ({d})"
    yield


@pytest.fixture(scope="session")
def store_dir(tmp_path_factory):
    """Gate 2 §0 freeze 5: session store via 0001's seam from the guarded fixture."""
    out = tmp_path_factory.mktemp("store0006")
    build_store(FIXTURE, "^NSEI", out)
    return out


@pytest.fixture
def spy(monkeypatch):
    """Gate 2 §0 freeze 1: counting passthrough over src.regime's bound name."""
    calls = []
    real = regime_mod.search_analogs

    def counting(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(regime_mod, "search_analogs", counting)
    return calls


def read_store(store_dir, symbol="^NSEI"):
    import pandas as pd
    return pd.read_parquet(Path(store_dir) / f"{symbol}.parquet")


def iso_dates(df):
    import pandas as pd
    return pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").tolist()


def make_rows(base, n_rows, symbol="TINY"):
    """Gate 2 §0 freeze 5: valid inline store (0005's make_rows pattern)."""
    import datetime
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    lines = ["date,open,high,low,close,volume"]
    for i in range(n_rows):
        d = (datetime.date(2024, 1, 1) + datetime.timedelta(days=i)).isoformat()
        v = 100 + 0.5 * i
        lines.append(f"{d},{v},{v},{v},{v},0")
    csv = base / "in.csv"
    csv.write_text("\n".join(lines) + "\n")
    out = base / "store"
    build_store(csv, symbol, out)
    return out


# --- Section 1: single-pass behavior (Fix B) ---


def test_t001_single_pass_success(store_dir, spy):
    res = search_analogs_regime("^NSEI", 10, 10, store_dir)
    assert len(spy) == 1, f"expected exactly 1 search_analogs call, got {len(spy)}"
    args, _kwargs = spy[0]
    assert args[2] == 4673  # the full-pool request: K == n
    assert set(res) == {"regime", "analogs"}
    assert len(res["analogs"]) == 10
    reg = res["regime"]
    assert set(reg) == {"trend", "volatility", "cell", "p252"}
    assert reg["cell"] == "bearish-normal"
    assert abs(reg["p252"] - 0.5476190476190477) <= 1e-15


def test_t002_validations_short_circuit(store_dir, tmp_path, spy):
    with pytest.raises(ValueError, match="store"):
        search_analogs_regime("NOPE", 10, 10, store_dir)
    assert len(spy) == 0
    with pytest.raises(ValueError, match="window"):
        search_analogs_regime("^NSEI", 61, 10, store_dir)
    assert len(spy) == 0
    with pytest.raises(ValueError, match="window"):
        search_analogs_regime("^NSEI", True, 10, store_dir)
    assert len(spy) == 0
    with pytest.raises(ValueError, match="K"):
        search_analogs_regime("^NSEI", 10, 0, store_dir)
    assert len(spy) == 0
    with pytest.raises(ValueError, match="K"):
        search_analogs_regime("^NSEI", 10, -1, store_dir)
    assert len(spy) == 0


def test_t003_bars_regime_order(store_dir, tmp_path, spy):
    d29 = make_rows(tmp_path / "s29", 29)
    with pytest.raises(ValueError, match="bars"):
        search_analogs_regime("TINY", 10, 10, d29)
    assert len(spy) == 1  # the single call is what reports `bars`
    d40 = make_rows(tmp_path / "s40", 40)
    with pytest.raises(ValueError, match="regime"):
        search_analogs_regime("TINY", 10, 10, d40)
    assert len(spy) == 2  # one call per invocation; then the regime gate fired


# --- Section 2: payload integrity (Fix A) ---


def test_t004_payload_identity(store_dir):
    df = read_store(store_dir)
    n = len(df)
    full = search_analogs("^NSEI", 10, n, store_dir)
    assert len(full) == 4644
    dates = iso_dates(df)
    i_of = {d: i for i, d in enumerate(dates)}
    wrap = search_analogs_regime("^NSEI", 10, 10, store_dir)["analogs"]
    sample = [full[i] for i in (0, 1, 2, 2321, 2322, 2323, 4641, 4642, 4643)]
    for item in sample + wrap:
        assert type(item["distance"]) is float
        assert type(item["score"]) is float
        assert type(item["close"]) is float
        tau = i_of[item["date"]]
        assert item["close"] == float(df["close"].iloc[tau])  # bit-identical
        fwd = item["forward"]
        assert len(fwd) == 10
        fdates = [r["date"] for r in fwd]
        assert fdates == sorted(fdates) and len(set(fdates)) == 10
        for k, row in enumerate(fwd):
            r = tau + 1 + k
            assert row["date"] == dates[r]
            for key in ("open", "high", "low", "close"):
                assert type(row[key]) is float
                assert row[key] == float(df[key].iloc[r])  # bit-identical


def test_t005_search_anchors(store_dir):
    res = search_analogs("^NSEI", 10, 10, store_dir)
    expect = [
        ("2019-05-14", 0.570966011106),
        ("2020-03-20", 0.659910750504),
        ("2018-05-24", 0.668395481286),
    ]
    prev = float("-inf")
    for item, (d, dist) in zip(res, expect):
        assert item["date"] == d
        assert item["distance"] == pytest.approx(dist, abs=1e-6)
        assert item["score"] == pytest.approx(100.0 / (1.0 + item["distance"]), rel=1e-12)
        assert item["distance"] >= prev
        prev = item["distance"]


def test_t006_wrapper_anchors(store_dir):
    res = search_analogs_regime("^NSEI", 10, 10, store_dir)
    analogs = res["analogs"]
    assert len(analogs) == 10
    assert analogs[0]["date"] == "2012-05-14"
    assert analogs[0]["distance"] == pytest.approx(0.73704193241622, abs=1e-6)
    reg = res["regime"]
    assert set(reg) == {"trend", "volatility", "cell", "p252"}
    assert reg["cell"] == "bearish-normal"
    assert abs(reg["p252"] - 0.5476190476190477) <= 1e-15


# --- Section 3: performance & hygiene ---


def test_t007_perf_bounds(store_dir):
    search_analogs("^NSEI", 10, 10, store_dir)  # warm-up
    best_full = min(
        (lambda t0: (search_analogs("^NSEI", 10, 4673, store_dir), time.perf_counter() - t0)[1])(time.perf_counter())
        for _ in range(3)
    )
    assert best_full <= 1.0, f"full pool took {best_full:.3f}s (baseline 2.332s, bound 1.0s)"
    search_analogs_regime("^NSEI", 10, 10, store_dir)  # warm-up
    best_wrap = min(
        (lambda t0: (search_analogs_regime("^NSEI", 10, 10, store_dir), time.perf_counter() - t0)[1])(time.perf_counter())
        for _ in range(3)
    )
    assert best_wrap <= 1.0, f"wrapper took {best_wrap:.3f}s (baseline 2.332s, bound 1.0s)"


def test_t008_determinism(store_dir):
    a1 = search_analogs_regime("^NSEI", 10, 10, store_dir)
    a2 = search_analogs_regime("^NSEI", 10, 10, store_dir)
    assert a1 == a2
    f1 = search_analogs("^NSEI", 10, 4673, store_dir)
    f2 = search_analogs("^NSEI", 10, 4673, store_dir)
    assert f1 == f2


def test_t009_hermetic_readonly(store_dir, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", boom)
    p = Path(store_dir) / "^NSEI.parquet"
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    res = search_analogs_regime("^NSEI", 10, 10, store_dir)
    full = search_analogs("^NSEI", 10, 4673, store_dir)
    assert res["analogs"] and len(full) == 4644
    assert hashlib.sha256(p.read_bytes()).hexdigest() == before
