#!/usr/bin/env python3
"""
Pull NASA GISTEMP v4 global land-ocean temperature anomaly data. Stdlib-only
(urllib), no API key required.

Note: NOAA NCEI's own "Climate at a Glance" global time series (the other
commonly-cited source for this same measurement) was not reachable from this
dev environment during testing (requests hung/timed out via both PowerShell
and Python urllib, despite the endpoint being confirmed live via a browser-
based fetch) — GISTEMP was used instead as a working equivalent. If NCEI
works fine on your machine, either source is a legitimate primary reference
for the secular_warming driver; no need to switch.

Usage:
    python fetch_temp_anomaly.py
"""
import csv
import io
import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

GISTEMP_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "temp-anomaly-status.json"
REFRESH_LOG_PATH = ROOT / "data" / "refresh-log.json"


def fetch_csv_text():
    req = urllib.request.Request(GISTEMP_URL, headers={"User-Agent": "climate-risk-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def parse_annual(text):
    # First line is a title, not a header — skip it.
    lines = text.splitlines()[1:]
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    rows = []
    for row in reader:
        try:
            year = int(row["Year"])
        except (KeyError, ValueError):
            continue
        jd = row.get("J-D", "").strip()
        if jd in ("", "***"):
            continue
        try:
            rows.append({"year": year, "annual_anomaly_c": float(jd)})
        except ValueError:
            continue
    return rows


def update_refresh_log():
    if not REFRESH_LOG_PATH.exists():
        return
    log = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8"))
    for dt in log.get("data_types", []):
        if dt["type"] == "temp_anomaly":
            dt["last_run"] = datetime.now().isoformat(timespec="seconds")
    REFRESH_LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def main():
    try:
        text = fetch_csv_text()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"Failed to fetch GISTEMP data: {e}", file=sys.stderr)
        sys.exit(1)

    rows = parse_annual(text)
    if not rows:
        print("Fetched GISTEMP data but could not parse any annual rows — NASA may have changed the CSV format.", file=sys.stderr)
        sys.exit(1)

    rows.sort(key=lambda r: r["year"])
    latest = rows[-1]
    last_10 = rows[-10:]
    decade_avg = sum(r["annual_anomaly_c"] for r in last_10) / len(last_10)

    result = {
        "fetched_on": date.today().isoformat(),
        "source": "NASA GISS Surface Temperature Analysis (GISTEMP v4), " + GISTEMP_URL,
        "baseline_period": "1951-1980",
        "latest_year": latest["year"],
        "latest_annual_anomaly_c": latest["annual_anomaly_c"],
        "trailing_10yr_avg_anomaly_c": round(decade_avg, 3),
        "trailing_10yr": last_10,
        "note": "Global land-ocean annual mean temperature anomaly (deg C) vs. the 1951-1980 baseline. Current year's J-D (Jan-Dec) figure may be a partial-year average if fetched before December.",
    }

    OUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    update_refresh_log()

    print(f"Latest GISTEMP annual anomaly ({latest['year']}): {latest['annual_anomaly_c']:+.2f}C vs 1951-1980 baseline")
    print(f"Trailing 10-year average: {decade_avg:+.3f}C")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
