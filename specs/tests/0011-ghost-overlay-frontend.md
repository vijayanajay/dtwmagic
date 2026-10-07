# Gate 2 — Test Spec `0011-ghost-overlay-frontend`

**Status:** `FROZEN — approved by user 2026-10-07 ("approved"); 10 scenarios + six §0 interface freezes; all pins probe-verified (digest table + fixture v2 payload + anchor math, PROBE_EXIT=0); Gate 3 started.`
**Date:** 2026-10-07
**Maps 1-to-1 to:** `specs/requirements/0011-ghost-overlay-frontend.md` (Gate 1
approved 2026-10-07, §2.9 revision round applied same day). Eval file:
`tests/test_0011.py`.
**Probe posture:** every pin below was measured before authoring — post-R1/R2
digest table (`sha256sum`), the fixture v2 payload via `build_snapshot_v2`,
and the re-anchored ghost values (`PROBE_EXIT=0`), 2026-10-07.

**Documented interim state (expected, not a regression):** after the approved
§2.9 edits and before Gate 3's fetch switch, the suite shows **exactly 2
failures** — `test_0008::T-008` (page lacks the v2 literal) and
`test_0010::T-009` (page still on v1), 18 of 20 passing, guards green. Those
two failures *are* the fetch-switch RED; they flip green the moment
`index.html` switches. Gate 3 ends with **zero** failures suite-wide.

---

## 0. Interface Freezes (clarifying details of the approved Gate 1)

1. **Guard table (autouse):** both fixtures + **all ten prior eval files**
   `test_0001 … test_0010` at their post-R1/R2 digests (full digests in the
   test file). Distinguishing entries vs the 0010 freeze:
   - `test_0008.py` = `bafc6d0dbe231fbfe23a1576d1a92caf78abc322e603dd020e87b745c412a7fe` (**post-R2**, re-pinned)
   - `test_0010.py` = `fb3338d3a17cd5260bacb0610dead2da63bddc9db0a8fa907e61e6cfbce24d21` (**post-R1**, first time pinned by a later eval)
   - `test_0001…0007 + test_0009` unchanged from 0010's table; fixtures
     `25657e31…f7a93e` / `f0b8004e…bc9ba`.
2. **Fetch seam & behavioral literals (page, frozen before code — 0008
   posture):**
   - `"./api/v2/%5ENSEI.json"` present; **`api/v1` absent** from the page.
   - `const GHOST_TOP = 3`, `const GHOST_TOP_FREE = 1`.
   - Anchor expression verbatim: `c0 * a.forward[i-1].close / a.close`.
   - Chart entry point: `function ghostSVG(` (named beside `coneSVG`).
   - Legend copy verbatim: `Historical Ghost Paths — each line replays the
     actual path a matched historical episode took after its match date,
     re-anchored from that date's close to today's close.`
   - Existing literals survive: `const DEFAULT_WINDOW = "10"`,
     `const FREE_TOP_K = 3`, `Simple`, `Quant`, `Free view`,
     `const STALE_DAYS = 4`.
3. **Hermetic v2 payload pins (fixture store via `build_snapshot_v2`) + anchor
   math:** document keys exactly
   `["schema","symbol","bars","last_date","regime","windows","query"]`;
   `c0 = query.candles[59].close == 22555.75` (date `2026-10-05`, 60 candles);
   window `"10"` top analog `date == "2012-05-14"`, `close == 4907.8`,
   `distance == 0.73704193241622`; re-anchored ghost points **recomputed in
   the test** as `c0 * f["close"] / a["close"]` must equal:
   - T+1 `22716.606442805332`, T+5 `22338.36400729451`,
     T+10 `22933.99243551082` (exact repr, probe-verified).
