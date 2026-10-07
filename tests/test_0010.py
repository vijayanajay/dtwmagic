"""Frozen eval for spec 0010 — Gate 2: specs/tests/0010-v2-query-block.md.

IMMUTABLE: T-001..T-010 are transcribed from the frozen test spec (10 scenarios +
six §0 interface freezes, approved 2026-10-07).
Never edit to make failing code pass; fix src/snapshot_v2.py / src/eod_job.py instead.
"""
import hashlib
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import pytest

from src.eod_fetch import fetch_eod_index
from src.eod_job import run_eod_job
from src.ohlcv_store import build_store
from src.snapshot import build_snapshot
from src.snapshot_v2 import build_snapshot_v2

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path("tests/fixtures/nifty50_daily_ohlcv.csv")
PAYLOAD = Path("tests/fixtures/ind_close_all_20261005.csv")

# Gate 2 §0 freeze 1: fixture shas + zero-edits golden regression over ALL prior evals.
GUARD_SHAS = {
    "tests/fixtures/nifty50_daily_ohlcv.csv":
        "25657e31db82a50f98910015c6b57a93192cabf8eb42dee8e69e09678bf7a93e",
    "tests/fixtures/ind_close_all_20261005.csv":
        "f0b8004e9bc79b11cff3c939cb42cdeb4a31b71ebd03942b98b57f44fa3bc9ba",
    "tests/test_0001.py": "804a090d4db3b1ce9e37a6f186e6fefaf1966b69078daf5d128820725f99a09c",
    "tests/test_0002.py": "9a5ba0cb6f88b6948c0b5a6c4cecfa2289cea583a5201065bf13f6e1927f1cfc",
    "tests/test_0003.py": "0b3d1c560a68f538a1800d3bab0fc55adca951f7e986531694809f5d6490c06d",
    "tests/test_0004.py": "78d6184716ac333460c01565bd9db83be3d18855ea27048925e984906ab94730",
    "tests/test_0005.py": "a3769489f4a9b75ab9b507a91822593579c658979f2ea33f68d60caf92a94213",
    "tests/test_0006.py": "08f764b5797ca08bd99939ea7c673da47e152a2ad9da1efb592b07a994c05c35",
    "tests/test_0007.py": "e6295aa53c5aa300ade0ba64ec32b10335a2730fab0ea80ac6c5a742ba79867c",
    "tests/test_0008.py": "b90993e24332eccf85f2543115d77423a66ed412b28b4cc932f1170a89e6cb68",
    "tests/test_0009.py": "f693240cdd5d784f998b249073b37c44a9fc12ef884da5d52bd19c81efbc7ec5",
}

# Gate 2 §0 freeze 3 pins (probe-verified, PROBE_EXIT=0 / PROBE_B_EXIT=0)
V2_SHA256 = "4994e3ff8c1c2723630e9321a182ea61b4d8b01cc10cef5fc07e7737cc97c88f"
V2_BYTES = 69457
V1_SHA256 = "fa4c598cf59c2f65ad7284b451c786280735a909d8e84a604dd789634b781897"
V1_BYTES = 63791
C_FIRST = {"date": "2026-07-10", "open": 24124.7, "high": 24228.45,
           "low": 24120.35, "close": 24206.9}
C_MID = {"date": "2026-09-21", "open": 23330.2, "high": 23466.8,
         "low": 23314.8, "close": 23414.3}
C_LAST = {"date": "2026-10-05", "open": 22532.4, "high": 22621.8,
          "low": 22397.1, "close": 22555.75}
SLICE_FIRST = {"date": "2009-03-03", "open": 2672.15, "high": 2688.5,
               "low": 2611.55, "close": 2622.4}

