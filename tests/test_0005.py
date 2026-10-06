"""Frozen eval for spec 0005 — Gate 2: specs/tests/0005-regime-conditioning.md.

IMMUTABLE: T-001..T-017 are transcribed from the frozen test spec (17 scenarios +
six §0 interface freezes, approved 2026-10-06).
Never edit to make failing code pass; fix src/regime.py instead.
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
from src.outcome_stats import summarize_analogs
from src.pattern_search import search_analogs
from src.regime import search_analogs_regime

FIXTURE = Path("tests/fixtures/nifty50_daily_ohlcv.csv")
FIXTURE_SHA256 = "25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e"


@pytest.fixture(autouse=True)
def fixture_hash_guard():
    """Gate 2 §0: fixture drift invalidates the eval."""
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert digest == FIXTURE_SHA256, f"fixture drift: {digest}"
    yield


@pytest.fixture(scope="session")
def store_dir(tmp_path_factory):
    """Gate 2 §0 freeze 4: main store built once per session via 0001's seam."""
    out = tmp_path_factory.mktemp("store0005")
    build_store(FIXTURE, "^NSEI", out)
    return out


@pytest.fixture(scope="session")
def slice_dir(tmp_path_factory):
    """Gate 2 §0 freeze 4: fixture rows date <= 2009-06-04 -> SLICE store (416 rows)."""
    out = tmp_path_factory.mktemp("slice0005")
    raw = pd.read_csv(FIXTURE, parse_dates=["date"])
    sl = raw[raw["date"] <= "2009-06-04"]
    csv = out / "slice.csv"
    sl.to_csv(csv, index=False)
    build_store(csv, "SLICE", out)
    return out


def read_store(store_dir, symbol="^NSEI"):
    return pd.read_parquet(Path(store_dir) / f"{symbol}.parquet")


def iso_dates(df):
    return pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d").tolist()


