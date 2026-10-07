# Gate 1 — Requirement Spec `0011-ghost-overlay-frontend`

**Status:** `APPROVED — Gate 1 signed off 2026-10-07 (user: "Approve Gate 1 for spec 0011, apply the four R1 edits…"); R1/R2 edits applied same day; Gate 2 test spec in authoring; Gate 3 not started.`
**Date:** 2026-10-07
**Consumes:** frozen contract `dtwmagic.api.v2` (spec 0010 — live artifact
`data/static/api/v2/^NSEI.json`, 69,536 B, `last_date 2026-10-07`) and the
Phase-1 dashboard (spec 0008 — `data/static/index.html`, 18,426 B, R1).
**Side:** Frontend only (BRD §4.4 isolation) — consumes JSON; imports no Python.
**Special:** this spec requires a **precisely scoped revision (R1) of two frozen
evals** (0008 + 0010) because the v2 fetch switch crosses pins both of those
specs wrote *anticipating this switch* — see §2.9 and sign-off box 1.

---

## 1. User Value Rationale (DIRECT — no waiver needed)

- **This is the product's flagship feature (BRD F-05).** *"Overlays top 3–5
  matched historical price trajectories directly on top of the live candle
  chart, labeled with exact historical dates — Visual historical audit."*
  BRD's own rationale: *"Retail traders are visual. Seeing the exact historical
  chart from Oct 2020 or Jun 2022 overlaid gives immediate clarity."* Every
  other Phase-1 surface shipped in spec 0008; the one thing a visitor sees
  first — today's candles with the matched episodes' actual paths beside them —
  is still missing.
- **It is the monetization surface:** F-05's tier column is the clearest
  Free/Pro split in the BRD (Free Top 1 / Pro Top 5 + ghost paths), and the
  Free view is the lead-gen page (spec 0008 §1).
- **The deferral is now resolvable:** spec 0008 §6 #8 flagged that the overlay
  needs *"a v2 `query` block"* — delivered and verified by spec 0010 (the live
  v2 file carries the last 60 OHLC rows; today's close is
  `query.candles[59].close`). The gap was never a data gap after tonight — only
  a frontend gap.

---

## 2. What Is Needed (Scope)

### 2.1 Side & seam — the fetch switch (single page, in place)

- **One change to the existing seam:** `const API = "./api/v1/%5ENSEI.json"`
  → `"./api/v2/%5ENSEI.json"` in `data/static/index.html`. The page renders
  from the v2 document alone — it is a strict superset (every v1 key the page
  consumes is unchanged and deep-equal; spec 0010 §2.2), so **all eight
  spec-0008 components keep working unmodified**.