# Gate 2 §0 freeze 4 (0009's frozen pins reused — report/errors unchanged)
SNAPSHOT_STAGE_ERROR = "snapshot: bars: store has 1 rows; window 5 needs >= 20"
UNKNOWN_SYMBOL_ERROR = "refresh: unknown symbol: '__NOPE__' (known: ['^NSEI'])"
REPORT_KEYS = ["symbol", "end_date", "ok", "refresh", "snapshot", "error"]
SNAPSHOT_KEYS = {"symbol", "path", "bytes", "last_date", "windows", "k"}
TOP_KEYS = ["schema", "symbol", "bars", "last_date", "regime", "windows", "query"]


@pytest.fixture(autouse=True)
def guards():
    """Gate 2 §0: fixture drift OR prior-eval edits invalidate this eval."""
    for path, sha in GUARD_SHAS.items():
        d = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert d == sha, f"frozen file edited: {path} ({d})"
    yield


@pytest.fixture(scope="session")
def store_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("store0010")
    build_store(FIXTURE, "^NSEI", out)
    return out


@pytest.fixture(scope="session")
def slice_dir(tmp_path_factory):
    """Fixture rows date <= 2009-06-04 -> SLICE store (416 rows), 0007's pattern."""
    out = tmp_path_factory.mktemp("slice0010")
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
    """Valid inline store (0007's make_rows pattern) for error-path tests."""
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


def fixture_df():
    return pd.read_csv(FIXTURE, dtype={"date": str})


def seed_master(root, df=None):
    """0002's derived ledger path: {parquet_dir.parent}/eod/{symbol}.csv."""
    root = Path(root)
    (root / "eod").mkdir(parents=True, exist_ok=True)
    (fixture_df() if df is None else df).to_csv(root / "eod" / "^NSEI.csv", index=False)
    return root


def recorder():
    """get stub that records URLs and fails the test if any call arrives."""
    calls = []

    def get(url):
        calls.append(url)
        raise AssertionError(f"unexpected get call: {url}")

    return calls, get


def run(root, get):
    return run_eod_job("^NSEI", "2007-09-17", "2026-10-05",
                       Path(root) / "parquet", Path(root) / "api", get=get)


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "src.eod_job", *args],
        capture_output=True, text=True, cwd=REPO_ROOT)


# --- Section 1: v2 document contract ---

def test_t001_v2_schema_and_shared_part(store_dir, tmp_path):
    out = tmp_path / "out"
    man = build_snapshot_v2("^NSEI", store_dir, out)
    doc = load_doc(man["path"])
    assert list(doc) == TOP_KEYS
    assert doc["schema"] == "dtwmagic.api.v2"
    man1 = build_snapshot("^NSEI", store_dir, tmp_path / "v1out")
    v1 = load_doc(man1["path"])
    for key in ["symbol", "bars", "last_date", "regime", "windows"]:
        assert doc[key] == v1[key], key


def test_t002_query_block_pins(store_dir, tmp_path):
    man = build_snapshot_v2("^NSEI", store_dir, tmp_path / "out")
    doc = load_doc(man["path"])
    q = doc["query"]
    assert list(q) == ["L", "candles"]
    assert q["L"] == 60
    assert len(q["candles"]) == 60
    for c in q["candles"]:
        assert list(c) == ["date", "open", "high", "low", "close"]
    assert q["candles"][0] == C_FIRST
    assert q["candles"][50] == C_MID
    assert q["candles"][59] == C_LAST
    assert q["candles"][59]["date"] == doc["last_date"] == "2026-10-05"
    assert doc["bars"] == 4673


def test_t003_store_tail_fidelity_manifest_readonly(store_dir, tmp_path):
    store_p = Path(store_dir) / "^NSEI.parquet"
    before = sha256_file(store_p)
    out = tmp_path / "deep" / "nested"
    man = build_snapshot_v2("^NSEI", store_dir, out)
    df = pd.read_parquet(store_p)
    tail = df.tail(60)
    dates = pd.to_datetime(tail["date"]).dt.strftime("%Y-%m-%d").tolist()
    expect = [
        {"date": dates[i],
         "open": float(tail["open"].iloc[i]),
         "high": float(tail["high"].iloc[i]),
         "low": float(tail["low"].iloc[i]),
         "close": float(tail["close"].iloc[i])}
        for i in range(60)
    ]
    doc = load_doc(man["path"])
    assert doc["query"]["candles"] == expect
    assert set(man) == SNAPSHOT_KEYS
    assert Path(man["path"]).name == "^NSEI.json"
    assert Path(man["path"]).parent == out
    assert man["bytes"] == Path(man["path"]).stat().st_size
    assert man["last_date"] == "2026-10-05"
    assert man["windows"] == [5, 10, 15, 30, 60]
    assert man["k"] == 10
    assert sha256_file(store_p) == before


