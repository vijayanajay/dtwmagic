# VPS Deployment Checklist — dtwmagic

End-to-end from a fresh Debian/Ubuntu VPS to a serving site. Companion doc:
[nightly-eod-cron.md](nightly-eod-cron.md) carries the *why* (TZ rationale,
monitoring, failure semantics) — this is the *do* list. Documentation only —
no code or config files ship in the repo (spec 0009 frozen decision #5).

Order matters: **`data/static/api/` is git-ignored output** (`.gitignore`
carve-out), so it does not exist until the job has run — serve only after
step 3.

---

## 0. Prerequisites

- [ ] Debian/Ubuntu VPS (BRD §4.1: 4 vCPU / 8 GB is the documented ceiling, far
      above current single-symbol needs), NTP on (`timedatectl set-ntp true`).
- [ ] Outbound HTTPS reachable: github.com (clone) and
      `nsearchives.nseindia.com` (nightly fetch).
- [ ] DNS A/AAAA record pointing at the box (HTTP first; TLS in §6).

## 1. Clone

```bash
sudo apt-get update && sudo apt-get install -y python3-venv nginx
git clone https://github.com/vijayanajay/dtwmagic.git /opt/dtwmagic
cd /opt/dtwmagic
```

- [ ] Repo cloned at `/opt/dtwmagic` (single canonical path — the cron line
      and the Nginx root below both hardcode it).

## 2. Python venv

```bash
python3 -m venv .venv
.venv/bin/pip install pandas numpy pyarrow
.venv/bin/python -c "import pandas, numpy, pyarrow; print('deps ok')"
```

- [ ] `deps ok` printed. Runtime deps are exactly these three (the job uses
      stdlib `urllib`, no API keys, no database server).

## 3. Manual job run (creates `data/` outputs — do this before serving)

```bash
cd /opt/dtwmagic
.venv/bin/python -m src.eod_job; echo "JOB_EXIT=$?"
```

- [ ] `JOB_EXIT=0` and one stdout JSON line with `"ok": true`.
- [ ] All three outputs exist:
  ```bash
  ls -la data/parquet/^NSEI.parquet data/eod/^NSEI.csv \
         data/static/api/v1/^NSEI.json data/static/api/v2/^NSEI.json
  ```
- [ ] First run on a fresh clone is a **cold backfill (~1 h**, paced fetch of
      2007→today; run it inside `tmux`). Every later run is a delta of a few
      seconds.
- [ ] `data/eod/` now exists (the cron log target — the job creates it).

## 4. Cron install

```bash
crontab -e
```

```cron
TZ=Asia/Kolkata
30 17 * * 1-5 cd /opt/dtwmagic && .venv/bin/python -m src.eod_job >> data/eod/job.log 2>&1
```

- [ ] `crontab -l` shows the line above (17:30 IST weekdays — after NSE's
      16:30 publish, before the next open; full TZ/fallback discussion in the
      companion doc §3).
- [ ] Next weekday after 17:30 IST: `tail -1 data/eod/job.log` shows
      `"ok": true` (freshness check one-liner in the companion doc §4).

## 5. Nginx static serving

Install already done in §1. Create the site config:

```bash
sudo tee /etc/nginx/sites-available/dtwmagic >/dev/null <<'EOF'
server {
    listen 80 default_server;
    server_name _;

    root /opt/dtwmagic/data/static;   # serves index.html + api/v{1,2}/*.json
    index index.html;
    autoindex off;

    gzip on;
    gzip_types text/html application/json;

    # nightly artifacts: 5-minute cache so the EOD refresh shows up promptly
    location /api/ {
        add_header Cache-Control "public, max-age=300";
        try_files $uri =404;
    }

    location / {
        try_files $uri =404;          # single-page app; no SPA rewrite needed
    }

    location ~ /\. { deny all; }      # no .git / dotfiles

    access_log /var/log/nginx/dtwmagic.access.log;
    error_log  /var/log/nginx/dtwmagic.error.log;
}
EOF
sudo ln -sf /etc/nginx/sites-available/dtwmagic /etc/nginx/sites-enabled/dtwmagic
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

- [ ] `nginx -t` reports syntax ok (the one step that cannot be rehearsed
      off-box — run it on the VPS).
- [ ] Worker user can read the tree: `sudo -u www-data test -r
      /opt/dtwmagic/data/static/index.html` (if not: `chmod a+rX -R
      /opt/dtwmagic`).
- [ ] `data/static/api/` is under the root **and** git-ignored — deploys never
      overwrite nightly output, and nightly output never enters git.

## 6. Verification (on the VPS, then from your machine)

```bash
curl -sI http://SERVER/ | head -1                       # HTTP/1.1 200
curl -s  http://SERVER/api/v2/%5ENSEI.json | head -c 60 # {"schema": "dtwmagic.api.v2"…
curl -s  http://SERVER/api/v1/%5ENSEI.json | head -c 60 # {"schema": "dtwmagic.api.v1"…
curl -s  http://SERVER/ | grep -c "Ghost overlay"       # 1 (spec 0011 page)
```

- [ ] All four return as expected; open `http://SERVER/` in a browser: ToS
      modal → ghost chart with dated historical paths → footer. The freshness
      badge turns stale automatically if the cron dies (> 4 calendar days).

## 7. Ceilings / later

- **TLS:** HTTP first; `certbot --nginx` when the hostname is final (BRD CDN
  path stays an option — §4.1's $0-egress static serving is what this setup
  already is).
- **Longer cache:** once deploys get CDN'd, purge-on-EOD or a content-hash
  filename for the JSON replaces the 5-minute `max-age`.
- **Log growth:** cron log is one line/week/day; rotate via logrotate if it
  ever matters (companion doc ceiling).
- **Multi-symbol (Phase-2 / F-06):** same root; the job gains a batch loop
  first — serving config does not change.
