# Gate 1 — Requirement Spec `0008-phase1-dashboard`

**Status:** `APPROVED — Gate 1 signed off 2026-10-07 (user, “approved”); Gate 2 test spec in authoring`
**Date:** 2026-10-07
**Consumes:** frozen contract `dtwmagic.api.v1` (spec 0007) + its nightly producer
(spec 0009, live-verified 2026-10-07: store 4,675 rows, snapshot `last_date
2026-10-07`). Frontend-only per BRD §4.4 isolation; specs 0001–0009 untouched.

---

## 1. User Value Rationale (DIRECT — no waiver needed)

- **Why a paying trader cares:** this spec *is* the product. The engine (0001–0007)
  and its heartbeat (0009) produce a JSON file nobody can look at; BRD §7.2's Phase 1
  is "engine **+ standalone interactive web dashboard**", and the dashboard is the
  only Phase-1 item still missing. The trader's entire value loop — "has this pattern
  occurred before, and what did those episodes do?" — renders here: the outcome cone
  (F-03), observed MAE/MFE (F-04), historical analogs with dates (F-05's drawer), and
  the regime tag (F-02).
- **Monetization link:** the Free tier (BRD §2.2) *is* this page — NIFTY 50, 10-day
  window, top-3, EOD. It is the lead-gen surface; nothing sells Pro without it.
- **Compliance link:** SEBI safe-harbor copy (§8.2A footer, §8.2B ToS modal, §8.2C
  tooltips, §8.2D phrasing) only becomes real in the UI. A public launch without it
  is not launchable.

---

## 2. What Is Needed (Scope)

### 2.1 Layout, serving, and the one tracked-file change

- **Authored dashboard:** a single self-contained `data/static/index.html`
  (inline CSS/JS, evolved from the existing 141-line `preview.html` prototype —
  same dark theme, cone SVG, tables; extended per §2.3–§2.5).
- **Fetch:** `./api/v1/%5ENSEI.json` (percent-encoded `^` — the prototype already
  proves this works; no alias map needed, 0007's ceiling resolved as "not needed").
- **Serve:** `python -m http.server 8000 -d data/static` → `http://localhost:8000/`.
  No build step, no bundler, no backend process.
- **`.gitignore` (the only tracked file this spec modifies):** replace `/data/` with
  `/data/parquet/`, `/data/eod/`, `/data/static/api/` — generated store, ledger, and
  snapshots stay ignored; the authored dashboard becomes committable. Gate 1 approval
  covers this edit.

### 2.2 Stack & budget (BRD §7.1)

- Vanilla HTML/JS (ES2020) + inline SVG charts. **Zero dependencies** — no npm,
  no node, no framework, no bundler (rung 3–6; BRD §4.2 "zero heavy framework").
- **Total authored static bytes < 100 KB** (lint-enforced; prototype is 9 KB) with
  first meaningful paint ≤ 300 ms (§7.1 SLA, sanity-checked manually at Gate 3).

### 2.3 Screens (BRD §6.2 + §6.3 progressive disclosure, v1-complete)

1. **Context bar:** `NIFTY 50 (^NSEI)` (literal display map in the page — frontend
   data, not an import of 0002's dict), `schema` tag, `bars`, **freshness badge**
   from `last_date` (styled stale when `today − last_date > 4` calendar days —
   weekend/holiday tolerant; no trading calendar, §5 ceiling), and the regime pills:
   `HISTORICAL REGIME: BEARISH / NORMAL`, `cell`, `NATR percentile p252`.
2. **Window selector:** buttons rendered from the document's own `windows` keys
   (data-driven: 5/10/15/30/60), default **10** (Free tier's fixed window),
   choice persisted in `localStorage`.
3. **Executive summary card** (§6.3 Layer 1): plain-English bullets derived from the
   selected window's `summary` — positive frequency in words ("In N of n matched
   historical episodes (X%), price closed higher after 10 sessions"), median outcome,
   adverse-excursion context, p10–p90 spread — plus the mandatory §6.3/§8.2C
   footnote: *"Descriptive historical observations only — not a forecast, target, or
   investment recommendation."*
4. **Forward cone chart** (SVG): p10–p90 and p25–p75 bands, p50 line, raw analog
   forward paths, zero line — with §6.3 Layer-2 legend labels ("Typical Historical
   Path (p50)", "Common Historical Zone (Middle 50%)", "Full Historical Range
   (Outer 80%)").
5. **Statistics matrix:** full horizon table T+1…T+10 — `positive_frequency`,
   `cone` p10/p25/p50/p75/p90, `mae[h].p80`, `mfe[h].p50` — each header carrying its
   §8.2C tooltip (Layer 3).
6. **Historical matches list:** one card per analog — date, `score` similarity %,
   `distance`, observed historical outcome (return at T+10 from
   `forward[9].close / close − 1`), and a mini SVG sparkline of that episode's own
   forward path (self-contained: drawable from `close` + `forward`).
7. **Simple / Quant toggle** (§6.3): Simple = summary card + cone + matches;
   Quant = full matrices, raw distances, p252, raw JSON `<details>` viewer.
   Preference persisted in `localStorage`.
8. **Free view toggle:** client-side truncation to the BRD §2.2 Free tier —
   `L=10` only, top-**3** analogs, median-only cone/stat row — honoring 0003/0007's
   frozen decision that *"Free top-3 truncation is the UI's"*. **Default view is
   full** (no billing exists to enforce tiers yet, §6 #5).

### 2.4 Compliance layer (§8.2, verbatim strings)

- **Persistent footer** with the full §8.2A statutory text, visible on every view.
- **ToS acceptance modal** with §8.2B's two checkboxes; view is blocked until both are
  checked; acceptance persisted in `localStorage` (`dtwmagic_tos_accepted`).
- **Six §8.2C tooltips** (observed MAE, observed MFE, positive frequency, median p50,
  quantile range, historical regime) — verbatim.
- All copy obeys §8.2D phrasing; the lint in §2.6 enforces it mechanically.

### 2.5 Edge & honesty states

- **`summary: null`** (zero-pool / thin-regime days — the contract's real state):
  render an *"Insufficient historical sample in this regime"* panel showing
  `n = 0` context instead of an empty chart — never a blank card, never a crash.
- **Fetch failure / non-200:** red error banner with the status (prototype pattern).
- **Window key absent:** selector only offers keys present in the document.

### 2.6 Testing (frontend testable without a JS runtime — zero new deps)

`tests/test_0008.py` — a **static contract lint**, text-level only, respecting
BRD §4.4's isolation (no JS execution, no UI import of backend internals):

- Hermetic payload: build the v1 document via 0007's `build_snapshot` into `tmp_path`
  (fixture store, no network).
- **Key coverage:** `index.html` references every consumed key path
  (`windows`, `analogs`, `forward`, `summary`, `cone`, `positive_frequency`, `mae`,
  `mfe`, `regime`, `p252`, `last_date`, `%5ENSEI.json`, horizon keys `"1"…"10"`).
- **Mandatory strings present:** the §8.2A footer sentence, both §8.2B checkbox
  texts, all six §8.2C tooltips, the §6.3 footnote.
- **Forbidden-word scan** (§8.2D: "win rate", "target price", "stop-loss",
  "forecast", "signal", "prediction", …) over the authored file — Gate 2 must freeze
  the exact word list and the whitelist scope (the statutory texts themselves
  necessarily contain banned words inside negations, e.g. §8.2A's "does not provide…
  stop-loss levels").
- **Budget:** total authored bytes < 100 KB; `.gitignore` carve-out present; the
  page contains no reference to `src.` / Python internals (isolation check).
- **Full suite:** all 118 existing evals stay green and unmodified (sha guards).

### 2.7 Dependencies

**None.** Stdlib pytest assertions over static text; the browser is the renderer.

### 2.8 Acceptance summary (for Gate 2 authoring)

- Served page loads from the committed file, fetches the v1 payload, and renders all
  eight §2.3 components; both toggles and the ToS acceptance survive reload
  (localStorage).
- `summary: null` window renders the insufficient-sample panel, not an empty chart.
- Footer visible without scrolling on load (persistent), tooltips verbatim, lint
  green, suite 118+ green, bundle < 100 KB.
- **Manual render check** at Gate 3 via a local `http.server` (the human-visible
  artifact — screenshots reviewed by the user), since no JS runtime is in scope.

---

## 3. What Is NOT Needed (Negative Scope)

- **No backend changes of any kind** — `src/`, specs 0001–0009, fixtures, and the
  v1 schema are untouched; their frozen evals and shas are regression gates.
- **No schema v2 / `query` block** — see §6 #8: the current-window candle panel,
  live-chart ghost overlay (F-05's "projected onto today"), and twin sparklines need
  prices the v1 document does not carry. Deferred to their own future Gate-1 spec
  (§4.4: schema changes require a version bump).
- **No auth, billing, accounts, or server-side tier enforcement** (Phase 3) — the
  Free view is a client-side toggle only.
- **No F-06 screener, no F-07 volume weighting, no alerts, no exports, no
  multi-timeframe/intraday, no symbol switcher** (one snapshot, `^NSEI`, exists).
- **No npm/node/React/Vue/bundler/TypeScript, no web framework, no FastAPI/nginx
  config, no Docker** — `python -m http.server` only.
- **No JS unit/e2e test runtime** (vitest/playwright would be new deps — §5 ceiling),
  no service worker/PWA, no analytics/telemetry, no i18n, no VIX/macro context
  (absent from v1; a v2 candidate).

---

## 4. Architecture Alignment (Kailash Nadh)

- One committed HTML file + one stdlib static server: the entire delivery layer.
- Contract-first (BRD §4.4): the page knows only the JSON schema; the backend knows
  only Parquet; they meet at `data/static/api/v1/*.json` and nothing else.
- Pre-computation already paid for (0009): the page does arithmetic on 10-row arrays
  and draws SVG — no server-side render, no cache layer, no CDN needed yet.

---

## 5. Known Ceilings (Ponytail ceiling comments)

- `# ponytail: ceiling is no JS test runtime; upgrade path is vitest/playwright when
  a UI behavior regression actually costs more than the dependency.`
- `# ponytail: ceiling is freshness badge with a 4-calendar-day heuristic; upgrade
  path is an NSE holiday calendar (shared with 0002/0009).`
- `# ponytail: ceiling is a single self-contained index.html; upgrade path is
  splitting css/js once the file outgrows one screen.`
- `# ponytail: ceiling is %5E percent-encoding for the `^` filename; upgrade path is
  a URL-alias map if a non-encoded URL is ever required.`
- `# ponytail: ceiling is localStorage-only state (Free view, toggle, ToS); upgrade
  path is accounts when billing lands (Phase 3).`
- **Schema ceiling (the big one):** no current-window prices in v1 → no live-candle
  overlay; upgrade path is a v2 `query` block spec (§6 #8).

---

## 6. Frozen Decisions (pre-Gate-1 session)

| # | Decision | Choice |
|---|---|---|
| 1 | Side & seam | **Frontend only**; sole seam is the committed v1 JSON (BRD §4.4) |
| 2 | Layout / serve | `data/static/index.html`, fetch `./api/v1/%5ENSEI.json`, `python -m http.server -d data/static` |
| 3 | Tracked-file change | **`.gitignore` narrowed** `/data/` → `/data/parquet/` + `/data/eod/` + `/data/static/api/` (dashboard committable, outputs stay ignored) |
| 4 | Stack | **Vanilla + inline SVG, zero deps, single file, <100 KB lint** (BRD §7.1) |
| 5 | Tier display | **Default full; client-side "Free view" toggle** (L=10/top-3/median-only) — honors 0003/0007's "truncation is the UI's"; no billing to enforce against yet |
| 6 | Testing | **pytest static-contract lint only** — hermetic 0007-built payload + text assertions; no JS runtime (§2.6) |
| 7 | Honesty states | `summary: null` → insufficient-sample panel; fetch error → banner; freshness badge stale at > 4 calendar days |
| 8 | Current-window gap | **Flagged, not silently dropped:** live-candle ghost overlay / twin sparklines / current-price context need a v2 `query` block (§4.4 bump, would supersede frozen 0007/0009 pins) → **deferred to a future Gate-1 spec**; Phase-1 renders the complete historical-search surface from v1 |
| 9 | Symbol | `^NSEI` only, displayed "NIFTY 50 (^NSEI)" via a literal in the page |

---

## 7. Gate 1 Sign-Off

- [x] **User approves** this requirement spec (incl. the §2.1 `.gitignore` edit,
      §2.3 screen list, §2.6 test approach, and §6 frozen decisions — **especially
      #5 default tier view and #8 deferring the current-window overlay**) →
      agent may author Gate 2 test spec `specs/tests/0008-phase1-dashboard.md`.
      **(Approved 2026-10-07)**
- [x] **No new dependency** (§2.7) — nothing to approve. **(Approved 2026-10-07)**

**STOP:** No Gate 2 or Gate 3 work proceeds until the box above is checked by the user.