- **No second page.** The statutory layer (§8.2A footer, §8.2B modal) must
  exist in exactly one file — duplicating verbatim compliance copy across two
  HTML files creates two places to drift. The ghost chart joins the existing
  screen (BRD §6.2 #2 describes one integrated chart view).
- v1 keeps being written nightly (its frozen 0007/0009 contracts and pins
  stand); the page simply stops referencing it (§7 #7).

### 2.2 The chart component (BRD §6.2 #2, verbatim layout)

A new inline-SVG chart in the existing render pipeline (one new function beside
`coneSVG`, called from `render()` — window-selector-driven, re-renders on
window change and on the Simple/Quant and Free toggles):

- **Left:** today's candlestick window — the **last `L` candles of
  `query.candles`** (`candles.slice(-L)`), OHLC drawn as candlesticks, `L` =
  the selected window (5/10/15/30/60, default 10).
- **Right:** **ghost paths** — for the top analogs of the selected window, one
  polyline per episode of its *actual* 10-session close path, **re-anchored to
  today's close** (§2.3), starting at the current candle and extending 10
  columns right. **Each ghost is labeled with its exact historical match date**
  (`analog.date`, e.g. `2012-05-14`) — BRD's "visual historical audit" requires
  the date on the line, not in a tooltip.
- **X-domain:** `L + 10` columns (candles `0..L-1`, ghosts extend to `L+9`).
  Y-domain: shared by candles and ghosts (ghost prices are anchored to the
  candle level by construction).
- **Legend copy (Layer 2, §8.2D-safe — frozen at Gate 2):** a caption reading
  *"Historical Ghost Paths — each line replays the actual path a matched
  historical episode took after its match date, re-anchored from that date's
  close to today's close."* plus the existing mandatory footnote nearby. Copy
  must clear the 0008 frozen forbidden-word scan (`forecast/predict/signal/
  tip/target/buy/sell/…`) — it is descriptive-past by construction.
- **No new §8.2C tooltip entry:** the six frozen tooltips stay the canonical
  set; the ghost explanation is legend copy, not an indicator header.

### 2.3 Anchoring math (frozen formula)

For analog `a` of the selected window, with today's close
`c0 = query.candles[59].close` (window-independent):

```
ghost[0]      = (L-1, c0)                        # anchor at the current candle close
ghost[i]      = (L-1+i, c0 * a.forward[i-1].close / a.close)   # i = 1..10
```

- **Ratio re-anchor from the episode's own match-day close** — exactly
  GLOSSARY's definition (*"the actual subsequent path … anchored to the current
  price"*). Pure descriptive replay: the historical shape is preserved; only
  the price level is rescaled. No extrapolation, no smoothing, no model.
- Close-only polylines for ghosts (trajectories, not candles) — the episode's
  OHLC lives in `forward` but a line is the honest minimal rendering (rung 6);
  candle-by-candle replay of ghosts is a ceiling.
- `analog.close` is the T+0 baseline of `forward` (spec 0003), so the ratio is
  dimensionless and era-safe (2012's 4,870 and 2026's 22,600 both map onto
  today's axis).

### 2.4 Tier truncation (client-side, honoring frozen decisions)

| View | Ghosts shown |
|---|---|
| Full (default, spec 0008 #5 — no billing exists yet) | **top 3** (BRD §6.2 #2: "Top 3 historical patterns") |
| Free view toggle | **top 1** (BRD F-05: "Free (Top 1)") |

- Constants frozen as literals: `const GHOST_TOP = 3`,
  `const GHOST_TOP_FREE = 1` (0011's eval pins them; 0008's pin on
  `FREE_TOP_K = 3` is untouched — match-list truncation stays 3).
- **Ambiguity surfaced, not buried (§7 #5):** F-05's tier column reads
  *"Pro (Top 5 + Ghost paths)"*, which can be read as ghosts being Pro-only.
  Recommendation: show ghosts in both views now (no billing to enforce against
  — 0008 #5), re-gate at Phase 3. Flag if you disagree.

### 2.5 Edge & honesty states

- **`query` absent/short (stale or wrong artifact served):** hide the chart
  component, render everything else — never a crash, never a blank block.
- **Fetch failure / non-200:** the existing red banner (0008 §2.5) — unchanged.
- **`summary: null` windows:** unaffected — the chart reads `analogs` +
  `query`, not `summary`; the insufficient-sample panel still renders for the
  stats surfaces.
- **Freshness:** ghost chart sits under the existing staleness badge logic
  (`STALE_DAYS = 4`, unchanged).

### 2.6 Testing (static contract lint — 0008 posture, zero new deps)

`tests/test_0011.py`, hermetic v2 payload built via spec 0010's
`build_snapshot_v2` (fixture store, no network):

- **Fetch seam:** page contains `"./api/v2/%5ENSEI.json"`, and `api/v1` does
  **not** appear anywhere in the page.
- **Contract coverage:** page references the new key paths (`query`,
  `candles`) plus all 28 frozen 0008 substrings still (version-agnostic).
- **Behavioral literals (frozen before code, 0008 posture):**
  `const GHOST_TOP = 3`, `const GHOST_TOP_FREE = 1`, the exact §2.3 anchor
  expression `c0 * a.forward[i-1].close / a.close`, chart function marker.
- **Compliance survival regression:** statutory markers, exactly two ToS
  checkboxes, all six §8.2C tooltips verbatim, footer/footnote/labels, the
  forbidden-word scan over the whole (non-statutory) page — including the new
  ghost copy — and **localStorage key set still exactly
  `{dtwmagic_tos_accepted, dtwmagic_view_mode, dtwmagic_window}`** (no new
  keys — 0008 T-008 asserts exact equality).
- **Budget/isolation:** total authored bytes < 100,000 (0008 T-001 keeps
  enforcing it too); `ABSENT` list (no `src.*`, no `<script src`, no http
  assets); `.gitignore` carve-out intact.
- **Guard table:** both fixtures + `test_0001..test_0010` (10 evals) at their
  **post-R1** digests — measured after the §2.9 revision round, probe-verified
  before Gate 2 freeze.
- **Manual render pass at Gate 3** (the human-visible artifact, as in 0008):
  `python -m http.server -d data/static`, all components + ghost chart with
  labeled dates, window-switch re-render, Free view → 1 ghost, both toggles,
  console clean, screenshots for you.

### 2.7 Dependencies

**None.** Vanilla ES2020 + inline SVG as shipped; no chart library.

### 2.8 Acceptance Summary (for Gate 2 authoring)

- Page fetches the v2 file; all eight 0008 components still render from it
  (shared keys deep-equal by construction — 0010 §2.2); ghost chart renders
  `L` candles + ≤3 labeled ghosts (≤1 in Free view) per §2.3 formula.
- The two R1 revisions land **exactly** as scoped in §2.9; post-R1, **the
  full suite (138 existing evals + new 0011 eval) is green** with prior evals
  otherwise byte-untouched.
- Bundle < 100 KB; compliance layer byte-survives; forbidden scan clean with
  the new copy in place.
- Manual render pass verified with screenshots.

### 2.9 The R1 revision — exact scope (approved by sign-off box 1)

**Why it is allowed:** both pins *name this spec*. 0010's frozen §0 freeze 6
says the v2 absence is *"(frontend switch belongs to spec 0011, Gate 1 §7 #7)"*;
0008's fetch literal was the v1 contract of its day. Revising a frozen eval is
forbidden **unless user-directed** — that directive is this gate.

**Exactly four edits, nothing else:**

1. `tests/test_0008.py` — `LITERALS` entry `"./api/v1/%5ENSEI.json"` →
   `"./api/v2/%5ENSEI.json"` (one string) + docstring notes R1 (pattern: the
   existing data-tip→data-metric R1 note).
2. `specs/tests/0008-phase1-dashboard.md` — R1 note + the two prose mentions
   of the fetch literal (§0 freeze 6, T-008 text) updated to v2.
3. `tests/test_0010.py` — T-009's frontend pin flips:
   `assert "./api/v2/" in page`, `assert "api/v1" not in page` (the isolation
   intent — *consume the JSON seam, never Python* — is unchanged), **and**
   `GUARD_SHAS["tests/test_0008.py"]` re-pinned to its post-R1 digest (edit 1
   changes that file; nothing else pins it).
4. `specs/tests/0010-v2-query-block.md` — R1 note + freeze-6 prose updated.

**Cascade analysis (why this is the whole list):** test_0008's guard pins
`test_0001..0007 + test_0009` (not itself, not 0010); test_0010's guard pins
`test_0001..0009`; **nothing pins `test_0010.py`** — so the chain stops at
edit 3. No frozen *code* (`src/`), no prior spec doc, no fixture changes.

**Timing:** edits 1–4 are applied **immediately after Gate 1 approval and
before Gate 2 authoring**, so Gate 2's guard table can pin the real post-R1
digests (probe-before-freeze intact). The revisions are logged in 0011's Gate 4
record with before/after shas.

---

## 3. What Is NOT Needed (Negative Scope)

- **No backend changes** — `src/`, fixtures, and specs 0001–0010's code and
  pins are untouched (the only edits anywhere are the four in §2.9).
- **No second HTML page, no new localStorage keys, no new checkboxes, no
  changes to the six-frozen-tooltip §8.2C set** (0008's evals assert exact
  equality on several of these).
- **No twin-sparkline *pattern* geometry** — the matched episodes' preceding
  L-bar prices are not in v2 (0010 ceiling); ghosts show forward paths only.
- **No volume/F-07 wick weighting, no VIX/macro context** (absent from v2),
  **no intraday, no symbol switcher, no auth/billing enforcement** (Phase 3),
  **no JS test runtime/bundler/npm**, **no alerting**, **no v1 retirement**
  (its producer and pins stand until a user-approved 0009 revision says
  otherwise).

---

## 4. Architecture Alignment (Kailash Nadh)

- The whole feature is **one fetch literal, one SVG function, two constants,
  and one legend caption** — a rendering of data that already exists; zero new
  compute, zero new dependencies, ~3–5 KB of authored bytes.
- Contract-first (BRD §4.4): the page still knows only the JSON schema; the
  backend still knows only Parquet; the switch is a versioned path change on
  the frozen seam.
- The single-page decision keeps the statutory layer a single source of truth
  — boring and auditable.

---

## 5. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is 3 ghosts (full) / 1 (Free); upgrade path is 5
  (F-05 Pro) when billing lands, then per-tier gating server-side.`
- `# ponytail: ceiling is close-line ghosts; upgrade path is replaying each
  episode's OHLC as candlesticks if a line reads as too coarse.`
- `# ponytail: ceiling is EOD-anchored ghosts (anchor = last close); upgrade
  path is intraday anchoring, which needs an intraday store first.`
- `# ponytail: ceiling is editing index.html in place; upgrade path is
  splitting css/js once the file outgrows one screen (0008's ceiling).`
- **Inherited (0010):** no analog-side pattern prices → true geometric twin
  sparklines wait on a v3 block; 4-calendar-day staleness heuristic; localStorage-only state.

---

## 6. Frozen Decisions (pre-Gate-1 session; approval approves all seven)

| # | Decision | Choice |
|---|---|---|
| 1 | Seam switch | **Fetch `./api/v2/%5ENSEI.json` in the single existing page** — v2 is a superset so all 0008 components keep rendering; no second page (statutory copy stays single-source) |
| 2 | R1 to frozen evals | **Exactly the four edits of §2.9**, applied post-Gate-1/pre-Gate-2, cascade-stopping at test_0010 (nothing pins it), logged with before/after shas in Gate 4 — no other assertion, spec, fixture, or `src/` file is touched |
| 3 | Anchoring | **Ratio re-anchor to today's close:** `c0 * forward.close / analog.close`, close-line polylines, x-domain `L + 10`, ghosts labeled with `analog.date` — descriptive replay per GLOSSARY, no extrapolation |
| 4 | Tier truncation | `GHOST_TOP = 3` (full, BRD §6.2 #2) / `GHOST_TOP_FREE = 1` (Free, BRD F-05); client-side only, matching 0003/0007/0008 "truncation is the UI's" |
| 5 | F-05 tier ambiguity | **Ghosts visible in both views now** (no billing exists — 0008 #5); the "Pro (Top 5 + Ghost paths)" reading is re-examined at Phase 3 — surfaced for veto at sign-off |
| 6 | Testing | Static lint `tests/test_0011.py` over the authored file + hermetic `build_snapshot_v2` payload; guard table = fixtures + `test_0001..0010` post-R1; manual `http.server` render pass with screenshots at Gate 3 |
| 7 | v1 fate | **Kept, produced nightly, unreferenced by the page** — retiring the v1 write is a separate user-approved 0009 revision, not part of this spec |

---

## 7. Gate 1 Sign-Off

- [x] **User approves** this requirement spec — **including §2.1's fetch
  switch, §2.9's exact four-edit R1 revision of frozen evals 0008/0010, the
  §2.3 formula, §2.4 ghost counts, and §6 decisions #4/#5 (ghosts in both
  views)** → agent may (a) apply the R1 edits, then (b) author Gate 2 test
  spec `specs/tests/0011-ghost-overlay-frontend.md`. **(Approved 2026-10-07)**
- [x] **No new dependency requested** (§2.7) — nothing to approve. **(Approved
  2026-10-07)**

**STOP:** No Gate 2 or Gate 3 work proceeds until the boxes above are checked
by the user. The R1 edits are applied only after approval. The test spec is
**IMMUTABLE once approved**; Gate 3 (code) still requires that separate
approval.
