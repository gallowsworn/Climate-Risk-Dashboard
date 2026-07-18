#!/usr/bin/env python3
"""
Pull current US Drought Monitor severity statistics (CONUS + total US) from
the official NIDIS/USDM data service. Stdlib-only (urllib), no API key
required.

Weekly release (Thursdays). D0-D4 are cumulative severity categories (D0 =
Abnormally Dry through D4 = Exceptional Drought) expressed as % of area.

Usage:
    python fetch_drought.py
"""
import csv
import io
import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

USDM_URL = (
    "https://usdmdataservices.unl.edu/api/USStatistics/"
    "GetDroughtSeverityStatisticsByAreaPercent"
    "?aoi=us&startdate={start}&enddate={end}&statisticsType=1"
)

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "drought-status.json"
REFRESH_LOG_PATH = ROOT / "data" / "refresh-log.json"


def fetch_csv_text():
    today = date.today()
    # Pull a 60-day window to comfortably include the latest weekly release.
    start = today.replace(day=1)
    if today.month > 2:
        start = start.replace(month=today.month - 2)
    else:
        start = start.replace(year=today.year - 1, month=today.month + 10)
    url = USDM_URL.format(
        start=f"{start.month}/{start.day}/{start.year}",
        end=f"{today.month}/{today.day}/{today.year}",
    )
    req = urllib.request.Request(url, headers={"User-Agent": "climate-risk-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def parse_rows(text):
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def update_refresh_log():
    if not REFRESH_LOG_PATH.exists():
        return
    log = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8"))
    for dt in log.get("data_types", []):
        if dt["type"] == "drought_status":
            dt["last_run"] = datetime.now().isoformat(timespec="seconds")
    REFRESH_LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def main():
    try:
        text = fetch_csv_text()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"Failed to fetch US Drought Monitor data: {e}", file=sys.stderr)
        sys.exit(1)

    rows = parse_rows(text)
    if not rows:
        print("Fetched drought data but could not parse any rows — NIDIS may have changed the response format.", file=sys.stderr)
        sys.exit(1)

    conus_rows = [r for r in rows if r.get("AreaOfInterest") == "CONUS"]
    conus_rows.sort(key=lambda r: r["MapDate"], reverse=True)
    latest = conus_rows[0] if conus_rows else rows[0]

    result = {
        "fetched_on": date.today().isoformat(),
        "source": "https://usdmdataservices.unl.edu (NIDIS/USDM)",
        "latest_map_date": latest["MapDate"],
        "valid_start": latest["ValidStart"],
        "valid_end": latest["ValidEnd"],
        "conus_pct_any_drought_D0plus": float(latest["D0"]),
        "conus_pct_severe_D2plus": float(latest["D2"]),
        "conus_pct_extreme_D3plus": float(latest["D3"]),
        "conus_pct_exceptional_D4": float(latest["D4"]),
        "trailing_weeks": conus_rows[:6],
        "note": "D0-D4 are cumulative severity categories (% of CONUS area at or above that severity). Weekly release, Thursdays.",
    }

    OUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    update_refresh_log()

    print(f"Latest USDM ({latest['MapDate']}): D0+ {latest['D0']}% | D2+ {latest['D2']}% | D3+ {latest['D3']}% | D4 {latest['D4']}%")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
