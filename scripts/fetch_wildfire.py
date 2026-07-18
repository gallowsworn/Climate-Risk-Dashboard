#!/usr/bin/env python3
"""
Pull active fire detections from NASA FIRMS (Fire Information for Resource
Management System) for a California bounding box — the region relevant to
this dataset's wildfire-exposed entries (CB, BLDR, LEN). Stdlib-only
(urllib), requires a free MAP_KEY (see below) but no paid account.

Get a free MAP_KEY (email only, no account/password, delivered instantly):
    https://firms.modaps.eosdis.nasa.gov/api/map_key/

Then set it as an environment variable before running (don't hardcode a key
into this file or commit one to git):
    PowerShell:  $env:NASA_FIRMS_MAP_KEY = "your-key-here"
    Bash:        export NASA_FIRMS_MAP_KEY="your-key-here"

This was built as the alternative to NIFC/WFIGS wildfire-perimeter data,
which requires an ArcGIS auth token on every endpoint tested (see
CLAUDE.md / refresh-log.json's wildfire_perimeters row for that dead end).
FIRMS gives point-level fire *detections* (satellite hotspots), not fire
*perimeters* — a different, coarser kind of data, but still a genuine
primary source, and the free tier (5,000 requests/10min) is far more than
this project will ever need.

Usage:
    python fetch_wildfire.py
"""
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
SOURCE = "VIIRS_SNPP_NRT"  # VIIRS is higher-resolution than MODIS for active-fire detection
DAY_RANGE = 2

# California bounding box (min_lon,min_lat,max_lon,max_lat) — widen this if
# wildfire relevance expands beyond CA-tagged entries (CB, BLDR, LEN).
CALIFORNIA_BBOX = "-124.5,32.5,-114.0,42.0"

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "wildfire-status.json"
REFRESH_LOG_PATH = ROOT / "data" / "refresh-log.json"


def fetch_csv_text(map_key):
    url = f"{FIRMS_BASE}/{map_key}/{SOURCE}/{CALIFORNIA_BBOX}/{DAY_RANGE}"
    req = urllib.request.Request(url, headers={"User-Agent": "climate-risk-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8")


def update_refresh_log():
    if not REFRESH_LOG_PATH.exists():
        return
    log = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8"))
    for dt in log.get("data_types", []):
        if dt["type"] == "wildfire_perimeters":
            dt["fetch_script"] = "scripts/fetch_wildfire.py"
            dt["source"] = "NASA FIRMS (active-fire point detections, not perimeters — free MAP_KEY required)"
            dt["last_run"] = datetime.now().isoformat(timespec="seconds")
    REFRESH_LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def main():
    map_key = os.environ.get("NASA_FIRMS_MAP_KEY")
    if not map_key:
        print(
            "NASA_FIRMS_MAP_KEY environment variable is not set.\n"
            "Get a free key (email only, instant) at:\n"
            "  https://firms.modaps.eosdis.nasa.gov/api/map_key/\n"
            "Then set it: $env:NASA_FIRMS_MAP_KEY = \"your-key-here\"  (PowerShell)",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        text = fetch_csv_text(map_key)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"Failed to fetch FIRMS data: {e}", file=sys.stderr)
        sys.exit(1)

    if text.strip().lower().startswith(("invalid", "error")):
        print(f"FIRMS API returned an error (likely a bad MAP_KEY): {text[:200]}", file=sys.stderr)
        sys.exit(1)

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    total_frp = sum(float(r["frp"]) for r in rows if r.get("frp"))
    high_confidence = [r for r in rows if r.get("confidence") in ("h", "high") or (r.get("confidence", "").isdigit() and int(r["confidence"]) >= 80)]

    result = {
        "fetched_on": date.today().isoformat(),
        "source": "NASA FIRMS, VIIRS_SNPP_NRT, California bbox, trailing 2 days",
        "region_bbox": CALIFORNIA_BBOX,
        "day_range": DAY_RANGE,
        "detection_count": len(rows),
        "high_confidence_count": len(high_confidence),
        "total_fire_radiative_power_mw": round(total_frp, 1),
        "note": "Point-level active-fire detections (satellite hotspots), not fire perimeters/acreage. A rough intensity/activity proxy, not a substitute for CAL FIRE incident data — treat detection_count and total FRP as directional indicators of current fire activity in the region, not precise acreage.",
    }

    OUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    update_refresh_log()

    print(f"California, trailing {DAY_RANGE}d: {len(rows)} detections ({len(high_confidence)} high-confidence), total FRP {total_frp:.1f} MW")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
