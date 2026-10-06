"""Frozen eval for spec 0007 — Gate 2: specs/tests/0007-eod-snapshot.md.

IMMUTABLE: T-001..T-010 are transcribed from the frozen test spec (10 scenarios +
six §0 interface freezes, approved 2026-10-06).
Never edit to make failing code pass; fix src/snapshot.py instead.
"""
import hashlib
import json
import socket
import time
from pathlib import Path

import pandas as pd
import pytest

from src.ohlcv_store import build_store
from src.outcome_stats import summarize_analogs
from src.regime import search_analogs_regime
from src.snapshot import build_snapshot

FIXTURE = Path("tests/fixtures/nifty50_daily_ohlcv.csv")
FIXTURE_SHA256 = "25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e"

# Gate 2 §0 freeze 4: zero-edits golden regression over all prior evals.
FROZEN_EVALS = {
    "tests/test_0001.py": "804a090d4db3b1ce9e37a6f186e6fefaf1966b69078daf5d128820725f99a09c",
    "tests/test_0002.py": "9a5ba0cb6f88b6948c0b5a6c4cecfa2289cea583a5201065bf13f6e1927f1cfc",
    "tests/test_0003.py": "0b3d1c560a68f538a1800d3bab0fc55adca951f7e986531694809f5d6490c06d",
    "tests/test_0004.py": "78d6184716ac333460c01565bd9db83be3d18855ea27048925e984906ab94730",
    "tests/test_0005.py": "a3769489f4a9b75ab9b507a91822593579c658979f2ea33f68d60caf92a94213",
    "tests/test_0006.py": "08f764b5797ca08bd99939ea7c673da47e152a2ad9da1efb592b07a994c05c35",
}

# Gate 2 §0 freeze 4 pins (probe-verified, PROBE_EXIT=0)
SNAPSHOT_SHA256 = "fa4c598cf59c2f65ad7284b451c786280735a909d8e84a604dd789634b781897"
SNAPSHOT_BYTES = 63791
ANCHORS = {
    5: ("2011-06-21", 0.6545378884539143),
    10: ("2012-05-14", 0.73704193241622),
    15: ("2016-01-12", 1.1565867903174754),
    30: ("2011-05-24", 2.2385831629584225),
    60: ("2012-06-04", 4.612532697912032),
}
MANIFEST_KEYS = {"symbol", "path", "bytes", "last_date", "windows", "k"}


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
    out = tmp_path_factory.mktemp("store0007")
    build_store(FIXTURE, "^NSEI", out)
    return out


