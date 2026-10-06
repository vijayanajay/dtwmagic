"""Frozen eval for spec 0004 — Gate 2: specs/tests/0004-outcome-stats.md.

IMMUTABLE: T-001..T-015 are transcribed from the frozen test spec.
Never edit to make failing code pass; fix src/outcome_stats.py instead.
"""
import hashlib
import math
import socket
import time
from pathlib import Path

import numpy as np
import pytest

from src.ohlcv_store import build_store
from src.outcome_stats import summarize_analogs
from src.pattern_search import search_analogs

FIXTURE = Path("tests/fixtures/nifty50_daily_ohlcv.csv")
FIXTURE_SHA256 = "25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e"
QUANTILES = (("p10", 0.10), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p90", 0.90))


@pytest.fixture(autouse=True)
def fixture_hash_guard():
    """Gate 2 §0 freeze 3: fixture drift invalidates the eval."""
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert digest == FIXTURE_SHA256, f"fixture drift: {digest}"
    yield


@pytest.fixture(scope="session")
def store_dir(tmp_path_factory):
    """Composition store: 0001 seam on the committed fixture (hermetic)."""
    out = tmp_path_factory.mktemp("store0004")
    build_store(FIXTURE, "^NSEI", out)
    return out


def mk(closes, base, lows=None, highs=None):
    """R2-shaped synthetic analog (Gate 2 §0 freeze 2); open = close."""
    closes = [float(c) for c in closes]
    lows = [float(v) for v in lows] if lows is not None else list(closes)
    highs = [float(v) for v in highs] if highs is not None else list(closes)
    forward = [
        {"date": f"2024-01-{i + 1:02d}", "open": c, "high": hi, "low": lo, "close": c}
        for i, (c, lo, hi) in enumerate(zip(closes, lows, highs))
    ]
    return {
        "date": "2024-01-01",
        "distance": 0.5,
        "score": 66.6,
        "close": float(base),
        "forward": forward,
    }


def qlin(vals, q):
    """Hand-rolled numpy-'linear' quantile: h=(n-1)*q, lerp (never np.quantile)."""
    x = sorted(vals)
    n = len(x)
    h = (n - 1) * q
    lo, hi = int(np.floor(h)), int(np.ceil(h))
    return x[lo] + (h - lo) * (x[hi] - x[lo])


def ref(analogs):
    """Literal reference (Gate 2 §0 freeze 1): loops + qlin, no import from src/."""
    n = len(analogs)
    out = {
        "n": n,
        "horizons": list(range(1, 11)),
        "cone": {},
        "positive_frequency": {},
        "mae": {},
        "mfe": {},
    }
    for h in range(1, 11):
        R, M, F = [], [], []
        for a in analogs:
            p = a["close"]
            f = a["forward"]
            R.append(f[h - 1]["close"] / p - 1)
            M.append(min(f[j]["low"] / p - 1 for j in range(h)))
            F.append(max(f[j]["high"] / p - 1 for j in range(h)))
        out["cone"][h] = {k: qlin(R, q) for k, q in QUANTILES}
        out["positive_frequency"][h] = sum(1 for v in R if v > 0) / n
        out["mae"][h] = {"p80": -qlin([-v for v in M], 0.80)}
        out["mfe"][h] = {"p50": qlin(F, 0.50)}
    return out


def assert_maps_close(got, want, tol=1e-12):
    """Compare the four frozen maps (and horizons) between two results."""
    assert got["horizons"] == want["horizons"]
    for h in want["horizons"]:
        for k, q in QUANTILES:
            assert got["cone"][h][k] == pytest.approx(want["cone"][h][k], abs=tol)
        assert got["positive_frequency"][h] == pytest.approx(
            want["positive_frequency"][h], abs=tol
        )
        assert got["mae"][h]["p80"] == pytest.approx(want["mae"][h]["p80"], abs=tol)
        assert got["mfe"][h]["p50"] == pytest.approx(want["mfe"][h]["p50"], abs=tol)


def assert_profiles_monotone(res):
    """Gate 1 §2.2 invariants: mfe non-decreasing, mae non-increasing, mae<=mfe."""
    mfe = [res["mfe"][h]["p50"] for h in range(1, 11)]
    mae = [res["mae"][h]["p80"] for h in range(1, 11)]
    assert all(mfe[i + 1] >= mfe[i] for i in range(9))
    assert all(mae[i + 1] <= mae[i] for i in range(9))
    assert all(res["mae"][h]["p80"] <= res["mfe"][h]["p50"] for h in range(1, 11))


def hand_case():
    a = mk([100 * (1 + 0.01 * j) for j in range(1, 11)], 100)  # closes 101..110
    b = mk([100 * (1 - 0.01 * j) for j in range(1, 11)], 100)  # closes 99..90
    return [a, b]


# --- Section 1: output contract ---


def test_t001_frozen_dict_shape():
    analogs = [
        mk([100 * (1 + 0.01 * j) for j in range(1, 11)], 100),
        mk([100 * (1 - 0.005 * j) for j in range(1, 11)], 100),
        mk([105, 97, 104, 96, 105, 95, 106, 94, 107, 93], 100),
    ]
    res = summarize_analogs(analogs)
    assert set(res) == {"n", "horizons", "cone", "positive_frequency", "mae", "mfe"}
    assert res["n"] == 3 and isinstance(res["n"], int)
    assert res["horizons"] == list(range(1, 11))
    assert all(isinstance(h, int) for h in res["horizons"])
    for m in (res["cone"], res["positive_frequency"], res["mae"], res["mfe"]):
        assert set(m) == set(range(1, 11))
        assert all(isinstance(k, int) for k in m)
    for h in range(1, 11):
        assert set(res["cone"][h]) == {"p10", "p25", "p50", "p75", "p90"}
        assert set(res["mae"][h]) == {"p80"}
        assert set(res["mfe"][h]) == {"p50"}
        for v in res["cone"][h].values():
            assert isinstance(v, float)
        freq = res["positive_frequency"][h]
        assert isinstance(freq, float) and 0.0 <= freq <= 1.0
        assert isinstance(res["mae"][h]["p80"], float)
        assert isinstance(res["mfe"][h]["p50"], float)
        assert res["mae"][h]["p80"] <= res["mfe"][h]["p50"]


def test_t002_reference_crosscheck_and_signs():
    # X: every low above the baseline -> MAE > 0; Y: every high below -> MFE < 0
    x_c = [105 + j for j in range(10)]
    y_c = [95 - j for j in range(10)]
    X = mk(x_c, 100, lows=[c - 0.5 for c in x_c], highs=[c + 1 for c in x_c])
    Y = mk(y_c, 100, lows=[c - 1 for c in y_c], highs=[c + 0.5 for c in y_c])
    Z = mk([103, 97, 104, 96, 105, 95, 106, 94, 107, 93], 100,
           lows=[99, 95, 100, 94, 101, 93, 102, 92, 103, 91],
           highs=[104, 99, 105, 98, 107, 97, 108, 96, 109, 95])
    analogs = [X, Y, Z]
    got = summarize_analogs(analogs)
    want = ref(analogs)
    assert got["n"] == want["n"] == 3
    assert_maps_close(got, want, tol=1e-12)
    # sign semantics (Gate 1 2.2 correction) through the public seam
    assert summarize_analogs([X])["mae"][1]["p80"] > 0
    assert summarize_analogs([Y])["mfe"][1]["p50"] < 0


def test_t003_determinism():
    analogs = hand_case()
    assert summarize_analogs(analogs) == summarize_analogs(analogs)


def test_t004_performance_sanity(store_dir):
    analogs = search_analogs("^NSEI", 10, 10, store_dir)
    t0 = time.perf_counter()
    summarize_analogs(analogs)
    assert time.perf_counter() - t0 < 5.0


# --- Section 2: aggregation math (hand-verifiable pins) ---


def test_t005_two_analog_hand_case():
    res = summarize_analogs(hand_case())
    for h in range(1, 11):
        cone = res["cone"][h]
        assert cone["p10"] == pytest.approx(-0.008 * h, abs=1e-12)
        assert cone["p25"] == pytest.approx(-0.005 * h, abs=1e-12)
        assert cone["p50"] == pytest.approx(0.0, abs=1e-12)
        assert cone["p75"] == pytest.approx(0.005 * h, abs=1e-12)
        assert cone["p90"] == pytest.approx(0.008 * h, abs=1e-12)
        assert res["positive_frequency"][h] == 0.5
        assert res["mae"][h]["p80"] == pytest.approx(-(0.008 * h - 0.002), abs=1e-12)
        assert res["mfe"][h]["p50"] == pytest.approx(0.005 * h - 0.005, abs=1e-12)


def test_t006_unweighted_duplication():
    """Revision R1: freq invariance + reference match (quantiles shift with n)."""
    base = hand_case() + [mk([101, 99, 102, 98, 103, 97, 104, 96, 105, 95], 100)]
    s1 = summarize_analogs(base)
    s2 = summarize_analogs(base + base)
    assert s2["n"] == 2 * s1["n"]
    for h in range(1, 11):  # the ratio is the duplication-invariant statistic
        assert s2["positive_frequency"][h] == s1["positive_frequency"][h]
    # the real unweighted proof: both lists match the unweighted reference
    assert_maps_close(s1, ref(base), tol=1e-12)
    assert_maps_close(s2, ref(base + base), tol=1e-12)


def test_t007_monotonicity(store_dir):
    assert_profiles_monotone(summarize_analogs(hand_case()))  # T-005 input
    analogs = search_analogs("^NSEI", 10, 10, store_dir)      # T-009 input
    assert_profiles_monotone(summarize_analogs(analogs))


def test_t008_strict_positive_frequency():
    flat = summarize_analogs([mk([100.0] * 10, 100)])
    rise = summarize_analogs([mk([100 * (1 + 0.01 * j) for j in range(1, 11)], 100)])
    for h in range(1, 11):
        assert flat["positive_frequency"][h] == 0.0  # zero return is not positive
        assert rise["positive_frequency"][h] == 1.0


# --- Section 3: composition ---


def test_t009_composition_anchors(store_dir):
    analogs = search_analogs("^NSEI", 10, 10, store_dir)
    res = summarize_analogs(analogs)
    assert res["n"] == 10
    assert_maps_close(res, ref(analogs), tol=1e-12)
    assert_profiles_monotone(res)
    c10 = res["cone"][10]
    assert c10["p10"] == pytest.approx(-0.01247148067428826, abs=1e-9)
    assert c10["p25"] == pytest.approx(-0.009747233614655182, abs=1e-9)
    assert c10["p50"] == pytest.approx(0.01105743068690379, abs=1e-9)
    assert c10["p75"] == pytest.approx(0.023938272265599192, abs=1e-9)
    assert c10["p90"] == pytest.approx(0.061937355116913805, abs=1e-9)
    assert res["cone"][1]["p50"] == pytest.approx(0.002058221272220273, abs=1e-9)
    assert res["positive_frequency"][3] == 0.7
    assert res["positive_frequency"][5] == 0.7
    assert res["positive_frequency"][10] == 0.6
    assert res["mae"][10]["p80"] == pytest.approx(-0.0267533227, abs=1e-9)
    assert res["mae"][1]["p80"] == pytest.approx(-0.0116546747, abs=1e-9)
    assert res["mfe"][5]["p50"] == pytest.approx(0.0232016430, abs=1e-9)
    assert res["mfe"][10]["p50"] == pytest.approx(0.0287962421, abs=1e-9)


# --- Section 4: rejections ---


def test_t010_analogs_keyword():
    with pytest.raises(ValueError, match="analogs"):
        summarize_analogs("nope")
    with pytest.raises(ValueError, match="analogs"):
        summarize_analogs({})
    with pytest.raises(ValueError, match="analogs"):
        summarize_analogs([])


def test_t011_analog_keyword():
    with pytest.raises(ValueError, match="analog"):
        summarize_analogs([42])
    with pytest.raises(ValueError, match="analog"):
        summarize_analogs([None])


def test_t012_close_keyword():
    good = mk([101, 102, 103, 104, 105, 106, 107, 108, 109, 110], 100)
    missing = dict(good)
    del missing["close"]
    with pytest.raises(ValueError, match="close"):
        summarize_analogs([missing])
    for bad in (0, -5, float("nan")):
        with pytest.raises(ValueError, match="close"):
            summarize_analogs([dict(good, close=bad)])


def test_t013_forward_keyword():
    good = mk([101, 102, 103, 104, 105, 106, 107, 108, 109, 110], 100)
    missing = dict(good)
    del missing["forward"]
    with pytest.raises(ValueError, match="forward"):
        summarize_analogs([missing])
    with pytest.raises(ValueError, match="forward"):
        summarize_analogs([dict(good, forward=good["forward"][:9])])
    with pytest.raises(ValueError, match="forward"):
        summarize_analogs([dict(good, forward=123)])


# --- Section 5: edge semantics ---


def test_t014_single_analog():
    a = mk([100 * (1 + 0.01 * j) for j in range(1, 11)], 100)
    res = summarize_analogs([a])
    assert res["n"] == 1
    seen = []
    for h in range(1, 11):
        for k in ("p10", "p25", "p50", "p75", "p90"):
            v = res["cone"][h][k]
            seen.append(v)
            assert v == pytest.approx(0.01 * h, abs=1e-12)
        assert res["positive_frequency"][h] == 1.0
        mae = res["mae"][h]["p80"]
        seen.append(mae)
        assert mae == pytest.approx(0.01, abs=1e-12)
        assert mae > 0  # every forward low stays above the baseline
        mfe = res["mfe"][h]["p50"]
        seen.append(mfe)
        assert mfe == pytest.approx(0.01 * h, abs=1e-12)
    assert not any(math.isnan(v) for v in seen)


def test_t015_hermetic(store_dir, monkeypatch):
    def no_socket(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", no_socket)
    summarize_analogs(hand_case())  # synthetic
    analogs = search_analogs("^NSEI", 10, 10, store_dir)
    summarize_analogs(analogs)      # composition
