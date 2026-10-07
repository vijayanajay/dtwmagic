"""Frozen eval for spec 0008 — Gate 2: specs/tests/0008-phase1-dashboard.md (R1).

IMMUTABLE: T-001..T-010 are transcribed from the frozen test spec (10 scenarios +
seven §0 interface freezes, approved 2026-10-07; revision R1 renamed the tooltip
attribute data-tip -> data-metric so the mandated literal cannot trip freeze 4's
\\btip\\b scan). Never edit to make failing code pass; fix data/static/index.html
instead.
"""
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from src.ohlcv_store import build_store
from src.snapshot import build_snapshot

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "data" / "static" / "index.html"
GITIGNORE = REPO / ".gitignore"
FIXTURE = Path("tests/fixtures/nifty50_daily_ohlcv.csv")

# §0 freeze 1: zero-edits guard over all prior evals + both fixtures (full digests).
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
    "tests/test_0009.py": "f693240cdd5d784f998b249073b37c44a9fc12ef884da5d52bd19c81efbc7ec5",
}

# §0 freeze 3: verbatim copy (probe-verified against BRD.md / the Gate 1 spec).
FOOTER_NEEDLES = [
    "is an independent financial technology and data analytics platform designed "
    "strictly for educational, research, and historical pattern search purposes",
    "We are NOT registered with SEBI as an Investment Adviser (RIA) or Research Analyst (RA)",
    "All trading and investment decisions are the sole responsibility of the user",
    "Securities trading involves substantial risk of financial loss",
]
CHECKBOX_NEEDLES = [
    "is a technical search engine for historical chart data and does not offer "
    "trading advice, stock recommendations, or price predictions",
    "I understand that historical pattern occurrences are purely descriptive and "
    "do not guarantee future performance",
]
TOOLTIP_NEEDLES = [
    "Maximum Adverse Excursion (MAE) reflects the deepest historical drawdown "
    "observed in this matched historical sample between T+0 and T+10. This is "
    "historical empirical data, NOT a recommended stop-loss.",
    "Maximum Favorable Excursion (MFE) reflects the peak historical gain reached "
    "in this matched historical sample. This is historical empirical data, NOT a "
    "target price.",
    "Displays the historical proportion of matched episodes where price closed "
    "positive at horizon T+H. This represents past sample frequency, NOT a future "
    "win probability or predictive indicator.",
    "The 50th percentile (middle) historical return of the matched sample. Half of "
    "past matched episodes finished higher, and half finished lower. NOT an "
    "expected or forecasted return.",
    "The outer statistical boundary encompassing 80% of matched historical "
    "episodes. Represents the observed historical dispersion of past moves.",
    "Trend and volatility classification at the time of the pattern. Past matches "
    "are strictly filtered to those sharing the exact same regime weather.",
]
LABEL_NEEDLES = [
    "Historical Sample Positive Frequency",
    "Historical Median Forward Return",
    "HISTORICAL REGIME",
]
FOOTNOTE_NEEDLE = "Descriptive historical observations only"
GATE1_COPY = "Insufficient historical sample"

# §0 freeze 4: forbidden-word scan (frozen order; re.IGNORECASE in T-007).
FORBIDDEN = [
    r"\bwin rate\b", r"\baccuracy\b", r"\btarget\b", r"stop[- ]loss",
    r"\bstop level\b", r"\bexpected gain\b", r"forecast", r"\bbuy setup\b",
    r"\bbullish signal\b", r"\bpredict", r"\brecommendations?\b", r"\bbuy\b",
    r"\bsell\b", r"\bhold\b", r"\bentry\b", r"\bexit\b", r"\bcall\b",
    r"\btip\b", r"\bsignal\b",
]

# §0 freeze 5: contract keys the page must reference (28) + payload pins.
KEY_SUBSTRINGS = [
    "schema", "bars", "last_date", "regime", "trend", "volatility", "cell",
    "p252", "windows", "analogs", "summary", "cone", "positive_frequency",
    "mae", "mfe", "horizons", "distance", "score", "forward", "close",
    "p10", "p25", "p50", "p75", "p90", "p80", "String(", "%5ENSEI.json",
]

# §0 freeze 6: behavioral literals.
LITERALS = [
    'const DEFAULT_WINDOW = "10"',
    "const FREE_TOP_K = 3",
    "Simple",
    "Quant",
    "Free view",
    "./api/v1/%5ENSEI.json",
]
STORAGE_KEYS = {"dtwmagic_tos_accepted", "dtwmagic_view_mode", "dtwmagic_window"}
ABSENT = [
    "from src", "src.snapshot", "src.eod_job", "src.ohlcv", "<script src",
    "@import", 'href="http', 'src="http', 'url(http',
]

MARK_START = "<!-- statutory:start -->"
MARK_END = "<!-- statutory:end -->"


@pytest.fixture(autouse=True)
def guards():
    """§0 freeze 1: fixture drift OR prior-eval edits invalidate this eval."""
    for path, sha in GUARD_SHAS.items():
        d = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert d == sha, f"frozen file edited: {path} ({d})"
    yield


def page_text():
    assert PAGE.exists(), f"missing deliverable: {PAGE}"
    return PAGE.read_text(encoding="utf-8")


def statutory_spans(text):
    pat = re.escape(MARK_START) + r".*?" + re.escape(MARK_END)
    return [m.span() for m in re.finditer(pat, text, re.S)]


def in_statutory(text, needle):
    i = text.find(needle)
    assert i >= 0, f"verbatim copy missing: {needle[:70]!r}"
    inside = any(a <= i < b for a, b in statutory_spans(text))
    return inside, f"copy outside statutory markers: {needle[:70]!r}"


