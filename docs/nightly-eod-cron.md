# Nightly EOD Job — Linux VPS Cron Install

**Scope:** scheduling documentation for `python -m src.eod_job` (spec 0009,
extended by spec 0010). Per spec 0009's frozen decision #5 this repo ships **no
committed cron/systemd file** — the line below is documentation; the scheduler
stays the operator's. No code is changed by following this doc.

One cron tick = one command that:

```
fetch NSE ind_close_all → master ledger + Parquet store  (spec 0002)
→ data/static/api/v1/{symbol}.json   (dtwmagic.api.v1, spec 0007 — frozen)
→ data/static/api/v2/{symbol}.json   (dtwmagic.api.v2 + query block, spec 0010)
```

The job prints **exactly one JSON line** to stdout and exits **0 iff `ok:
true`**. A failing run never touches the previously written good v1 or v2 file
(verified by eval T-008), so a partial failure never breaks the site.

---

## 1. One-time setup

```bash
# system deps: python3 + venv support (Debian/Ubuntu example)
sudo apt-get install -y python3-venv

git clone <repo-url> /opt/dtwmagic && cd /opt/dtwmagic
python3 -m venv .venv
.venv/bin/pip install pandas numpy pyarrow   # runtime deps: stdlib urllib only
```

The job needs no API keys and no web server to run; `data/` (store, ledger,
snapshots) is generated output and is git-ignored.

## 2. Prove it manually *before* installing cron

```bash
cd /opt/dtwmagic
.venv/bin/python -m src.eod_job; echo "JOB_EXIT=$?"
```

Expected on success:

- `JOB_EXIT=0` and a stdout line like
  `{"symbol": "^NSEI", "end_date": "…", "ok": true, "refresh": {…},
  "snapshot": {"path": "data\\static\\api\\v1\\^NSEI.json", "bytes": …, …},
  "error": null}`
- both artifacts present:
  ```bash
  ls -la data/static/api/v1/^NSEI.json data/static/api/v2/^NSEI.json
  ```
- `data/eod/` now exists (the job creates it — this is also where the cron log
  will go).

On an empty repo the **first** run backfills from `--start-date` (default
`2007-09-17`) at ~1 s/day pacing — roughly an hour. Run it inside
`tmux`/`nohup`. Every later run is a delta no-op taking a few seconds
(≈1 s store rewrite + ≈1.2 s dual snapshot build).

## 3. Install the crontab

```bash
crontab -e
```

Add (adjust `/opt/dtwmagic` to your clone path):

```cron
TZ=Asia/Kolkata
30 17 * * 1-5 cd /opt/dtwmagic && .venv/bin/python -m src.eod_job >> data/eod/job.log 2>&1
```

Why this line:

- **`30 17 * * 1-5` — 17:30 IST weekdays.** NSE publishes `ind_close_all`
  after the 16:30 IST close; the run finishes well before the next session
  opens (09:15 IST).
- **`TZ=Asia/Kolkata`** pins the schedule (and the job's `date.today()`
  `--end-date` default) to IST. If your cron flavor ignores `CRON_TZ`/`TZ`
  lines and the server runs UTC, the tick fires at 17:30 UTC = 23:00 IST —
  still the same calendar date and still after the close, so results stay
  correct; IST is preferred for clarity. Keep the clock NTP-synced
  (`timedatectl set-ntp true`).
- **`cd … && .venv/bin/python`** — relative paths, no reliance on cron's
  minimal `PATH`.
- **`>> data/eod/job.log`** — one JSON line per weekday (~250 lines/year);
  rotation is not worth configuring yet (see ceilings).

## 4. Verify the install

```bash
crontab -l                       # the line is present
# the next weekday after 17:30 IST:
tail -1 data/eod/job.log          # "ok": true, "error": null
```

Freshness check (stdlib only — no jq dependency needed):

```bash
.venv/bin/python -c "import json,sys; r=json.loads(open('data/eod/job.log').read().splitlines()[-1]); print(r['ok'], r['snapshot']['last_date'], r['error'])"
```

Expected: `True <today's session date> None`.

## 5. Monitoring (boring, by design)

- **Exit code / `ok`** is the health signal. A transient failure (NSE site
  down, network blip) exits 1 and **self-heals on the next tick** — 0009's
  documented posture: natural re-run, no retry framework.
- **`snapshot.last_date`** is the freshness signal. The dashboard's own
  freshness badge turns stale when `today − last_date > 4` calendar days
  (weekend/holiday tolerant), so a dead cron becomes visible to users without
  any extra tooling.
- **`error` prefixes name the failing stage:** `refresh: …` (fetch/ledger) vs
  `snapshot: …` (store too thin / unclassifiable regime / write failure).
- Both output files are regenerated wholesale each night; the v1 file remains
  byte-deterministic for a given store state and the frontend reads `api/v1`
  until spec 0011 switches it to `api/v2`.

## 6. What this doc deliberately does not do

- **No systemd unit, container, or scheduler daemon** — the crontab line is
  documentation (0009 §2.3 / frozen decision #5); if you prefer systemd timers
  on your VPS, `OnCalendar=Mon..Fri 17:30` + `TZ=` equivalent is the operator's
  choice with the same command.
- **No alerting integration** — wire your existing process monitor to the exit
  code or to `job.log`'s `ok` field; BRD §8.1.4 bars in-product broadcast
  channels anyway.
- **No serving/web-server config** — `data/static/` is plain static files for
  Nginx/CDN per BRD §4.2; how you serve it is out of scope here.

---

### Ceilings

- `# ponytail: ceiling is one appended log line per weekday, never rotated;
  upgrade path is logrotate (or clearing the file) if the log ever matters.`
- `# ponytail: ceiling is a single-symbol job on one VPS; upgrade path is
  0009's documented multi-symbol/Phase-2 batch (F-06).`
- `# ponytail: ceiling is manual freshness eyeballing via §4; upgrade path is
  a cron wrapper checking last_date age > 4 days and exiting nonzero.`