@pytest.fixture(scope="session")
def slice_dir(tmp_path_factory):
    """Fixture rows date <= 2009-06-04 -> SLICE store (416 rows)."""
    out = tmp_path_factory.mktemp("slice0007")
    raw = pd.read_csv(FIXTURE, parse_dates=["date"])
    sl = raw[raw["date"] <= "2009-06-04"]
    csv = out / "slice.csv"
    sl.to_csv(csv, index=False)
    build_store(csv, "SLICE", out)
    return out


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_doc(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def make_rows(base, n_rows, symbol="TINY"):
    """Valid inline store (0005's make_rows pattern) for error-path tests."""
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


# --- Section 1: document contract (fixture store) ---


def test_t001_schema(store_dir, tmp_path):
    man = build_snapshot("^NSEI", store_dir, tmp_path / "api")
    doc = load_doc(man["path"])
    assert list(doc) == ["schema", "symbol", "bars", "last_date", "regime", "windows"]
    assert doc["schema"] == "dtwmagic.api.v1"
    assert doc["symbol"] == "^NSEI"
    assert doc["bars"] == 4673
    assert doc["last_date"] == "2026-10-05"
    assert list(doc["windows"]) == ["5", "10", "15", "30", "60"]
    for key, block in doc["windows"].items():
        assert set(block) == {"L", "k", "analogs", "summary"}
        assert block["L"] == int(key)
        assert block["k"] == 10


def test_t002_regime_top_level(store_dir, tmp_path):
    man = build_snapshot("^NSEI", store_dir, tmp_path / "api")
    doc = load_doc(man["path"])
    direct = search_analogs_regime("^NSEI", 10, 10, store_dir)["regime"]
    assert doc["regime"] == direct
    assert doc["regime"]["cell"] == "bearish-normal"
    assert abs(doc["regime"]["p252"] - 0.5476190476190477) <= 1e-15


def test_t003_window_contents_equal_direct_calls(store_dir, tmp_path):
    man = build_snapshot("^NSEI", store_dir, tmp_path / "api")
    doc = load_doc(man["path"])
    for key, block in doc["windows"].items():
        L = int(key)
        direct = search_analogs_regime("^NSEI", L, 10, store_dir)["analogs"]
        assert block["analogs"] == direct  # exact, JSON round-trip included
        assert len(block["analogs"]) == 10
        ds = [a["distance"] for a in block["analogs"]]
        assert ds == sorted(ds)


def test_t004_summary_recompute_and_horizon_keys(store_dir, tmp_path):
    man = build_snapshot("^NSEI", store_dir, tmp_path / "api")
    doc = load_doc(man["path"])
    for key, block in doc["windows"].items():
        L = int(key)
        direct = search_analogs_regime("^NSEI", L, 10, store_dir)["analogs"]
        assert block["summary"] == json.loads(json.dumps(summarize_analogs(direct)))
        s = block["summary"]
        assert s["n"] == 10
        assert s["horizons"] == list(range(1, 11))
        assert all(isinstance(h, int) for h in s["horizons"])  # JSON array of ints
        expected_keys = [str(h) for h in range(1, 11)]
        for section in ("cone", "positive_frequency", "mae", "mfe"):
            assert sorted(s[section], key=int) == expected_keys
            assert all(isinstance(k, str) for k in s[section])  # frozen contract


def test_t005_anchors(store_dir, tmp_path):
    man = build_snapshot("^NSEI", store_dir, tmp_path / "api")
    doc = load_doc(man["path"])
    for L, (date, dist) in ANCHORS.items():
        top = doc["windows"][str(L)]["analogs"][0]
        assert top["date"] == date
        assert top["distance"] == pytest.approx(dist, abs=1e-6)


# --- Section 2: determinism & byte contract ---


def test_t006_bytes(store_dir, tmp_path):
    store_p = Path(store_dir) / "^NSEI.parquet"
    before = sha256_file(store_p)
    out = tmp_path / "api"
    m1 = build_snapshot("^NSEI", store_dir, out)
    sha1 = sha256_file(m1["path"])
    m2 = build_snapshot("^NSEI", store_dir, out)
    sha2 = sha256_file(m2["path"])
    assert sha1 == sha2 == SNAPSHOT_SHA256
    assert Path(m1["path"]).stat().st_size == SNAPSHOT_BYTES
    assert sha256_file(store_p) == before


# --- Section 3: edge path (slice store, last session 2009-06-04) ---


def test_t007_zero_pool_null_summary(slice_dir, tmp_path):
    man = build_snapshot("SLICE", slice_dir, tmp_path / "api")
    assert set(man) == MANIFEST_KEYS
    assert man["last_date"] == "2009-06-04"
    assert man["windows"] == [5, 10, 15, 30, 60]
    assert man["k"] == 10
    doc = load_doc(man["path"])
    assert doc["bars"] == 416
    assert doc["last_date"] == "2009-06-04"
    reg = doc["regime"]
    assert reg["trend"] == "bullish"
    assert reg["volatility"] == "normal"
    assert reg["cell"] == "bullish-normal"
    assert abs(reg["p252"] - 0.3492063492063492) <= 1e-15
    for key, block in doc["windows"].items():
        assert block["analogs"] == [], f"window {key} must be empty on this day"
        assert block["summary"] is None


# --- Section 4: hygiene, errors, performance ---


def test_t008_hermetic_mkdir(store_dir, tmp_path, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", boom)
    store_p = Path(store_dir) / "^NSEI.parquet"
    before = sha256_file(store_p)
    out = tmp_path / "deep" / "nested"
    assert not out.exists()
    man = build_snapshot("^NSEI", store_dir, out)
    assert out.exists()
    assert (out / "^NSEI.json").exists()
    assert Path(man["path"]) == out / "^NSEI.json"
    assert sha256_file(store_p) == before


def test_t009_manifest_contract(store_dir, tmp_path):
    man = build_snapshot("^NSEI", store_dir, tmp_path / "api")
    assert set(man) == MANIFEST_KEYS
    assert man["symbol"] == "^NSEI"
    assert isinstance(man["path"], str)
    assert man["path"].endswith("^NSEI.json")
    assert Path(man["path"]).exists()
    assert isinstance(man["bytes"], int)
    assert man["bytes"] == Path(man["path"]).stat().st_size
    assert man["last_date"] == "2026-10-05"
    assert man["windows"] == [5, 10, 15, 30, 60]
    assert man["k"] == 10


def test_t010_errors_and_perf(store_dir, tmp_path):
    with pytest.raises(ValueError, match="store"):
        build_snapshot("NOPE", store_dir, tmp_path / "o1")
    tiny = make_rows(tmp_path / "tiny", 251)
    with pytest.raises(ValueError, match="regime"):
        build_snapshot("TINY", tiny, tmp_path / "o2")
    build_snapshot("^NSEI", store_dir, tmp_path / "o3")  # warm-up
    best = 1e9
    for _ in range(3):
        t0 = time.perf_counter()
        build_snapshot("^NSEI", store_dir, tmp_path / "o4")
        best = min(best, time.perf_counter() - t0)
    assert best <= 2.0, f"snapshot took {best:.3f}s (bound 2.0s)"
