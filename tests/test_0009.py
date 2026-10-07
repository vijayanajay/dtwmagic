"""Frozen eval for spec 0009 — Gate 2: specs/tests/0009-eod-nightly-job.md.

IMMUTABLE: T-001..T-010 are transcribed from the frozen test spec (10 scenarios +
six §0 interface freezes, approved 2026-10-07).
Never edit to make failing code pass; fix src/eod_job.py instead.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path("tests/fixtures/nifty50_daily_ohlcv.csv")
PAYLOAD = Path("tests/fixtures/ind_close_all_20261005.csv")

# Gate 2 §0 freeze 1: fixture shas + zero-edits golden regression over all prior evals.
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
}

# Gate 2 §0 freeze 5 pins (probe-verified, PROBE_EXIT=0 / PROBE3_EXIT=0)
SNAPSHOT_SHA256 = "fa4c598cf59c2f65ad7284b451c786280735a909d8e84a604dd789634b781897"
SNAPSHOT_BYTES = 63791
DELTA_CALLS = ["02102026", "03102026", "04102026", "05102026"]
PAYLOAD_ROW_VOLUME = 412554239  # NSE ind_close_all volume for 2026-10-05 (fixture yfinance: 436700)
SNAPSHOT_STAGE_ERROR = "snapshot: bars: store has 1 rows; window 5 needs >= 20"
UNKNOWN_SYMBOL_ERROR = "refresh: unknown symbol: '__NOPE__' (known: ['^NSEI'])"

# Gate 2 §0 freeze 3
REPORT_KEYS = ["symbol", "end_date", "ok", "refresh", "snapshot", "error"]
REFRESH_KEYS = {"symbol", "rows", "first_date", "last_date", "parquet_path"}
SNAPSHOT_KEYS = {"symbol", "path", "bytes", "last_date", "windows", "k"}


@pytest.fixture(autouse=True)
def guards():
    """Gate 2 §0: fixture drift OR prior-eval edits invalidate this eval."""
    for path, sha in GUARD_SHAS.items():
        d = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert d == sha, f"frozen file edited: {path} ({d})"
    yield


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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


# --- Section 1: success paths ---


def test_t001_noop_run_contract(tmp_path):
    seed_master(tmp_path)
    calls, get = recorder()
    rep = run(tmp_path, get)
    assert list(rep) == REPORT_KEYS
    assert rep["symbol"] == "^NSEI"
    assert rep["end_date"] == "2026-10-05"
    assert rep["ok"] is True
    assert rep["error"] is None
    ref = rep["refresh"]
    assert set(ref) == REFRESH_KEYS
    assert ref["symbol"] == "^NSEI"
    assert ref["rows"] == 4673
    assert ref["first_date"] == "2007-09-17"
    assert ref["last_date"] == "2026-10-05"
    snap = rep["snapshot"]
    assert set(snap) == SNAPSHOT_KEYS
    assert snap["bytes"] == SNAPSHOT_BYTES
    assert snap["last_date"] == "2026-10-05"
    assert snap["windows"] == [5, 10, 15, 30, 60]
    assert snap["k"] == 10
    assert sha256_file(snap["path"]) == SNAPSHOT_SHA256
    assert calls == []


def test_t002_byte_determinism(tmp_path):
    seed_master(tmp_path)
    calls, get = recorder()
    rep1 = run(tmp_path, get)
    rep2 = run(tmp_path, get)
    assert rep1["ok"] is True
    assert rep2 == rep1
    assert sha256_file(rep2["snapshot"]["path"]) == SNAPSHOT_SHA256
    assert rep2["snapshot"]["bytes"] == SNAPSHOT_BYTES
    assert calls == []


def test_t003_delta_run(tmp_path):
    seed_master(tmp_path, fixture_df().iloc[:-1])
    calls = []

    def get(url):
        calls.append(url.rsplit("_", 1)[-1].removesuffix(".csv"))
        return PAYLOAD.read_bytes() if url.endswith("05102026.csv") else None

    rep = run(tmp_path, get)
    assert rep["ok"] is True
    assert calls == DELTA_CALLS
    assert rep["refresh"]["rows"] == 4673
    assert rep["refresh"]["last_date"] == "2026-10-05"
    back = pd.read_parquet(tmp_path / "parquet" / "^NSEI.parquet")
    ref_dir = tmp_path / "ref"
    build_store(FIXTURE, "^NSEI", ref_dir)
    ref = pd.read_parquet(ref_dir / "^NSEI.parquet")
    assert len(back) == 4673
    for col in ["date", "open", "high", "low", "close"]:
        assert back[col].equals(ref[col]), col
    vol_diff = list(back.index[back["volume"] != ref["volume"]])
    assert len(vol_diff) == 1  # 0002 §5: NSE vs yfinance volume drift, one cell
    i = vol_diff[0]
    assert str(back.loc[i, "date"]) == "2026-10-05"
    assert int(back.loc[i, "volume"]) == PAYLOAD_ROW_VOLUME
    mask = back.index != i
    assert (back.loc[mask, "volume"] == ref.loc[mask, "volume"]).all()
    assert sha256_file(rep["snapshot"]["path"]) == SNAPSHOT_SHA256


# --- Section 2: failure paths (stage-honest reporting) ---


def test_t004_refresh_failure_preserves_outputs(tmp_path):
    seed_master(tmp_path)
    first = run(tmp_path, lambda url: None)
    assert first["ok"] is True
    assert sha256_file(first["snapshot"]["path"]) == SNAPSHOT_SHA256
    store_p = tmp_path / "parquet" / "^NSEI.parquet"
    store_bytes = store_p.read_bytes()
    seed_master(tmp_path, fixture_df().iloc[:-1])
    calls = []

    def boom(url):
        calls.append(url)
        raise OSError("boom")

    rep = run(tmp_path, boom)
    assert rep["ok"] is False
    assert rep["refresh"] is None
    assert rep["snapshot"] is None
    assert rep["error"].startswith("refresh: ")
    assert "boom" in rep["error"]
    assert sha256_file(first["snapshot"]["path"]) == SNAPSHOT_SHA256  # prior pin untouched
    assert store_p.read_bytes() == store_bytes  # fetch raised before any store rewrite
    assert len(calls) == 1
    assert calls[0].endswith("02102026.csv")


def test_t005_snapshot_stage_failure(tmp_path):
    seed_master(tmp_path)
    first = run(tmp_path, lambda url: None)
    assert first["ok"] is True
    assert sha256_file(first["snapshot"]["path"]) == SNAPSHOT_SHA256
    one = fetch_eod_index("Nifty 50", "2026-10-05", "2026-10-05",
                          get=lambda url: PAYLOAD.read_bytes())
    seed_master(tmp_path, one)
    rep = run(tmp_path, lambda url: None)
    assert rep["ok"] is False
    ref = rep["refresh"]  # the refresh stage *succeeded*
    assert set(ref) == REFRESH_KEYS
    assert ref["rows"] == 1
    assert ref["first_date"] == ref["last_date"] == "2026-10-05"
    assert rep["snapshot"] is None
    assert rep["error"] == SNAPSHOT_STAGE_ERROR
    assert (tmp_path / "parquet" / "^NSEI.parquet").exists()  # rewritten store persists
    assert sha256_file(first["snapshot"]["path"]) == SNAPSHOT_SHA256  # prior pin untouched


def test_t006_unknown_symbol_no_network(tmp_path):
    seed_master(tmp_path)
    calls, get = recorder()
    rep = run_eod_job("__NOPE__", "2007-09-17", "2026-10-05",
                      tmp_path / "parquet", tmp_path / "api", get=get)
    assert rep["ok"] is False
    assert rep["refresh"] is None
    assert rep["snapshot"] is None
    assert rep["error"] == UNKNOWN_SYMBOL_ERROR
    assert calls == []


# --- Section 3: CLI ---


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "src.eod_job", *args],
        capture_output=True, text=True, cwd=REPO_ROOT)


def test_t007_cli_success(tmp_path):
    seed_master(tmp_path)
    proc = _cli("--parquet-dir", str(tmp_path / "parquet"),
                "--snapshot-dir", str(tmp_path / "api"),
                "--end-date", "2026-10-05")
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.strip().splitlines()
    assert len(lines) == 1  # exactly one JSON line (§0 freeze 4)
    rep = json.loads(lines[0])
    assert list(rep) == REPORT_KEYS
    assert rep["ok"] is True
    assert sha256_file(rep["snapshot"]["path"]) == SNAPSHOT_SHA256


def test_t008_cli_failure_help_and_crontab_doc(tmp_path):
    seed_master(tmp_path)
    proc = _cli("--symbol", "__NOPE__",
                "--parquet-dir", str(tmp_path / "parquet"),
                "--snapshot-dir", str(tmp_path / "api"),
                "--end-date", "2026-10-05")
    assert proc.returncode == 1
    lines = proc.stdout.strip().splitlines()
    assert len(lines) == 1
    rep = json.loads(lines[0])
    assert rep["ok"] is False
    assert rep["error"].startswith("refresh: ")
    help_proc = _cli("--help")
    assert help_proc.returncode == 0
    src = (REPO_ROOT / "src" / "eod_job.py").read_text(encoding="utf-8")
    assert "30 17 * * 1-5" in src  # Gate 1 §2.3 documented crontab line


# --- Section 4: hygiene & performance ---


def test_t009_hermetic_and_readonly(tmp_path, monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", boom)
    seed_master(tmp_path)
    rep = run(tmp_path, lambda url: None)
    assert rep["ok"] is True
    back = pd.read_parquet(tmp_path / "parquet" / "^NSEI.parquet")
    ref_dir = tmp_path / "ref"
    build_store(FIXTURE, "^NSEI", ref_dir)
    ref = pd.read_parquet(ref_dir / "^NSEI.parquet")
    pd.testing.assert_frame_equal(back, ref)  # 0001: content, not bytes, is the contract
    assert sha256_file(rep["snapshot"]["path"]) == SNAPSHOT_SHA256


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
    assert best <= 3.0, f"no-op run too slow: {best:.2f}s (probe 0.64s)"
