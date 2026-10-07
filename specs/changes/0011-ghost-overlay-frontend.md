# Gate 4 — Change & Decision Record `0011-ghost-overlay-frontend`

**Date:** 2026-10-07
**Outcome:** all 4 gates complete. **Zero test-spec revisions to 0011** (R0 for
its own file); the cross-spec revision round of frozen evals 0008/0010 was the
one **user-approved R-round** executed at Gate 1 §2.9 (0008 → **R2**,
0010 → **R1**).

---

## 1. Files added / modified

| File | Change |
|---|---|
| `specs/requirements/0011-ghost-overlay-frontend.md` | **new** — Gate 1 (275 lines, approved 2026-10-07 incl. §2.9 R-round) |
| `specs/tests/0011-ghost-overlay-frontend.md` | **new** — Gate 2 FROZEN (6 freezes, T-001..T-010, approved 2026-10-07) |
| `tests/test_0011.py` | **new** (~330 lines) — frozen eval, 12-entry guard + 9-file backend digest table |
| `data/static/index.html` | **modified** — fetch → `./api/v2/%5ENSEI.json`; `GHOST_TOP`/`GHOST_TOP_FREE` constants; new `ghostSVG()`; render wiring + legend caption |
| `tests/test_0008.py` | **R2 edit (user-directed)** — `LITERALS` fetch literal v1 → v2 + docstring |
| `specs/tests/0008-phase1-dashboard.md` | **R2 note** — status, freeze 6, T-008 prose, header contract, revision log |
| `tests/test_0010.py` | **R1 edit (user-directed)** — T-009 pin flip + `GUARD_SHAS[test_0008]` re-pin + docstring |
| `specs/tests/0010-v2-query-block.md` | **R1 note** — status, freeze 6, T-009 prose, revision log |
| `specs/changes/0011-ghost-overlay-frontend.md` | **new** — this record |

---

## 2. Decisions & the revision ledger (and why)

1. **Single-page switch, not a second page (Gate 1 #1):** the statutory layer
   (§8.2A footer / §8.2B modal) stays single-source; v2 is a strict superset of
   v1 so all eight spec-0008 components rendered unchanged after the switch.
2. **The R-round was bounded and cascades stopped where Gate 1 predicted:**
   - `tests/test_0008.py`: `b90993e2…6cb68` → **`bafc6d0d…412a7fe`** (one
     literal + docstring).
   - `specs/tests/0008…`: prose + R2 revision-log entry.
   - `tests/test_0010.py`: T-009 flip + guard re-pin
     (`fb3338d3…24d21`), R1 docstring.
   - `specs/tests/0010…`: prose + R1 revision-log entry.
   - **Nothing else:** `src/` untouched (enforced by freeze 6's 9-digest
     table), no fixture changed, nothing pins `test_0011.py` or
     `test_0010.py` — verified by T-008 and by every guard staying green.
3. **Interim RED was planned and named, not discovered:** post-Round and
   pre-switch the suite showed exactly `2 failed, 18 passed` (`0008::T-008`,
   `0010::T-009`) — documented in the frozen Gate 2 header *before* freeze so
   it could not be mistaken for collateral damage; both flipped green the
   moment the fetch literal switched.
4. **Anchor formula pinned twice (page + eval):** the literal
   `c0 * a.forward[i-1].close / a.close` in `ghostSVG` and the eval's
   independent recomputation (`22716.606442805332 / 22338.36400729451 /
   22933.99243551082` from the fixture) bind code and test to one number.
5. **Ghost counts shipped as approved:** `GHOST_TOP = 3` (BRD §6.2 #2) /
   `GHOST_TOP_FREE = 1` (BRD F-05), client-side slice only; visible in both
   views per #5 (the "Pro (Top 5 + Ghost paths)" reading is deferred to
   Phase-3 billing).
6. **Defensive edge:** `ghostSVG` returns `""` when `query` is absent/short —
   a v1 artifact at the v2 URL degrades to the 0008 page, never a crash.

---

## 3. Known limits & ceilings (Gate 1 §5)

- Ghosts are close-line polylines, 3 full / 1 Free (upgrade: 5 at billing;
  candle-by-candle replay if lines read too coarse).
- EOD-anchored only (anchor = last close); no intraday without an intraday store.
- True geometric twin sparklines still wait on a v3 block with analog-side
  window prices (0010's ceiling).
- Single `index.html` continues to grow (~18.4 KB → ~24 KB; <100 KB lint green).

---

## 4. Verification output (Gate 3 evidence)

- **RED:** `pytest tests/test_0011.py -q` → `4 failed, 6 passed in 50.16s`,
  `EXIT=1` — failures exactly `T-001` (seam), `T-002` (literals), `T-004`
  (page formula), `T-007` (legend); the 6 passes pin already-true invariants.
- **GREEN (first run):** → `10 passed in 36.79s`, `EXIT=0`.
- **Full suite:** → **`148 passed in 143.86s`, `EXIT=0`** (138 prior + 10 new;
  the two named interim failures resolved; all 12 guard entries + 9 backend
  digests green — zero edits to anything outside the approved file list).
- **Manual render pass** (`python -m http.server 8078 -d data/static`,
  payload `./api/v2/%5ENSEI.json` → 200 / 69,536 B):
  - Header shows `dtwmagic.api.v2 · 4675 bars · last session 2026-10-07`.
  - Ghost chart L=10: 10 candles + **3** dashed ghosts labeled `2012-05-16`,
    `2016-01-14`, `2012-05-22` (live-store top-3), legend caption verbatim.
  - **Free view:** exactly **1** ghost (`2012-05-16`), only `L=10` button,
    3 match cards, `dtwmagic_view_mode = "simple,free"` persisted.
  - **Window switch → L=30:** re-render with **30 candles + 3 ghosts**
    labeled `2011-05-25/26/27`, `dtwmagic_window = "30"` persisted.
  - **Quant toggle:** matrix + MAE/MFE/Range columns visible, ghost card
    intact, `dtwmagic_view_mode = "quant"` persisted.
  - ToS modal gated the view on first load (fresh origin).
  - **Console: 0 messages.** Screenshots reviewed in-session.
- **Cleanup:** browser tab closed; server PID 19492 terminated (0 listeners on
  8078); probe scripts removed.

---

## 5. Verification commands (reproducible)

```bash
.venv/Scripts/python.exe -m pytest -q          # 148 passed
.venv/Scripts/python.exe -m pytest tests/test_0011.py -q   # 10 passed
python -m http.server 8078 -d data/static       # manual render pass
```