def strip_statutory(text):
    pat = re.escape(MARK_START) + r".*?" + re.escape(MARK_END)
    return re.sub(pat, "", text, flags=re.S)


@pytest.fixture(scope="session")
def fixture_payload(tmp_path_factory):
    """Hermetic v1 document from the committed fixture (0007's builder)."""
    out = tmp_path_factory.mktemp("contract0008")
    build_store(FIXTURE, "^NSEI", out / "store")
    man = build_snapshot("^NSEI", out / "store", out / "api")
    return json.loads(Path(man["path"]).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def slice_payload(tmp_path_factory):
    """Zero-pool slice document (0007's slice pattern): all summaries null."""
    out = tmp_path_factory.mktemp("slice0008")
    raw = pd.read_csv(FIXTURE, parse_dates=["date"])
    csv = out / "slice.csv"
    raw[raw["date"] <= "2009-06-04"].to_csv(csv, index=False)
    build_store(csv, "SLICE", out / "store")
    man = build_snapshot("SLICE", out / "store", out / "api")
    return json.loads(Path(man["path"]).read_text(encoding="utf-8"))


# --- Section 1: file, budget & repo boundary ---


def test_t001_file_budget_gitignore():
    text = page_text()
    assert len(PAGE.read_bytes()) < 100_000, "BRD 7.1 bundle budget exceeded"
    gi = GITIGNORE.read_text(encoding="utf-8").replace("\r\n", "\n")
    lines = {ln.strip() for ln in gi.splitlines()}
    for ln in ("/data/parquet/", "/data/eod/", "/data/static/api/"):
        assert ln in lines, f"missing gitignore line {ln}"
    assert "/data/" not in lines, "broad /data/ ignore still present (Gate 1 2.1)"


# --- Section 2: contract consumption ---


def test_t002_contract_key_coverage(fixture_payload):
    doc = fixture_payload
    assert list(doc) == ["schema", "symbol", "bars", "last_date", "regime", "windows"]
    wins = doc["windows"]
    assert list(wins) == ["5", "10", "15", "30", "60"]
    block = wins["10"]
    assert list(block) == ["L", "k", "analogs", "summary"]
    s = block["summary"]
    assert list(s) == ["n", "horizons", "cone", "positive_frequency", "mae", "mfe"]
    assert list(s["cone"]["5"]) == ["p10", "p25", "p50", "p75", "p90"]
    assert list(s["mae"]["5"]) == ["p80"]
    assert list(s["mfe"]["5"]) == ["p50"]
    assert list(s["positive_frequency"]) == [str(i) for i in range(1, 11)]
    assert s["horizons"] == list(range(1, 11))
    assert s["n"] == 10
    a = block["analogs"][0]
    assert list(a) == ["date", "distance", "score", "close", "forward"]
    assert list(a["forward"][0]) == ["date", "open", "high", "low", "close"]
    assert list(doc["regime"]) == ["trend", "volatility", "cell", "p252"]
    assert doc["bars"] == 4673
    assert doc["last_date"] == "2026-10-05"
    text = page_text()
    missing = [k for k in KEY_SUBSTRINGS if k not in text]
    assert not missing, f"page does not reference contract keys: {missing}"


def test_t003_null_summary_panel(slice_payload):
    for k in ["5", "10", "15", "30", "60"]:
        blk = slice_payload["windows"][k]
        assert blk["summary"] is None and blk["analogs"] == [], k
    text = page_text()
    assert GATE1_COPY in text, "insufficient-sample panel copy missing"
    assert ".summary" in text, "null guard on summary missing"


# --- Section 3: compliance layer (verbatim) ---


def test_t004_footer_verbatim():
    text = page_text()
    assert "<footer" in text, "persistent footer element missing"
    for needle in FOOTER_NEEDLES:
        ok, msg = in_statutory(text, needle)
        assert ok, msg


def test_t005_tos_modal():
    text = page_text()
    assert "tos-modal" in text
    assert text.count('type="checkbox"') == 2, "exactly two ToS checkboxes"
    for needle in CHECKBOX_NEEDLES:
        ok, msg = in_statutory(text, needle)
        assert ok, msg
    assert "dtwmagic_tos_accepted" in text, "ToS persistence key missing"


def test_t006_tooltips_labels_footnote():
    text = page_text()
    for needle in TOOLTIP_NEEDLES:
        ok, msg = in_statutory(text, needle)
        assert ok, msg
    for label in LABEL_NEEDLES:
        assert label in text, f"mandatory label missing: {label}"
    ok, msg = in_statutory(text, FOOTNOTE_NEEDLE)
    assert ok, msg
    assert text.count("data-metric=") >= 3, "fewer than three metric hooks (R1)"


def test_t007_forbidden_scan():
    stripped = strip_statutory(page_text())
    hits = []
    for pat in FORBIDDEN:
        m = re.search(pat, stripped, re.I)
        if m:
            hits.append((pat, m.group(0)))
    assert not hits, f"banned phrasing outside statutory regions: {hits}"


# --- Section 4: interaction surface (static polarity) ---


def test_t008_toggles_persistence():
    text = page_text()
    for lit in LITERALS:
        assert lit in text, f"missing behavioral literal: {lit!r}"
    keys = set(re.findall(r"dtwmagic_[A-Za-z0-9_]+", text))
    assert keys == STORAGE_KEYS, f"localStorage keys drifted: {keys}"


def test_t009_isolation_selfcontained():
    text = page_text()
    found = [s for s in ABSENT if s in text]
    assert not found, f"isolation/self-containment violated: {found}"


def test_t010_freshness_badge():
    text = page_text()
    assert "const STALE_DAYS = 4" in text, "staleness threshold missing"
    assert "last_date" in text, "freshness badge does not read last_date"
    assert "stale" in text, "stale marker missing"
