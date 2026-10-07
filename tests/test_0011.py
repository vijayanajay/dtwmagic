"""Frozen eval for spec 0011 — Gate 2: specs/tests/0011-ghost-overlay-frontend.md.

IMMUTABLE: T-001..T-010 are transcribed from the frozen test spec (10 scenarios +
six §0 interface freezes, approved 2026-10-07; pins probe-verified PROBE_EXIT=0).
Never edit to make failing code pass; fix data/static/index.html instead.
"""
import hashlib
import json
import re
import socket
from pathlib import Path

import pytest

from src.ohlcv_store import build_store
from src.snapshot_v2 import build_snapshot_v2

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "data" / "static" / "index.html"
GITIGNORE = REPO / ".gitignore"
FIXTURE = Path("tests/fixtures/nifty50_daily_ohlcv.csv")

# §0 freeze 1: fixtures + all ten prior evals at post-R1/R2 digests.
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
    "tests/test_0008.py":
        "bafc6d0dbe231fbfe23a1576d1a92caf78abc322e603dd020e87b745c412a7fe",  # post-R2
    "tests/test_0009.py": "f693240cdd5d784f998b249073b37c44a9fc12ef884da5d52bd19c81efbc7ec5",
    "tests/test_0010.py":
        "fb3338d3a17cd5260bacb0610dead2da63bddc9db0a8fa907e61e6cfbce24d21",  # post-R1
}

# §0 freeze 6: backend untouched by this frontend-only spec.
SRC_SHAS = {
    "src/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "src/eod_fetch.py": "27e0e7e0ecc22e425bd753ada43d3a857b9204792739ee14b4b3d1e53be25be7",
    "src/eod_job.py": "3f834c5b8f8ab30ecb2fb5611f0fce1f4a40ddccaf41c13e3ae1deb56a6bc68b",
    "src/ohlcv_store.py": "e851e5f4c63550255e047977ad162a7c761ad7a98f983fc71732a6db089a37bd",
    "src/outcome_stats.py": "f522e57314cea9e941a3dae25a11b6b800e751906e6271d4bd2086f198438aea",
    "src/pattern_search.py": "d37af68b00e91b3f86ddff6676e213e1f41212cff0fecc476339d03eb3998a44",
    "src/regime.py": "39120570ee4cf89d7fe5295d6e96a6668788692b77cb2837b74d7edc73636702",
    "src/snapshot.py": "cbbf047c3016b023a973b0897ba2d01861b8164e4da6eb51b7351c1aab9ff436",
    "src/snapshot_v2.py": "1b7bca74870f12a803f3f86cb34110c50aaf5bfeceeb94f8cc42596d3d782234",
}

# §0 freeze 2: page literals (frozen before code, 0008 posture).
V2_FETCH = '"./api/v2/%5ENSEI.json"'
ANCHOR = "c0 * a.forward[i-1].close / a.close"
LEGEND = ("Historical Ghost Paths — each line replays the actual path a matched "
          "historical episode took after its match date, re-anchored from that "
          "date's close to today's close.")
PAGE_LITERALS = [
    "const GHOST_TOP = 3",
    "const GHOST_TOP_FREE = 1",
    ANCHOR,
    "function ghostSVG(",
    LEGEND,
    'const DEFAULT_WINDOW = "10"',
    "const FREE_TOP_K = 3",
    "Simple",
    "Quant",
    "Free view",
    "const STALE_DAYS = 4",
]

# §0 freeze 3: hermetic v2 payload + anchor math (probe-verified).
C0 = 22555.75
ANALOG10 = {"date": "2012-05-14", "close": 4907.8, "distance": 0.73704193241622}
GHOST_T1 = 22716.606442805332
GHOST_T5 = 22338.36400729451
GHOST_T10 = 22933.99243551082

# §0 freeze 4: compliance needles (verbatim, from 0008's frozen sets).
STAT_START = "<!-- statutory:start -->"
STAT_END = "<!-- statutory:end -->"
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
STORAGE_KEYS = {"dtwmagic_tos_accepted", "dtwmagic_view_mode", "dtwmagic_window"}

