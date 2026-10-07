# Gate 4 — Change & Decision Record `0008-phase1-dashboard`

**Date:** 2026-10-07
**Gates:** Gate 1 approved (2026-10-07) → Gate 2 frozen (2026-10-07, 10 scenarios +
seven §0 freezes, final PROBE_EXIT=0) with **user-directed revision R1** (same day,
before any Gate 3 code) → Gate 3 Red → Green complete **+ manual browser render pass**.

---

## 1. Files Added / Modified

| File | Change |
|---|---|
| `specs/requirements/0008-phase1-dashboard.md` | Added — Gate 1 (approved) |
| `specs/tests/0008-phase1-dashboard.md` | Added — Gate 2 (FROZEN, 10 scenarios + seven §0 freezes, R1 applied) |
| `tests/test_0008.py` | Added — the frozen eval T-001…T-010 (autouse sha guard now covers tests 0001–0007 + 0009 and both fixtures) |
| `data/static/index.html` | Added — the deliverable: single self-contained page, **18,426 bytes** (18% of the 100 KB budget) |
| `.gitignore` | **Modified** (the one tracked-file change Gate 1 §2.1/#3 approved): `/data/` → `/data/parquet/` + `/data/eod/` + `/data/static/api/` — dashboard committable, generated outputs still ignored (`git check-ignore` re-verified for `^NSEI.json` and `preview.html`) |
| `data/static/api/v1/preview.html` | Untouched (untracked prototype, per §0 freeze 1) |
| Sources of specs 0001–0007, 0009 | **Untouched** — all evals re-run green under the new guard |

---

## 2. Architectural & Quantitative Decisions

1. **R1 before code (the frozen-spec self-contradiction).** Gate 3 pre-flight found
   that freeze 2/T-006 mandated literal `data-tip=` while freeze 4's `\btip\b`
   pattern matches it (hyphen = word boundary) — T-007 could never pass. Surfaced
   instead of silently patched; the user chose rename-to-`data-metric` over dropping
   the pattern or special-casing the scan, so both enforcement goals survive. Logged
   as R1 in the test spec's revision log; no other freeze changed.
2. **Statutory markers as the scan mechanism.** Safe-harbor copy (footer, modal,
   `TOOLTIPS` object, executive footnote) sits in `<!-- statutory:start/end -->`
   spans; T-007 strips them (DOTALL) and the 19-pattern scan runs over everything
   else — so §8.2 copy can quote banned words inside negations while page copy
   cannot use them at all. Inside `<script>` the markers ride on JS line comments
   (web-compat `<!--` semantics), keeping the file parseable in a browser and
   scannable as text.
3. **Tooltips bound at runtime, not markup.** Six §8.2C texts live in one
   `TOOLTIPS` literal (inside markers); headers carry `data-metric` keys and a
   loader sets `el.title` — native browser tooltips, zero CSS, and the banned-word
   text never appears outside a marked span. Render pass confirmed **6/6 elements
   received titles**.
4. **Three localStorage keys, combined view mode.** Gate 1 wanted both toggles to
   persist but freeze 6 capped keys at exactly three: `dtwmagic_view_mode` stores
   `"quant,free"` (mode + tier concatenated), parsed on load — persistence verified
   across a real reload with no fourth key.
5. **Tier truncation is client-side composition** (0003/0007's frozen "the UI's
   job"): Free view = `DEFAULT_WINDOW = "10"` only, `FREE_TOP_K = 3` analogs,
   median-only bullets/stat columns (`pro-only` CSS), cone drops bands — confirmed
   in the render pass (1 window button, 3 matches, pro columns `display:none`).
   Orthogonal to Simple/Quant, which keeps detail levels independent of tier.
6. **Static-contract lint instead of a JS runtime.** T-001…T-010 are text/regex
   assertions over the page plus hermetic payloads built by 0007's builder
   (fixture + slice) — no node, no new deps, zero backend imports (T-009), and the
   slice's all-null windows pin the contract state the panel must handle.
7. **`.gitignore` carve-out, not a new tree.** The BRD puts the frontend at
   `data/static/`; narrowing the ignore to the three generated subdirs keeps the
   served layout, the BRD seam, and git hygiene intact in one tracked-file change.

---

## 3. Known Limits & Ceilings (in `data/static/index.html` + Gate 1 §5)

- **No current-window prices in v1** (Gate 1 §6 #8, flagged at approval): no
  live-candle ghost overlay, no twin sparklines, no current-price context — needs a
  v2 `query` block spec (§4.4 version bump, would supersede frozen 0007/0009 pins).
- Freshness badge = `STALE_DAYS = 4` calendar heuristic (no trading calendar —
  shared ceiling with 0002/0009).
- Single self-contained `index.html` (split css/js when it outgrows one screen);
  `%5E` percent-encoding instead of a URL-alias map; localStorage-only state
  (accounts arrive with Phase 3 billing); no JS unit/e2e runtime (vitest/playwright
  = new dep — the render pass covers behavior until a regression costs more);
  gzip/serving left to Nginx/CDN; EOD-only (no auto-poll — reload pulls fresh).
- Null-summary panel proven hermetically (T-003); the live fixture-regime data
  always has pools, so the panel was code-reviewed but not visually triggered.

---

## 4. Verification Output (Gate 3)

```
RED (collection): 1 error, RED_EXIT=2   — transcription typo (unterminated
       f-string) in my test file, repaired before the behavioral Red; no
       assertion weakened.
RED (behavioral): 10 failed in 2.05s    RED_EXIT=1  (missing index.html,
       .gitignore not yet narrowed; sha guard green — 0 frozen files touched)
GREEN:            10 passed in 1.38s    GREEN_EXIT=0  (first run)
Full suite (0001..0009): 128 passed in 23.97s   FULL_EXIT=0  (118 prior + 10 new)

Pins confirmed live:
  page 18,426 bytes < 100,000; .gitignore has the three carve-out lines,
  no /data/ line; api/ outputs still ignored
  T-002 payload structure (8 key-order lists) + all 28 key substrings present
  T-003 slice: 416 bars, all five summaries null -> panel copy + .summary guard
  T-004..T-006: 4 footer + 2 checkbox + 6 tooltip needles verbatim, each inside
       statutory spans; exactly 2 checkboxes; 6 data-metric hooks (>= 3)
  T-007: 19 patterns x 0 hits outside markers (after R1 removed the self-trip)
  T-008/010: literals present; localStorage keys exactly the frozen three;
       T-009: zero isolation/self-containment violations
  sha guard: tests 0001..0007 + 0009 and both fixtures all match (0 edits)

Manual render pass (http.server on 127.0.0.1:8077, live payload 63,868 bytes):
  load: all eight Gate 1 2.3 components render; console clean (0 messages)
  ToS: modal blocks view -> both boxes -> hidden, dtwmagic_tos_accepted="1"
  Quant: body.quant, matrix visible, 6/6 tooltips bound, distances revealed
  Free view: only L=10, exactly 3 matches, pro columns hidden, median-only
       bullets + cone caption, view_mode="quant,free"
  reload: quant+free restored, ToS stays accepted, console clean
  cleanup: server + browser tab stopped (0 listeners on 8077, curl 000)
```

No test file or test spec was edited to achieve green; the autouse sha guard in
`tests/test_0008.py` proves it mechanically on every subsequent run (R1 was a
user-directed spec revision made before Gate 3 began, recorded in its revision log).