def test_t004_byte_determinism_and_pins(store_dir, slice_dir, tmp_path):
    m1 = build_snapshot_v2("^NSEI", store_dir, tmp_path / "a")
    m2 = build_snapshot_v2("^NSEI", store_dir, tmp_path / "b")
    b1 = Path(m1["path"]).read_bytes()
    b2 = Path(m2["path"]).read_bytes()
    assert b1 == b2
    assert hashlib.sha256(b1).hexdigest() == V2_SHA256
    assert len(b1) == V2_BYTES
    assert b1.endswith(b"}\n")
    ms = build_snapshot_v2("SLICE", slice_dir, tmp_path / "s")
    assert sha256_file(ms["path"]) != V2_SHA256  # different store -> different file


def test_t005_zero_pool_slice(slice_dir, tmp_path):
    man = build_snapshot_v2("SLICE", slice_dir, tmp_path / "out")
    doc = load_doc(man["path"])
    assert doc["schema"] == "dtwmagic.api.v2"
    assert doc["bars"] == 416
    assert doc["last_date"] == "2009-06-04"
    for w in ["5", "10", "15", "30", "60"]:
        assert doc["windows"][w]["analogs"] == []
        assert doc["windows"][w]["summary"] is None
    assert set(doc["regime"]) == {"trend", "volatility", "cell", "p252"}
    q = doc["query"]
    assert len(q["candles"]) == 60
    assert q["candles"][0] == SLICE_FIRST
    assert q["candles"][-1]["date"] == "2009-06-04" == doc["last_date"]


def test_t006_errors_and_out_dir_creation(store_dir, tmp_path):
    with pytest.raises(ValueError, match="store"):
        build_snapshot_v2("NOPE", store_dir, tmp_path / "o1")
    tiny = make_rows(tmp_path / "tiny", 251)
    with pytest.raises(ValueError, match="regime"):
        build_snapshot_v2("TINY", tiny, tmp_path / "o2")
    out = tmp_path / "deep2" / "nested2"
    assert not out.exists()
    man = build_snapshot_v2("^NSEI", store_dir, out)
    assert out.exists()
    assert Path(man["path"]) == out / "^NSEI.json"
    assert load_doc(man["path"])["schema"] == "dtwmagic.api.v2"


# --- Section 2: nightly integration (Gate 1 2.6) ---

def test_t007_nightly_success_both_files(tmp_path):
    seed_master(tmp_path)
    calls, get = recorder()
    rep = run(tmp_path, get)
    assert list(rep) == REPORT_KEYS
    assert rep["ok"] is True
    assert rep["error"] is None
    snap = rep["snapshot"]
    assert set(snap) == SNAPSHOT_KEYS
    v1 = Path(snap["path"])
    assert sha256_file(v1) == V1_SHA256
    assert v1.stat().st_size == V1_BYTES
    v2 = tmp_path / "v2" / "^NSEI.json"
    assert v2.exists()
    assert sha256_file(v2) == V2_SHA256
    assert v2.stat().st_size == V2_BYTES
    assert load_doc(v2)["schema"] == "dtwmagic.api.v2"
    assert calls == []
    # CLI variant (freeze 4): one JSON line, exit 0, same two files.
    proc = _cli("--parquet-dir", str(tmp_path / "parquet"),
                "--snapshot-dir", str(tmp_path / "api"),
                "--end-date", "2026-10-05")
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.strip().splitlines()
    assert len(lines) == 1
    rep2 = json.loads(lines[0])
    assert list(rep2) == REPORT_KEYS
    assert rep2["ok"] is True
    assert sha256_file(v1) == V1_SHA256
    assert sha256_file(v2) == V2_SHA256


