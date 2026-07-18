#!/usr/bin/env python3
"""
Flag targets.json entries (and refresh-log.json data types) that are past
their staleness window.

Usage:
    python check_staleness.py            # human-readable report
    python check_staleness.py --json      # machine-readable report (for the dashboard)
"""
import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS_PATH = ROOT / "data" / "targets.json"
REFRESH_LOG_PATH = ROOT / "data" / "refresh-log.json"


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def check_targets(today):
    targets = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    results = []
    for t in targets:
        last_verified = parse_date(t["last_verified"])
        age_days = (today - last_verified).days
        stale = age_days > t["confidence_stale_after_days"]
        results.append({
            "ticker": t["ticker"],
            "name": t["name"],
            "last_verified": t["last_verified"],
            "age_days": age_days,
            "confidence_stale_after_days": t["confidence_stale_after_days"],
            "stale": stale,
        })
    return results


def check_refresh_log():
    if not REFRESH_LOG_PATH.exists():
        return []
    log = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8"))
    results = []
    for dt in log.get("data_types", []):
        results.append({
            "type": dt["type"],
            "cadence": dt["cadence"],
            "last_run": dt.get("last_run"),
            "never_run": dt.get("last_run") is None,
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a printed report")
    args = parser.parse_args()

    today = date.today()
    target_results = check_targets(today)
    refresh_results = check_refresh_log()

    stale_targets = [r for r in target_results if r["stale"]]
    # Only a "never run" data type with an automated fetch script represents an
    # actionable gap. A manual-research-only category (fetch_script: null, e.g.
    # insurance_reinsurance_loss_estimates) has no automated way to ever be
    # satisfied, so it must not permanently pin the exit code to 1.
    log = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8")) if REFRESH_LOG_PATH.exists() else {"data_types": []}
    automatable_never_run = [
        r for r, dt in zip(refresh_results, log.get("data_types", []))
        if r["never_run"] and dt.get("fetch_script")
    ]
    exit_code = 1 if (stale_targets or automatable_never_run) else 0

    if args.json:
        json.dump({
            "checked_on": today.isoformat(),
            "targets": target_results,
            "refresh_log": refresh_results,
        }, sys.stdout, indent=2)
        print()
        sys.exit(exit_code)

    print(f"Staleness check — {today.isoformat()}")
    print("=" * 60)
    if stale_targets:
        print(f"\n{len(stale_targets)} STALE target(s) (past confidence_stale_after_days):")
        for r in sorted(stale_targets, key=lambda r: -r["age_days"]):
            print(f"  [{r['ticker']:6s}] {r['name']:28s} verified {r['last_verified']} "
                  f"({r['age_days']}d old, window {r['confidence_stale_after_days']}d)")
    else:
        print("\nNo targets are past their staleness window.")

    print(f"\nTotal targets checked: {len(target_results)}")

    if refresh_results:
        print("\nData-type refresh log:")
        for r in refresh_results:
            status = "NEVER RUN" if r["never_run"] else f"last run {r['last_run']}"
            print(f"  [{r['type']:32s}] cadence={r['cadence']:24s} {status}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
