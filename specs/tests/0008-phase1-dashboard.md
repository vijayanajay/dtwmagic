# Gate 2 — Frozen Test Spec `0008-phase1-dashboard`

**Status:** `FROZEN — approved by user 2026-10-07 ("approved"); 10 scenarios + seven §0
interface freezes; every pin probe-verified (final PROBE_EXIT=0, 2026-10-07) before
authoring. This file is IMMUTABLE; it may never be edited to make failing code pass.
Only a user-directed revision may change it. (R1 applied 2026-10-07: tooltip
attribute `data-tip` → `data-metric` — see Revision log.)`
**Date:** 2026-10-07
**Maps 1-to-1 to:** `specs/requirements/0008-phase1-dashboard.md` (Gate 1, APPROVED
2026-10-07)
**Test file (Gate 3):** `tests/test_0008.py` (pytest, static-contract lint — no JS
runtime, per Gate 1 §2.6)
**Deliverable under test:** `data/static/index.html` (the page), consumed contract
`dtwmagic.api.v1`.

---

## 0. Interface Freezes (clarifying details of the approved Gate 1)

1. **File boundary (Gate 3 creates/edits exactly):** `data/static/index.html` (new,
   single self-contained file), `.gitignore` (narrowed per Gate 1 §2.1), and
   `tests/test_0008.py`. Sources of specs 0001–0007 and 0009 are untouched; the
   untracked prototype `data/static/api/v1/preview.html` is left in place (it is
   ignored output, not a deliverable, and nothing asserts on it). The eval sha-pins
   all nine prior test files + both fixtures (autouse):
   `test_0001 804a090d…99a09c`, `test_0002 9a5ba0cb…f1cfc`, `test_0003 0b3d1c56…90c06d`,
   `test_0004 78d61847…94730`, `test_0005 a3769489…94213`,
   `test_0006 08f764b5797ca08bd99939ea7c673da47e152a2ad9da1efb592b07a994c05c35`,
   `test_0007 e6295aa53c5aa300ade0ba64ec32b10335a2730fab0ea80ac6c5a742ba79867c`,
   `test_0009 f693240cdd5d784f998b249073b37c44a9fc12ef884da5d52bd19c81efbc7ec5`;
   `nifty50_daily_ohlcv.csv 25657e31…f7a93e`, `ind_close_all_20261005.csv f0b8004e…bc9ba`
   (full digests in the test file).