def ref_cells(df):
    """Gate 2 §0 freeze 3: literal in-test classification, read-back store, no src imports.

    Gate 1 §2.2 parameters verbatim: ewm(span, adjust=True); TR_0 = high-low;
    ewm(alpha=1/14, adjust=False); rolling(252).rank(pct=True) incl. t;
    disjoint bins <=1/3, <=2/3; cell = f"{trend}-{volatility}"; None for t < 251.
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


def ref_chain(cells, L, n):
    """(full, classifiable, in-regime) by literal index arithmetic (Gate 2 §0 freeze 3)."""
    qcell = cells[-1]
    elig = range(L - 1, n - L - 10)  # tau in [L-1, n-L-11]  (size n - 2L - 9)
    cls = [t for t in elig if cells[t] is not None]
    inr = [t for t in cls if cells[t] == qcell]
    return len(elig), len(cls), len(inr)


def make_rows(base, n_rows, symbol="TINY"):
    """Gate 2 §0 freeze 4: valid in-test store (constant o=h=l=c per row, varying)."""
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


# --- Section 1: happy path (fixture store, L=10, K=10) ---


def test_t001_payload_contract(store_dir):
    res = search_analogs_regime("^NSEI", 10, 10, store_dir)
    assert isinstance(res, dict)
    assert set(res) == {"regime", "analogs"}
    reg = res["regime"]
    assert set(reg) == {"trend", "volatility", "cell", "p252"}
    assert reg["trend"] == "bearish"
    assert reg["volatility"] == "normal"
    assert reg["cell"] == "bearish-normal"
    assert reg["cell"] == f"{reg['trend']}-{reg['volatility']}"
    assert isinstance(reg["p252"], float)
    assert abs(reg["p252"] - 0.5476190476190477) <= 1e-15
    analogs = res["analogs"]
    assert isinstance(analogs, list)
    assert len(analogs) <= 10
    prev = float("-inf")
    for item in analogs:
        assert isinstance(item, dict)
        assert set(item) == {"date", "distance", "score", "close", "forward"}
        datetime.date.fromisoformat(item["date"])
        for key in ("distance", "score", "close"):
            assert isinstance(item[key], float)
        fwd = item["forward"]
        assert isinstance(fwd, list) and len(fwd) == 10
        fdates = []
        for row in fwd:
            assert set(row) == {"date", "open", "high", "low", "close"}
            datetime.date.fromisoformat(row["date"])
            for key in ("open", "high", "low", "close"):
                assert isinstance(row[key], float)
            fdates.append(row["date"])
        assert fdates == sorted(fdates)
        assert len(set(fdates)) == 10
        assert item["distance"] >= prev
        prev = item["distance"]


def test_t002_reference_classification(store_dir):
    df = read_store(store_dir)
    cells, _p = ref_cells(df)
    dates = iso_dates(df)
    assert all(c is None for c in cells[:251])
    assert cells[251] is not None
    assert dates[251] == "2008-09-19"
    assert cells[-1] == "bearish-normal"
    occ = {}
    for c in cells[251:]:
        occ[c] = occ.get(c, 0) + 1
    assert occ == {
        "bullish-low": 1334, "bullish-normal": 718, "bullish-high": 410,
        "bearish-low": 83, "bearish-normal": 145, "bearish-high": 381,
        "neutral-low": 320, "neutral-normal": 420, "neutral-high": 611,
    }
    assert sum(occ.values()) == 4422


def test_t003_filter_soundness_chain(store_dir):
    df = read_store(store_dir)
    n, L = len(df), 10
    cells, _ = ref_cells(df)
    i_of = {d: i for i, d in enumerate(iso_dates(df))}
    qcell = cells[-1]
    assert ref_chain(cells, L, n) == (4644, 4402, 131)
    full = search_analogs("^NSEI", L, n, store_dir)
    assert len(full) == 4644
    res = search_analogs_regime("^NSEI", L, 10, store_dir)
    analogs = res["analogs"]
    assert len(analogs) == min(10, 131)
    kept = set()
    for it in analogs:
        i = i_of[it["date"]]
        assert i >= 251
        assert cells[i] == qcell
        kept.add(it["date"])
    # order-preserving subsequence of the full unfiltered pool
    it_pool = iter([x["date"] for x in full])
    assert all(d in it_pool for d in [x["date"] for x in analogs])
    # R1 (user-directed 2026-10-06): exclusion checked on a K=131 call, so
    # "not returned" ⇔ "filtered out" holds literally (whole in-regime pool).
    all_kept = search_analogs_regime("^NSEI", L, 131, store_dir)["analogs"]
    assert len(all_kept) == 131
    assert [x["date"] for x in all_kept][:10] == [x["date"] for x in analogs]
    all_dates = {x["date"] for x in all_kept}
    for x in full:
        if x["date"] not in all_dates:
            i = i_of[x["date"]]
            assert cells[i] is None or cells[i] != qcell


def test_t004_composition_identity(store_dir):
    df = read_store(store_dir)
    n = len(df)
    res = search_analogs_regime("^NSEI", 10, 10, store_dir)
    full = {it["date"]: it for it in search_analogs("^NSEI", 10, n, store_dir)}
    assert res["analogs"], "sanity: fixture query has results"
    for item in res["analogs"]:
        src = full[item["date"]]
        assert item["distance"] == src["distance"]
        assert item["score"] == src["score"]
        assert item["close"] == src["close"]
        assert item["forward"] == src["forward"]
        assert item["score"] == pytest.approx(100.0 / (1.0 + item["distance"]), rel=1e-12)


def test_t005_frozen_anchors(store_dir):
    analogs = search_analogs_regime("^NSEI", 10, 10, store_dir)["analogs"]
    expect = [
        ("2012-05-14", 0.73704193241622),
        ("2016-01-12", 0.8686873884829724),
        ("2011-06-23", 1.1371357193691016),
    ]
    assert len(analogs) >= 3
    for item, (d, dist) in zip(analogs, expect):
        assert item["date"] == d
        assert item["distance"] == pytest.approx(dist, abs=1e-6)


def test_t006_k_caps_after_filter(store_dir):
    r10 = search_analogs_regime("^NSEI", 10, 10, store_dir)["analogs"]
    r3 = search_analogs_regime("^NSEI", 10, 3, store_dir)["analogs"]
    r1 = search_analogs_regime("^NSEI", 10, 1, store_dir)["analogs"]
    assert len(r3) == 3  # a cap-then-filter bug returns fewer: unfiltered top-3 are out-of-regime
    assert r3 == r10[:3]
    assert r1 == r10[:1]


def test_t007_determinism(store_dir):
    a = search_analogs_regime("^NSEI", 10, 10, store_dir)
    b = search_analogs_regime("^NSEI", 10, 10, store_dir)
    assert a == b


def test_t008_hermetic_readonly(store_dir, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", boom)
    p = Path(store_dir) / "^NSEI.parquet"
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    res = search_analogs_regime("^NSEI", 10, 10, store_dir)
    assert res["analogs"]
    assert hashlib.sha256(p.read_bytes()).hexdigest() == before


def test_t009_performance_sanity(store_dir):
    t0 = time.perf_counter()
    search_analogs_regime("^NSEI", 10, 10, store_dir)
    assert time.perf_counter() - t0 < 5.0


# --- Section 2: parameterization (window length L) ---


def test_t010_l60(store_dir):
    df = read_store(store_dir)
    n, L = len(df), 60
    cells, _ = ref_cells(df)
    i_of = {d: i for i, d in enumerate(iso_dates(df))}
    assert ref_chain(cells, L, n) == (4544, 4352, 128)
    res = search_analogs_regime("^NSEI", L, 10, store_dir)
    analogs = res["analogs"]
    assert len(analogs) == 10
    assert analogs[0]["date"] == "2012-06-04"
    assert analogs[0]["distance"] == pytest.approx(4.612532697912032, abs=1e-6)
    for it in analogs:
        i = i_of[it["date"]]
        assert i >= 251
        assert cells[i] == cells[-1]
        assert len(it["forward"]) == 10
    # ordering matches the reference filter within exact equality
    full = search_analogs("^NSEI", L, n, store_dir)
    ref = [it for it in full
           if cells[i_of[it["date"]]] is not None and cells[i_of[it["date"]]] == cells[-1]]
    assert analogs == ref[:10]


def test_t011_l5_lower_bound(store_dir):
    df = read_store(store_dir)
    n, L = len(df), 5
    cells, _ = ref_cells(df)
    i_of = {d: i for i, d in enumerate(iso_dates(df))}
    assert ref_chain(cells, L, n) == (4654, 4407, 131)
    res = search_analogs_regime("^NSEI", L, 10, store_dir)
    assert set(res) == {"regime", "analogs"}
    reg = res["regime"]
    assert set(reg) == {"trend", "volatility", "cell", "p252"}
    assert reg["cell"] == "bearish-normal"
    assert isinstance(reg["p252"], float)
    analogs = res["analogs"]
    assert len(analogs) == 10
    q0 = n - L
    for it in analogs:
        i = i_of[it["date"]]
        assert i >= 251
        assert i <= n - L - 11  # window + forward strictly before the query window
        assert cells[i] == cells[-1]
        assert i + 10 < q0


# --- Section 3: zero-result path (slice store, last session 2009-06-04) ---


def test_t012_zero_pool(slice_dir):
    res = search_analogs_regime("SLICE", 10, 10, slice_dir)
    assert set(res) == {"regime", "analogs"}
    reg = res["regime"]
    assert set(reg) == {"trend", "volatility", "cell", "p252"}
    assert reg["trend"] == "bullish"
    assert reg["volatility"] == "normal"
    assert reg["cell"] == "bullish-normal"
    assert reg["p252"] == pytest.approx(0.3492063492063492, abs=1e-15)
    assert res["analogs"] == []
    df = read_store(slice_dir, "SLICE")
    n = len(df)
    assert n == 416
    cells, _ = ref_cells(df)
    assert ref_chain(cells, 10, n) == (387, 145, 0)
    res60 = search_analogs_regime("SLICE", 60, 10, slice_dir)
    assert set(res60) == {"regime", "analogs"}
    assert res60["regime"] == reg
    assert res60["analogs"] == []
    assert ref_chain(cells, 60, n) == (287, 95, 0)


# --- Section 4: warmup & tiny stores ---


def test_t013_unclassifiable_query_regime(tmp_path):
    d = make_rows(tmp_path / "s251", 251)
    with pytest.raises(ValueError, match="regime"):
        search_analogs_regime("TINY", 10, 10, d)


def test_t014_classifiable_query_no_candidates(tmp_path):
    d = make_rows(tmp_path / "s252", 252)
    res = search_analogs_regime("TINY", 60, 10, d)
    assert set(res) == {"regime", "analogs"}
    assert res["analogs"] == []
    reg = res["regime"]
    assert isinstance(reg["p252"], float)
    assert np.isfinite(reg["p252"])
    df = read_store(d, "TINY")
    cells, _ = ref_cells(df)
    assert cells[251] is not None
    assert reg["cell"] == cells[-1]


def test_t015_validation_order(tmp_path):
    d40 = make_rows(tmp_path / "s40", 40)
    with pytest.raises(ValueError, match="regime"):
        search_analogs_regime("TINY", 10, 10, d40)
    d29 = make_rows(tmp_path / "s29", 29)
    with pytest.raises(ValueError, match="bars"):
        search_analogs_regime("TINY", 10, 10, d29)


# --- Section 5: rejections (pass-through keywords, fixture store) ---


def test_t016_rejections(store_dir, tmp_path):
    with pytest.raises(ValueError, match="store"):
        search_analogs_regime("NOPE", 10, 10, store_dir)
    with pytest.raises(ValueError, match="window"):
        search_analogs_regime("^NSEI", 4, 10, store_dir)
    with pytest.raises(ValueError, match="window"):
        search_analogs_regime("^NSEI", 61, 10, store_dir)
    with pytest.raises(ValueError, match="window"):
        search_analogs_regime("^NSEI", 10.5, 10, store_dir)
    with pytest.raises(ValueError, match="window"):
        search_analogs_regime("^NSEI", True, 10, store_dir)
    with pytest.raises(ValueError, match="K"):
        search_analogs_regime("^NSEI", 10, 0, store_dir)
    with pytest.raises(ValueError, match="K"):
        search_analogs_regime("^NSEI", 10, -1, store_dir)
    with pytest.raises(ValueError, match="K"):
        search_analogs_regime("^NSEI", 10, 1.5, store_dir)
    with pytest.raises(ValueError, match="K"):
        search_analogs_regime("^NSEI", 10, True, store_dir)


# --- Section 6: composition with 0004 & regression ---


def test_t017_reducer_composition(store_dir):
    df = read_store(store_dir)
    n = len(df)
    res = search_analogs_regime("^NSEI", 10, 10, store_dir)
    cells, _ = ref_cells(df)
    i_of = {d: i for i, d in enumerate(iso_dates(df))}
    full = search_analogs("^NSEI", 10, n, store_dir)
    ref_subset = [it for it in full
                  if cells[i_of[it["date"]]] is not None and cells[i_of[it["date"]]] == cells[-1]]
    a = summarize_analogs(res["analogs"])
    b = summarize_analogs(ref_subset[: len(res["analogs"])])
    assert a == b
    assert res["analogs"] == ref_subset[:10]
