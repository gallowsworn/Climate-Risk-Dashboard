#!/usr/bin/env python3
"""
Pull the current ONI (Oceanic Nino Index) values from NOAA CPC and derive the
current ENSO phase. Stdlib-only (urllib), no API key required.

This is a proxy for the monthly NOAA CPC ENSO Diagnostic Discussion referenced
in the build brief, not a replacement for it — the Diagnostic Discussion adds
qualitative forecaster judgment (model spread, confidence) that the raw ONI
numbers don't carry. Cross-check WMO/JMA/BOM/C3S before treating a single
month's ONI reading as decisive.

Usage:
    python fetch_enso.py
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "enso-status.json"
REFRESH_LOG_PATH = ROOT / "data" / "refresh-log.json"

EL_NINO_THRESHOLD = 0.5
LA_NINA_THRESHOLD = -0.5


def fetch_oni_text():
    req = urllib.request.Request(ONI_URL, headers={"User-Agent": "climate-risk-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def parse_oni(text):
    """oni.ascii.txt columns: SEAS YR TOTAL ANOM"""
    rows = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) != 4:
            continue
        seas, yr, total, anom = parts
        try:
            rows.append({"season": seas, "year": int(yr), "anomaly": float(anom)})
        except ValueError:
            continue
    return rows


def classify(anomaly):
    if anomaly >= EL_NINO_THRESHOLD:
        return "El Nino"
    if anomaly <= LA_NINA_THRESHOLD:
        return "La Nina"
    return "Neutral"


def update_refresh_log():
    if not REFRESH_LOG_PATH.exists():
        return
    log = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8"))
    for dt in log.get("data_types", []):
        if dt["type"] == "enso_status":
            dt["last_run"] = datetime.now().isoformat(timespec="seconds")
    REFRESH_LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def main():
    try:
        text = fetch_oni_text()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"Failed to fetch ONI data from NOAA CPC: {e}", file=sys.stderr)
        sys.exit(1)

    rows = parse_oni(text)
    if not rows:
        print("Fetched ONI data but could not parse any rows — NOAA may have changed the file format.", file=sys.stderr)
        sys.exit(1)

    latest = rows[-1]
    phase = classify(latest["anomaly"])
    last_5 = rows[-5:]

    result = {
        "fetched_on": date.today().isoformat(),
        "source": ONI_URL,
        "latest_season": latest["season"],
        "latest_year": latest["year"],
        "latest_anomaly": latest["anomaly"],
        "phase": phase,
        "trailing_seasons": last_5,
        "note": "Raw ONI reading only. Cross-check the NOAA CPC ENSO Diagnostic Discussion for forecaster confidence before acting.",
    }

    OUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    update_refresh_log()

    print(f"Latest ONI: {latest['season']} {latest['year']} = {latest['anomaly']:+.1f}  ->  {phase}")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