def test_t008_stage_honesty_prior_pins_untouched(tmp_path):
    seed_master(tmp_path)
    first = run(tmp_path, lambda url: None)
    assert first["ok"] is True
    v1 = Path(first["snapshot"]["path"])
    v2 = tmp_path / "v2" / "^NSEI.json"
    assert sha256_file(v1) == V1_SHA256
    assert sha256_file(v2) == V2_SHA256

    # (a) snapshot-stage failure: 1-row store -> exact frozen error, both pins live.
    one = fetch_eod_index("Nifty 50", "2026-10-05", "2026-10-05",
                          get=lambda url: PAYLOAD.read_bytes())
    seed_master(tmp_path, one)
    rep = run(tmp_path, lambda url: None)
    assert rep["ok"] is False
    assert rep["snapshot"] is None
    assert rep["error"] == SNAPSHOT_STAGE_ERROR
    assert sha256_file(v1) == V1_SHA256  # prior pin untouched
    assert sha256_file(v2) == V2_SHA256

    # (b) restore full store, then refresh-stage failure: both pins live.
    seed_master(tmp_path)
    again = run(tmp_path, lambda url: None)
    assert again["ok"] is True
    store_p = tmp_path / "parquet" / "^NSEI.parquet"
    store_bytes = store_p.read_bytes()
    seed_master(tmp_path, fixture_df().iloc[:-1])

    def boom(url):
        raise OSError("boom")

    rep2 = run(tmp_path, boom)
    assert rep2["ok"] is False
    assert rep2["refresh"] is None
    assert rep2["snapshot"] is None
    assert rep2["error"].startswith("refresh: ")
    assert "boom" in rep2["error"]
    assert store_p.read_bytes() == store_bytes
    assert sha256_file(v1) == V1_SHA256
    assert sha256_file(v2) == V2_SHA256

    # (c) unknown symbol: zero network, exact frozen error, pins live.
    calls, get = recorder()
    rep3 = run_eod_job("__NOPE__", "2007-09-17", "2026-10-05",
                       tmp_path / "parquet", tmp_path / "api", get=get)
    assert rep3["ok"] is False
    assert rep3["snapshot"] is None
    assert rep3["error"] == UNKNOWN_SYMBOL_ERROR
    assert calls == []
    assert sha256_file(v1) == V1_SHA256
    assert sha256_file(v2) == V2_SHA256


# --- Section 3: hygiene, isolation, performance ---

def test_t009_hermetic_readonly_isolation(tmp_path, monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", boom)
    seed_master(tmp_path)
    rep = run(tmp_path, lambda url: None)
    assert rep["ok"] is True
    store_p = tmp_path / "parquet" / "^NSEI.parquet"
    before = sha256_file(store_p)
    # both builders are read-only over the store (Gate 1 2.8)
    build_snapshot("^NSEI", tmp_path / "parquet", tmp_path / "o1")
    build_snapshot_v2("^NSEI", tmp_path / "parquet", tmp_path / "o2")
    assert sha256_file(store_p) == before
    # frontend isolation (freeze 6): the dashboard still consumes v1 only.
    page = (REPO_ROOT / "data" / "static" / "index.html").read_text(encoding="utf-8")
    assert "./api/v1/" in page
    assert "api/v2" not in page


def test_t010_performance_sanity(tmp_path):
    seed_master(tmp_path)
    get = lambda url: None
    run(tmp_path, get)  # warm-up
    times = []
    for _ in range(3):
        t0 = time.perf_counter()
        rep = run(tmp_path, get)
        times.append(time.perf_counter() - t0)
        assert rep["ok"] is True
    best = min(times)
    assert best <= 3.0, f"no-op run too slow: {best:.2f}s (bound 3.0s, probe 1.15s)"