# §0 freeze 4: 0008's frozen 19-pattern forbidden scan (re.I over non-statutory).
FORBIDDEN = [
    r"\bwin rate\b", r"\baccuracy\b", r"\btarget\b", r"stop[- ]loss",
    r"\bstop level\b", r"\bexpected gain\b", r"forecast", r"\bbuy setup\b",
    r"\bbullish signal\b", r"\bpredict", r"\brecommendations?\b", r"\bbuy\b",
    r"\bsell\b", r"\bhold\b", r"\bentry\b", r"\bexit\b", r"\bcall\b",
    r"\btip\b", r"\bsignal\b",
]

# §0 freeze 5: coverage = 0008's 28 + query + candles; isolation lists.
KEY_SUBSTRINGS = [
    "schema", "bars", "last_date", "regime", "trend", "volatility", "cell",
    "p252", "windows", "analogs", "summary", "cone", "positive_frequency",
    "mae", "mfe", "horizons", "distance", "score", "forward", "close",
    "p10", "p25", "p50", "p75", "p90", "p80", "String(", "%5ENSEI.json",
    "query", "candles",
]
ABSENT = [
    "from src", "src.snapshot", "src.eod_job", "src.ohlcv", "<script src",
    "@import", 'href="http', 'src="http', 'url(http',
]
COMPONENTS = [
    "function header(", "function selector(", "function summaryCard(",
    "function nullPanel(", "function coneSVG(", "function summaryTable(",
    "function matrix(", "function spark(", "function matches(",
    "function render(", "function bind(", "function initTos(",
]


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
    pat = re.escape(STAT_START) + r".*?" + re.escape(STAT_END)
    return [m.span() for m in re.finditer(pat, text, re.S)]


def in_statutory(text, needle):
    i = text.find(needle)
    assert i >= 0, f"verbatim copy missing: {needle[:70]!r}"
    inside = any(a <= i < b for a, b in statutory_spans(text))
    return inside, f"copy outside statutory markers: {needle[:70]!r}"


def strip_statutory(text):
    pat = re.escape(STAT_START) + r".*?" + re.escape(STAT_END)
    return re.sub(pat, "", text, flags=re.S)


@pytest.fixture(scope="session")
def payload(tmp_path_factory):
    """Hermetic v2 document from the committed fixture (Gate 2 freeze 3)."""
    out = tmp_path_factory.mktemp("contract0011")
    build_store(FIXTURE, "^NSEI", out / "store")
    man = build_snapshot_v2("^NSEI", out / "store", out / "api")
    return json.loads(Path(man["path"]).read_text(encoding="utf-8"))


# --- Section 1: seam & component ---

def test_t001_fetch_seam_and_coverage():
    text = page_text()
    assert V2_FETCH in text, "v2 fetch literal missing"
    assert "api/v1" not in text, "page still references the v1 seam"
    missing = [k for k in KEY_SUBSTRINGS if k not in text]
    assert not missing, f"page does not reference contract keys: {missing}"


def test_t002_ghost_literals_and_structure():
    text = page_text()
    for lit in PAGE_LITERALS:
        assert lit in text, f"missing behavioral literal: {lit!r}"


def test_t003_hermetic_v2_payload(payload):
    assert list(payload) == [
        "schema", "symbol", "bars", "last_date", "regime", "windows", "query"]
    q = payload["query"]
    assert q["L"] == 60 and len(q["candles"]) == 60
    assert q["candles"][59] == {
        "date": "2026-10-05", "open": 22532.4, "high": 22621.8,
        "low": 22397.1, "close": C0}
    a = payload["windows"]["10"]["analogs"][0]
    assert a["date"] == ANALOG10["date"]
    assert a["close"] == ANALOG10["close"]
    assert a["distance"] == ANALOG10["distance"]


def test_t004_anchor_math_and_formula(payload):
    a = payload["windows"]["10"]["analogs"][0]
    ghosts = [C0 * f["close"] / a["close"] for f in a["forward"]]
    assert ghosts[0] == GHOST_T1
    assert ghosts[4] == GHOST_T5
    assert ghosts[9] == GHOST_T10
    assert ANCHOR in page_text(), "page formula differs from the pinned math"


# --- Section 2: compliance survival ---

