#!/usr/bin/env python3
"""
Pull NOAA CO-OPS monthly mean sea level for a set of tide gauge stations
relevant to this dataset's coastal entries, and compute a simple linear
trend (mm/yr) locally. Stdlib-only (urllib), no API key required.

Note: NOAA's dedicated "sea level trends" derived-product endpoint
(api.tidesandcurrents.noaa.gov/dpapi/...) returned 502 Bad Gateway during
testing — appears to be down/deprecated, not an auth or environment issue.
This script uses the primary, actively-maintained CO-OPS datagetter API
(monthly_mean product) instead and replicates NOAA's own trend methodology
(linear regression over the full available record) rather than depending on
the broken derived-product endpoint.

Usage:
    python fetch_sea_level.py
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

DATAGETTER_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# Station ID -> (name, relevance). Chosen for entries with sea_level_coastal /
# managed_retreat exposure (LEN, BLDR) — FL and CA coastal markets.
STATIONS = {
    "8723214": "Virginia Key, FL (Miami area)",
    "8724580": "Key West, FL",
    "9410660": "Los Angeles, CA",
    "9414290": "San Francisco, CA",
}

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "sea-level-status.json"
REFRESH_LOG_PATH = ROOT / "data" / "refresh-log.json"


def fetch_monthly_mean(station_id, begin_year, end_year):
    params = {
        "station": station_id,
        "product": "monthly_mean",
        "datum": "STND",
        "time_zone": "lst",
        "units": "metric",
        "format": "json",
        "begin_date": f"{begin_year}0101",
        "end_date": f"{end_year}1231",
    }
    url = f"{DATAGETTER_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "climate-risk-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def linear_trend_mm_per_year(points):
    """points: list of (decimal_year, msl_meters). Returns slope in mm/yr."""
    n = len(points)
    if n < 2:
        return None
    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in points)
    den = sum((x - mean_x) ** 2 for x, y in points)
    if den == 0:
        return None
    slope_m_per_year = num / den
    return round(slope_m_per_year * 1000, 2)


def update_refresh_log():
    if not REFRESH_LOG_PATH.exists():
        return
    log = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8"))
    for dt in log.get("data_types", []):
        if dt["type"] == "sea_level_trend":
            dt["last_run"] = datetime.now().isoformat(timespec="seconds")
    REFRESH_LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def main():
    this_year = date.today().year
    results = {}
    had_error = False

    for station_id, label in STATIONS.items():
        try:
            payload = fetch_monthly_mean(station_id, this_year - 30, this_year)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"[{station_id}] fetch failed: {e}", file=sys.stderr)
            had_error = True
            continue

        data = payload.get("data")
        if not data:
            print(f"[{station_id}] no monthly_mean data returned ({label})", file=sys.stderr)
            had_error = True
            continue

        points = []
        for row in data:
            try:
                year, month = int(row["year"]), int(row["month"])
                msl = float(row["MSL"])
            except (KeyError, ValueError, TypeError):
                continue
            points.append((year + (month - 0.5) / 12, msl))

        trend = linear_trend_mm_per_year(points)
        results[station_id] = {
            "label": label,
            "n_months": len(points),
            "period": f"{points[0][0]:.0f}-{points[-1][0]:.0f}" if points else None,
            "trend_mm_per_year": trend,
        }
        print(f"[{station_id:8s}] {label:30s} {trend:+.2f} mm/yr (n={len(points)} months)" if trend is not None else f"[{station_id}] {label}: insufficient data")

    if results:
        out = {
            "fetched_on": date.today().isoformat(),
            "source": "NOAA CO-OPS datagetter API, monthly_mean product (trend computed locally via linear regression)",
            "stations": results,
            "note": "Trend is a local linear-regression estimate over the available record (up to 30yr), not NOAA's own published sea-level-trends product (that derived-product endpoint was returning 502 as of this build). Directionally consistent with NOAA's methodology but treat exact mm/yr as approximate.",
        }
        OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
        update_refresh_log()
        print(f"Wrote {OUT_PATH.relative_to(ROOT)}")

    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