2. **Statutory regions (scan exemption mechanism):** every safe-harbor copy block —
   the §8.2A footer, the §8.2B modal, the §8.2C `TOOLTIPS` object literal, and the
   §6.3 footnote — is wrapped in HTML comment pairs exactly
   `<!-- statutory:start -->` … `<!-- statutory:end -->` (one or more pairs).
   The T-007 scan strips every span between such pairs (DOTALL) before searching;
   all other text in `index.html` is scanned. Tooltip *definitions* live in one
   `const TOOLTIPS = {…}` object inside statutory markers; headers reference them via
   `data-metric="<key>"` (R1: renamed from `data-tip`, which would itself trip
   freeze 4's `\btip\b` scan) — so no banned wording sits outside a marked region.
3. **Verbatim copy (probe-verified: every BRD-sourced needle exists in `BRD.md`):**
   - **Footer §8.2A** must contain, verbatim:
     `is an independent financial technology and data analytics platform designed strictly for educational, research, and historical pattern search purposes`;
     `We are NOT registered with SEBI as an Investment Adviser (RIA) or Research Analyst (RA)`;
     `All trading and investment decisions are the sole responsibility of the user`;
     `Securities trading involves substantial risk of financial loss`.
   - **ToS modal §8.2B** — both checkbox labels verbatim:
     `is a technical search engine for historical chart data and does not offer trading advice, stock recommendations, or price predictions`;
     `I understand that historical pattern occurrences are purely descriptive and do not guarantee future performance`.
   - **Tooltips §8.2C** — six values verbatim (exact BRD text):
     1 `Maximum Adverse Excursion (MAE) reflects the deepest historical drawdown observed in this matched historical sample between T+0 and T+10. This is historical empirical data, NOT a recommended stop-loss.`
     2 `Maximum Favorable Excursion (MFE) reflects the peak historical gain reached in this matched historical sample. This is historical empirical data, NOT a target price.`
     3 `Displays the historical proportion of matched episodes where price closed positive at horizon T+H. This represents past sample frequency, NOT a future win probability or predictive indicator.`
     4 `The 50th percentile (middle) historical return of the matched sample. Half of past matched episodes finished higher, and half finished lower. NOT an expected or forecasted return.`
     5 `The outer statistical boundary encompassing 80% of matched historical episodes. Represents the observed historical dispersion of past moves.`
     6 `Trend and volatility classification at the time of the pattern. Past matches are strictly filtered to those sharing the exact same regime weather.`
   - **Labels:** `Historical Sample Positive Frequency`, `Historical Median Forward
     Return`, `HISTORICAL REGIME` (BRD §6.2.3/§8.2D); footnote prefix
     `Descriptive historical observations only` (BRD §6.3).
   - **Gate-1-worded copy** (source: requirement spec §2.5, probe-verified there):
     `Insufficient historical sample`.
4. **Forbidden-word scan (frozen list, `re.IGNORECASE`, over non-statutory text):**
   `\bwin rate\b`, `\baccuracy\b`, `\btarget\b`, `stop[- ]loss`, `\bstop level\b`,
   `\bexpected gain\b`, `forecast`, `\bbuy setup\b`, `\bbullish signal\b`, `\bpredict`,
   `\brecommendations?\b`, `\bbuy\b`, `\bsell\b`, `\bhold\b`, `\bentry\b`, `\bexit\b`,
   `\bcall\b`, `\btip\b`, `\bsignal\b` — probe-verified: every pattern matches its
   canonical banned sample, and `tooltip`/`callback`/`household` do **not** trip
   `\btip\b`/`\bcall\b`/`\bhold\b`/`\bsell\b`.
5. **Contract keys the page must reference (probe P1 = the production surface):**
   frozen substring list — `schema`, `bars`, `last_date`, `regime`, `trend`,
   `volatility`, `cell`, `p252`, `windows`, `analogs`, `summary`, `cone`,
   `positive_frequency`, `mae`, `mfe`, `horizons`, `distance`, `score`, `forward`,
   `close`, `p10`, `p25`, `p50`, `p75`, `p90`, `p80`, `String(` (horizon-key
   coercion), `%5ENSEI.json`. Hermetic payload pin (fixture store via 0007's builder):
   top keys `["schema","symbol","bars","last_date","regime","windows"]`;
   `windows` keys `["5","10","15","30","60"]`; block `["L","k","analogs","summary"]`;
   summary `["n","horizons","cone","positive_frequency","mae","mfe"]`;
   `cone[h] == ["p10","p25","p50","p75","p90"]`; `mae["5"] == ["p80"]`;
   `mfe["5"] == ["p50"]`; positive_frequency keys `"1"…"10"` (strings);
   `horizons == [1..10]` (ints); `n == 10`; analog
   `["date","distance","score","close","forward"]`; forward row
   `["date","open","high","low","close"]`; `bars == 4673`, `last_date == "2026-10-05"`.
6. **Behavioral literals frozen (static, probe-backed):** fetch
   `./api/v1/%5ENSEI.json`; `const DEFAULT_WINDOW = "10"`; `const FREE_TOP_K = 3`;
   `const STALE_DAYS = 4`; `localStorage` keys exactly `dtwmagic_tos_accepted`,
   `dtwmagic_view_mode`, `dtwmagic_window`; mode labels `Simple` / `Quant` and
   `Free view`; ToS modal id `tos-modal`; footer element `<footer`; freshness badge
   class/word `stale`.
7. **Tolerances & conventions:** verbatim needles are **case-sensitive exact
   substring** matches on the file's text; the scan is regex/`IGNORECASE`;
   byte budget: `index.html` < **100_000** bytes (BRD §7.1; prototype = 9,050);
   runner `python -m pytest tests/test_0008.py` from repo root; payload fixtures are
   built hermetically via 0007's `build_snapshot` into `tmp_path` (fixture store +
   0007's slice pattern) — **no network, no reads of `data/`**; scan targets the file
   as text (no HTML parser, no JS execution).

**Eval conventions:**
- Autouse guard: the §0 freeze-1 ten-file sha table (nine prior evals + two fixtures
  — `nifty50` and `ind_close_all` counts as the two).
- Gate 3 additionally performs a **manual render pass** (serve `python -m http.server
  -d data/static`, open the page, screenshot the eight §2.3 components, the ToS gate,
  and the null-summary panel) — human-verified, recorded in the Gate 4 record; it is
  not an automated scenario here because Gate 1 §2.6 froze "no JS runtime".
- Full suite expectation at Green: **128 passed** (118 existing + 10 new), prior evals
  unmodified.

---

## 1. File, Budget & Repo Boundary

**T-001 — Deliverable exists, budget holds, `.gitignore` carve-out correct**
- *Given* the repo root,
- *When* `data/static/index.html` and `.gitignore` are inspected,
- *Then* `index.html` exists and is **< 100_000 bytes**; `.gitignore` contains the
  exact lines `/data/parquet/`, `/data/eod/`, `/data/static/api/` and **does not**
  contain a line exactly `/data/` (Gate 1 §2.1/#3); `data/static/` contains the
  authored page and the ignored `api/` output tree.

---

## 2. Contract Consumption (production ↔ page)

**T-002 — Key coverage: the page references every key the contract produces**
- *Given* a hermetic fixture payload built via 0007's `build_snapshot` in `tmp_path`
  (structure matching §0 freeze 5 exactly — all eight key-order lists and value pins),
- *When* `index.html`'s text is searched,
- *Then* every frozen substring in §0 freeze 5 (28 entries incl. `%5ENSEI.json` and
  `String(`) is present; and the payload's horizon keys are the strings `"1"…"10"`
  while `horizons` holds ints `[1..10]` (the page must coerce, hence `String(`).

**T-003 — Null-summary contract state maps to the insufficient-sample panel**
- *Given* a hermetic **slice** payload (fixture rows `date ≤ 2009-06-04`, 416 bars —
  0007's slice pattern) whose five windows all have `analogs == []` and
  `summary is None` (probe-verified),
- *When* the payload and `index.html` are inspected,
- *Then* all five windows are null in the payload (the state exists) and the page
  contains `Insufficient historical sample` plus the null guard reference
  (`summary` check) — the panel is wired, not an empty card.

---

## 3. Compliance Layer (§8.2 — verbatim)

**T-004 — Persistent footer (§8.2A)**
- *Given* `index.html`,
- *When* the footer region is inspected,
- *Then* a `<footer` element exists, it is wrapped in statutory markers, and it
  contains all four §0 freeze-3 footer needles verbatim.

**T-005 — ToS acceptance modal (§8.2B)**
- *Given* `index.html`,
- *When* the modal region is inspected,
- *Then* `tos-modal` exists, wrapped in statutory markers, containing **two**
  `type="checkbox"` inputs whose labels include both §0 freeze-3 checkbox needles
  verbatim, and the localStorage key `dtwmagic_tos_accepted` appears in the gating
  logic.

**T-006 — Tooltips, labels, footnote (§8.2C/§8.2D/§6.2.3/§6.3)**
- *Given* `index.html`,
- *When* the text is searched,
- *Then* all six §0 freeze-3 tooltip texts appear verbatim (inside a statutory-marked
  `TOOLTIPS` object); the labels `Historical Sample Positive Frequency` and
  `Historical Median Forward Return` appear; `HISTORICAL REGIME` appears; the §6.3
  footnote prefix `Descriptive historical observations only` appears inside statutory   markers; and at least three `data-metric=` references point at tooltip keys (R1).

**T-007 — Forbidden-word scan outside statutory regions**
- *Given* `index.html` with every `<!-- statutory:start -->…<!-- statutory:end -->`
  span removed (DOTALL),
- *When* the §0 freeze-4 nineteen patterns are searched (`re.IGNORECASE`),
- *Then* **zero** matches occur anywhere in the remainder (page copy, headings,
  comments, JS strings, derived executive-summary bullets — all §8.2D-clean).

---

## 4. Interaction Surface (static-polarity checks)

**T-008 — Toggles, defaults, persistence**
- *Given* `index.html`,
- *When* the interaction literals are searched,
- *Then* `const DEFAULT_WINDOW = "10"`, `const FREE_TOP_K = 3`, the three localStorage
  keys of §0 freeze 6 (exactly: no fourth `dtwmagic_` key), the labels `Simple`,
  `Quant`, and `Free view` are present, and the fetch literal
  `./api/v1/%5ENSEI.json` appears.

**T-009 — Isolation & self-containment (BRD §4.4)**
- *Given* `index.html`,
- *When* the text is searched,
- *Then* **none** of the following appear: `from src`, `src.snapshot`, `src.eod_job`,
  `src.ohlcv`, `<script src`, `@import`, `href="http`, `src="http`, `url(http` —
  the page imports no backend Python and loads no external resource (renders
  offline from the committed file + local payload).

**T-010 — Freshness badge**
- *Given* `index.html`,
- *When* the freshness logic is searched,
- *Then* `const STALE_DAYS = 4` appears, the `last_date` field is read for the badge,
  and the `stale` marker appears (Gate 1 §2.3.1 / §6 #7).

---

## 5. Coverage Map (requirement §2 → scenarios)

| Requirement rule | Scenarios |
|---|---|
| Layout/serving/.gitignore carve-out (§2.1) | T-001 |
| Vanilla stack, <100 KB budget (§2.2) | T-001 |
| Context bar / selector / summary / cone / matrix / matches / toggles (§2.3) | T-002, T-008, T-010 (+ manual render pass) |
| Free view truncation = UI's job, default full (§2.3.8, §6 #5) | T-008 (`FREE_TOP_K = 3`, `DEFAULT_WINDOW = "10"`) |
| Compliance layer verbatim (§2.4) | T-004, T-005, T-006 |
| Forbidden §8.2D phrasing (§2.4) | T-007 |
| Edge & honesty states (§2.5) | T-003, T-010 |
| Static contract lint, no JS runtime, hermetic (§2.6) | T-002, T-003 (0007-built payloads) |
| No new dependency (§2.7) | — (nothing to approve) |
| Zero backend changes; isolation (§3, §4) | §0 freeze 1 (sha guard), T-009 |
| Current-window gap deferred (§6 #8) | — (absence: no `query` references required; nothing in the page may imply live prices — covered by T-007's copy scan + manual pass) |
| Full suite stays green (§2.6) | §0 freeze 1 (autouse), runner convention |

---

## 6. Gate 2 Sign-Off

- [x] **User approves** this test spec **including the seven §0 interface freezes**
      → it is **IMMUTABLE**; Gate 3 (TDD: Red → Green — build `data/static/index.html`
      + narrow `.gitignore` + write `tests/test_0008.py`; no other file) may begin.
      **(Approved 2026-10-07)**

**STOP:** No `data/static/index.html` may be written until the box above is checked
by the user.

**Revision log:**

- **R1 (2026-10-07, user-directed):** §0 freeze 2 + T-006 rename the tooltip
  attribute `data-tip="<key>"` → `data-metric="<key>"`. Reason: the frozen
  `\btip\b` scan pattern (freeze 4) matches the mandated literal `data-tip`
  (hyphen = non-word boundary), so T-007 could never pass as written — a
  self-contradiction found at the Gate 3 pre-flight, before any code. Both
  enforcement goals (tip-ban + tooltip mechanism) are preserved; no other freeze,
  needle, pattern, or scenario changed. User chose this option over dropping the
  pattern or exempting the literal (asked 2026-10-07).

*(Authored after final PROBE_EXIT=0 (2026-10-07): payload
structure pins, slice null-state, 19 regex positive/negative controls, 16 BRD verbatim
needles, Gate-1 copy needle, `.gitignore` baseline, prototype byte budget. Probe round 1
mis-sourced the `Insufficient historical sample` needle as BRD text (it is Gate-1
wording) and lacked a failing exit code — both corrected before freeze, recorded here
for honesty. Any future change must be a user-directed revision recorded here, like
0003 R1/R2, 0005 R1.)*