4. **Compliance survival (verbatim, reused from 0008's frozen needles):**
   footer 4 needles, both ToS checkbox needles, all six §8.2C tooltip needles
   — each inside `<!-- statutory:start/end -->` spans; labels
   (`Historical Sample Positive Frequency`, `Historical Median Forward
   Return`, `HISTORICAL REGIME`); footnote `Descriptive historical
   observations only`; `Insufficient historical sample`; **exactly two**
   `type="checkbox"`; `data-metric=` ≥ 3; forbidden-word scan (0008's frozen
   19-pattern list, `re.I` over non-statutory text) clean **including the new
   ghost copy**; localStorage regex `dtwmagic_[A-Za-z0-9_]+` yields **exactly**
   `{dtwmagic_tos_accepted, dtwmagic_view_mode, dtwmagic_window}` (no new keys).
5. **Budget, coverage & isolation:** authored bytes **< 100,000**; contract-key
   coverage = 0008's frozen 28 substrings **+ `"query"` + `"candles"`** (30);
   `ABSENT` list (9 entries: `from src`, `src.snapshot`, `src.eod_job`,
   `src.ohlcv`, `<script src`, `@import`, `href="http`, `src="http`,
   `url(http`) zero hits; `.gitignore` carve-out lines present and broad
   `/data/` absent.
6. **Backend-untouched table (negative scope made enforceable):** `src/*.py`
   digests pinned — `__init__ e3b0c442…52b855`, `eod_fetch 27e0e7e0…be25be7`,
   `eod_job 3f834c5b…6bc68b`, `ohlcv_store e851e5f4…9a37bd`,
   `outcome_stats f522e573…8aea`, `pattern_search d37af68b…8a44`,
   `regime 39120570…6702`, `snapshot cbbf047c…f436`,
   `snapshot_v2 1b7bca74…2234`. Plus tolerances: strings text-exact, shas
   exact, no JS runtime; Gate 3 ends with the **full suite at zero failures**
   (the two named interim failures resolved by the switch).

---

## 1. Scenarios (T-001 … T-010)

### T-001 — fetch seam & contract coverage
- **Given** the committed page.
- **When** its text is scanned.
- **Then** `"./api/v2/%5ENSEI.json"` appears, `api/v1` appears nowhere, and
  all 30 freeze-5 key substrings (28 + `query` + `candles`) are referenced.

### T-002 — ghost component literals & structure
- **Given** the committed page.
- **When** its text is scanned.
- **Then** every freeze-2 literal is present: `const GHOST_TOP = 3`,
  `const GHOST_TOP_FREE = 1`, the verbatim anchor expression
  `c0 * a.forward[i-1].close / a.close`, `function ghostSVG(`, the verbatim
  legend copy, and the surviving 0008 literals
  (`DEFAULT_WINDOW`/`FREE_TOP_K`/`Simple`/`Quant`/`Free view`).

### T-003 — hermetic v2 payload contract
- **Given** the fixture store built in `tmp_path` (no network).
- **When** `build_snapshot_v2` writes the document.
- **Then** the 7-key order holds, `c0 == 22555.75` at
  `candles[59]` (`2026-10-05`, 60 candles), and the window-10 top analog is
  `2012-05-14 / 4907.8 / 0.73704193241622` (freeze 3).

### T-004 — anchor math recomputation
- **Given** that payload.
- **When** the test independently computes `c0 * forward.close / analog.close`
  for T+1/T+5/T+10.
- **Then** the values equal the freeze-3 exact reprs
  (`22716.606442805332`, `22338.36400729451`, `22933.99243551082`), and the
  page contains that same expression as its literal (T-002) — eval math and
  page code pinned to one formula.

### T-005 — compliance layer survives the switch
- **Given** the modified page.
- **When** 0008's full compliance battery runs (freeze 4): footer, modal,
  tooltips, labels, footnote, insufficient-sample copy inside statutory spans;
  two checkboxes; ≥3 metric hooks; forbidden scan clean over non-statutory
  text; localStorage set exactly the three frozen keys; `STALE_DAYS = 4`.
- **Then** every assertion holds — the ghost copy introduces zero violations.

### T-006 — budget, repo boundary & self-containment
- **Given** the modified page.
- **When** it is measured.
- **Then** bytes < 100,000; the `.gitignore` carve-out lines exist and broad
  `/data/` does not; the `ABSENT` list yields no hits (no Python imports, no
  external scripts/assets).

### T-007 — ghost copy & labeling intent
- **Given** the modified page.
- **When** its text is scanned.
- **Then** the freeze-2 legend copy appears verbatim, the ghost date-label is
  driven from `a.date` (the same source the matches list uses), and the
  mandatory footnote text exists — descriptive-past framing only.

### T-008 — R-round integrity (the §2.9 contract)
- **Given** the approved revision round.
- **When** the evals and their spec docs are inspected.
- **Then** `test_0008.py` carries the v2 literal and not the v1 one;
  `test_0010.py` pins `GUARD_SHAS["tests/test_0008.py"] == bafc6d0d…412a7fe`
  and asserts `"./api/v2/" in page` / `"api/v1" not in page`;
  `specs/tests/0008…` logs **R2 (2026-10-07** and
  `specs/tests/0010…` logs **R1 (2026-10-07** — the cascade stopped exactly
  where Gate 1 §2.9 said it would.

### T-009 — component coexistence (the switch didn't gut the UI)
- **Given** the modified page.
- **When** its structure is scanned.
- **Then** all eight 0008 component entry points still exist
  (`function header/selector/summaryCard/nullPanel/coneSVG/summaryTable/
  matrix/spark/matches/render/bind/initTos(`), `dtwmagic_tos_accepted` gating
  text and the stale badge logic remain, and `<footer` exists.

### T-010 — backend untouched & hermetic
- **Given** this frontend-only spec.
- **When** the `src/*.py` digests are checked (autouse, freeze 6) and the
  payload fixtures build.
- **Then** every backend file matches its pre-0011 digest, the store parquet
  bytes are unchanged after the build, and no socket was opened.

---

## 2. Traceability (Gate 1 clause → freeze/scenario)

| Gate 1 clause | Freeze / scenario |
|---|---|
| §2.1 fetch switch, single page | §0 freeze 2, T-001 |
| §2.2 chart component, layout, legend copy | §0 freeze 2, T-002, T-007 |
| §2.3 frozen anchor formula | §0 freeze 2 + 3, T-004 |
| §2.4 tier truncation constants | §0 freeze 2, T-002 |
| §2.5 edge states (existing banner/panel logic) | T-005, T-009 |
| §2.6 testing, guard over post-R1 evals | §0 freeze 1, T-008, T-010 |
| §2.8 acceptance (compliance, budget) | §0 freeze 4 + 5, T-005, T-006 |
| §2.9 four-edit revision round | §0 freeze 1 (post-R1 digests), T-008 |
| §3 negative scope (no backend, no new keys, no deps) | §0 freeze 4 + 6, T-005, T-006, T-010 |
| §6 decisions #1–#7 | freezes 2/3/6 + scenarios above |

---

## 3. What this eval does NOT do

- **No JS execution / browser automation** — text-level only (0008 posture);
  the ghost chart's visual correctness is the Gate 3 **manual render pass**
  (http.server + screenshots, reviewed by the user).
- **No backend execution beyond hermetic payload building** — `src/` is pinned
  read-only by digest, never modified.
- **No edits to prior evals** — the 12-entry guard makes any such edit fail.
- **No network.**

---

## 4. Gate 2 Sign-Off

- [x] **User approves** this test spec **including the six §0 freezes**
  (post-R1/R2 digests in freeze 1, page literals in freeze 2, anchor pins in
  freeze 3, backend digest table in freeze 6) → file is **FROZEN and
  immutable**; agent may start Gate 3 (RED → GREEN in `tests/test_0011.py` +
  the `index.html` switch). **(Approved 2026-10-07)**

**IMMUTABLE ONCE APPROVED:** a failing test means the *code* is fixed, never
this spec. Any post-freeze revision requires an explicit user directive and is
logged here (precedents: 0008 R1/R2, 0010 R1).