def test_t005_compliance_layer_survives():
    text = page_text()
    for needle in FOOTER_NEEDLES:
        ok, msg = in_statutory(text, needle)
        assert ok, msg
    assert text.count('type="checkbox"') == 2, "exactly two ToS checkboxes"
    for needle in CHECKBOX_NEEDLES:
        ok, msg = in_statutory(text, needle)
        assert ok, msg
    for needle in TOOLTIP_NEEDLES:
        ok, msg = in_statutory(text, needle)
        assert ok, msg
    for label in LABEL_NEEDLES:
        assert label in text, f"mandatory label missing: {label}"
    ok, msg = in_statutory(text, FOOTNOTE_NEEDLE)
    assert ok, msg
    assert GATE1_COPY in text
    assert text.count("data-metric=") >= 3
    assert "dtwmagic_tos_accepted" in text
    stripped = strip_statutory(text)
    hits = [(p, m.group(0)) for p in FORBIDDEN
            for m in [re.search(p, stripped, re.I)] if m]
    assert not hits, f"banned phrasing outside statutory regions: {hits}"
    keys = set(re.findall(r"dtwmagic_[A-Za-z0-9_]+", text))
    assert keys == STORAGE_KEYS, f"localStorage keys drifted: {keys}"


def test_t006_budget_repo_boundary_selfcontained():
    text = page_text()
    assert len(PAGE.read_bytes()) < 100_000, "BRD 7.1 bundle budget exceeded"
    gi = GITIGNORE.read_text(encoding="utf-8").replace("\r\n", "\n")
    lines = {ln.strip() for ln in gi.splitlines()}
    for ln in ("/data/parquet/", "/data/eod/", "/data/static/api/"):
        assert ln in lines, f"missing gitignore line {ln}"
    assert "/data/" not in lines, "broad /data/ ignore still present"
    found = [s for s in ABSENT if s in text]
    assert not found, f"isolation/self-containment violated: {found}"


def test_t007_ghost_copy_and_label_driver():
    text = page_text()
    assert LEGEND in text, "legend copy missing or altered"
    assert "a.date" in text, "ghost date label not driven by a.date"
    assert FOOTNOTE_NEEDLE in text


# --- Section 3: revision round & coexistence ---

def test_t008_r_round_integrity():
    t8 = (REPO / "tests" / "test_0008.py").read_text(encoding="utf-8")
    assert '"./api/v2/%5ENSEI.json"' in t8
    assert '"./api/v1/%5ENSEI.json"' not in t8
    t10 = (REPO / "tests" / "test_0010.py").read_text(encoding="utf-8")
    assert "bafc6d0dbe231fbfe23a1576d1a92caf78abc322e603dd020e87b745c412a7fe" in t10
    assert 'assert "./api/v2/" in page' in t10
    assert 'assert "api/v1" not in page' in t10
    s8 = (REPO / "specs" / "tests" / "0008-phase1-dashboard.md").read_text(
        encoding="utf-8")
    assert "R2 (2026-10-07" in s8
    s10 = (REPO / "specs" / "tests" / "0010-v2-query-block.md").read_text(
        encoding="utf-8")
    assert "R1 (2026-10-07" in s10


def test_t009_component_coexistence():
    text = page_text()
    for marker in COMPONENTS:
        assert marker in text, f"component entry point missing: {marker}"
    assert "<footer" in text
    assert "tos-modal" in text
    assert "const STALE_DAYS = 4" in text
    assert "last_date" in text


def test_t010_backend_untouched_and_hermetic(payload, monkeypatch, tmp_path):
    def boom(*_a, **_k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", boom)
    for path, sha in SRC_SHAS.items():
        d = hashlib.sha256((REPO / path).read_bytes()).hexdigest()
        assert d == sha, f"backend file changed: {path} ({d})"
    # payload fixture built hermetically above; store bytes read-only check
    store = tmp_path / "store"
    build_store(FIXTURE, "^NSEI", store)
    before = hashlib.sha256((store / "^NSEI.parquet").read_bytes()).hexdigest()
    build_snapshot_v2("^NSEI", store, tmp_path / "api")
    after = hashlib.sha256((store / "^NSEI.parquet").read_bytes()).hexdigest()
    assert before == after, "store mutated by the builder"
