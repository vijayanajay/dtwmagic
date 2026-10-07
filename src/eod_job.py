"""Nightly EOD job: fetch -> store -> static snapshot (spec 0009, BRD 4.2 heartbeat).

Composes the frozen seams: 0002's refresh_store (master ledger + full Parquet
rewrite), 0007's build_snapshot (byte-deterministic dtwmagic.api.v1 JSON), and
0010's build_snapshot_v2 (dtwmagic.api.v2 + query block, written to the sibling
v2/ dir — report contract stays frozen at 6 keys with the v1 manifest).
Each stage reports honestly so a cron wrapper can watch the exit code and the
report's last_date; a failing run never touches the previous good snapshot.

Documented crontab line (not committed — Gate 1 section 2.3):
    30 17 * * 1-5 cd /path/to/dtwmagic && .venv/bin/python -m src.eod_job >> data/eod/job.log 2>&1

# ponytail: ceiling is sequential single-symbol run; upgrade path is 0007's
# rank-only seam + multiprocessing for BRD 4.1's 2000-stock <90s (Phase 2).
# ponytail: ceiling is exit-code + last_date freshness monitoring; upgrade path
# is an NSE holiday calendar if a silent upstream stall becomes real (0002's).
# ponytail: ceiling is ~1h paced cold-start backfill (a snapshot needs >= 252
# rows for 0005's rolling-252 rank); upgrade path is seeding the master ledger
# from an existing store export (0002's ceiling).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from src.eod_fetch import _real_get, refresh_store
from src.snapshot import build_snapshot
from src.snapshot_v2 import build_snapshot_v2


def run_eod_job(symbol, start_date, end_date, parquet_dir, snapshot_dir, get=_real_get):
    """Run refresh_store then build_snapshot; always return the report (Gate 1 2.2)."""
    resolved = end_date if end_date is not None else date.today().isoformat()
    report = {
        "symbol": symbol,
        "end_date": resolved,
        "ok": False,
        "refresh": None,
        "snapshot": None,
        "error": None,
    }
    try:
        report["refresh"] = refresh_store(symbol, start_date, parquet_dir,
                                          get=get, end_date=resolved)
    except Exception as exc:
        report["error"] = f"refresh: {exc}"
        return report
    try:
        # Gate 1 2.6: both files must build before the manifest is reported;
        # v2 lands beside v1 at {parent}/v2 (BRD 4.4 versioned path).
        man = build_snapshot(symbol, parquet_dir, snapshot_dir)
        build_snapshot_v2(symbol, parquet_dir, Path(snapshot_dir).parent / "v2")
        report["snapshot"] = man
    except Exception as exc:
        report["error"] = f"snapshot: {exc}"
        return report
    report["ok"] = True
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m src.eod_job",
        description="Nightly EOD: fetch -> store -> static snapshot (spec 0009).",
    )
    parser.add_argument("--symbol", default="^NSEI")
    parser.add_argument("--start-date", default="2007-09-17")
    parser.add_argument("--end-date", default=None, metavar="YYYY-MM-DD",
                        help="default: today")
    parser.add_argument("--parquet-dir", default="data/parquet")
    parser.add_argument("--snapshot-dir", default="data/static/api/v1")
    args = parser.parse_args(argv)
    report = run_eod_job(args.symbol, args.start_date, args.end_date,
                         args.parquet_dir, args.snapshot_dir)
    print(json.dumps(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
