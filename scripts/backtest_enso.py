#!/usr/bin/env python3
"""
Backtest the dashboard's most-used driver: does an El Nino episode actually
predict higher cocoa/coffee/sugar prices in the following 3-12 months?

This is the one driver in the taxonomy that's genuinely testable without
hindsight bias — ENSO is a natural cycle independent of any single company's
story, with objective phase data (NOAA's ONI) going back to 1950 and
commodity price data (World Bank Pink Sheet) back to 1960. Every other
thesis in this dataset (a specific war, a specific merger, a specific
regulatory process) is a one-off event with no historical analog to test
against — this one has ~15-20 real historical episodes to check.

Data sources (both free, no signup):
  - NOAA CPC ONI:            https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
  - World Bank Pink Sheet:   CMO-Historical-Data-Monthly.xlsx (monthly prices, 1960-present)

Dependency note: this is the ONE script in this project that isn't
stdlib-only. The World Bank file is .xlsx, and there's no reasonable way to
parse Excel from the standard library — everything else here (drought,
sea level, temp anomaly, wildfire, COT, ONI itself) stays dependency-free.
Requires: pip install openpyxl

Methodology:
  - El Nino / La Nina episodes identified via NOAA's own operational
    definition: ONI >= +0.5 (or <= -0.5) for at least 5 consecutive
    overlapping 3-month seasons. Onset = the center month of the FIRST
    season in the qualifying run (note: in real time you wouldn't confirm
    this until ~2 seasons later — this backtests the natural cycle itself,
    not a realistic real-time trading signal).
  - Forward returns computed at 3/6/9/12 months from each episode's onset,
    for cocoa, coffee (Arabica + Robusta), and sugar (world price).
  - Compared against two baselines: the unconditional forward-return
    distribution across ALL months in the price history, and the same
    measurement during La Nina episodes — so the question is "does El Nino
    look different from other conditions," not just "did prices go up."
  - Small sample size (~15-20 episodes since 1950) means this will never
    produce strong statistical proof either way. Report distributions
    (mean/median/spread), not a single number, and don't overstate
    confidence — consistent with this project's whole approach.

Usage:
    python backtest_enso.py
"""
import io
import json
import statistics
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

try:
    import openpyxl
except ImportError:
    print(
        "This script needs openpyxl (the one non-stdlib dependency in this project,\n"
        "required because the World Bank's historical commodity data is .xlsx).\n"
        "Install it with: pip install openpyxl",
        file=sys.stderr,
    )
    sys.exit(1)

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
WORLDBANK_URL = "https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx"

# Column indices in the World Bank "Monthly Prices" sheet, confirmed 2026-07-18.
# If the World Bank restructures this file, these will need re-checking.
COMMODITY_COLUMNS = {
    "cocoa": 11,
    "coffee_arabica": 12,
    "coffee_robusta": 13,
    "sugar_world": 47,
}

SEASON_CENTER_MONTH = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}

EL_NINO_THRESHOLD = 0.5
LA_NINA_THRESHOLD = -0.5
MIN_CONSECUTIVE_SEASONS = 5
HORIZONS_MONTHS = [3, 6, 9, 12]

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "enso-backtest-results.json"
REFRESH_LOG_PATH = ROOT / "data" / "refresh-log.json"


def fetch_oni_rows():
    req = urllib.request.Request(ONI_URL, headers={"User-Agent": "climate-risk-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        text = resp.read().decode("utf-8")
    rows = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) != 4:
            continue
        seas, yr, _total, anom = parts
        try:
            rows.append({"season": seas, "year": int(yr), "anomaly": float(anom)})
        except ValueError:
            continue
    return rows


def fetch_commodity_prices():
    req = urllib.request.Request(WORLDBANK_URL, headers={"User-Agent": "climate-risk-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb["Monthly Prices"]
    rows = list(ws.iter_rows(values_only=True))
    prices = {name: {} for name in COMMODITY_COLUMNS}
    for row in rows[6:]:
        date_str = row[0]
        if not date_str or "M" not in str(date_str):
            continue
        yr_str, mo_str = str(date_str).split("M")
        try:
            yr, mo = int(yr_str), int(mo_str)
        except ValueError:
            continue
        for name, col in COMMODITY_COLUMNS.items():
            val = row[col] if col < len(row) else None
            if isinstance(val, (int, float)):
                prices[name][(yr, mo)] = float(val)
    return prices


def find_episodes(oni_rows, threshold, sign):
    """sign: +1 for El Nino (anomaly >= threshold), -1 for La Nina (anomaly <= threshold)."""
    episodes = []
    run_start = None
    run_len = 0
    for i, row in enumerate(oni_rows):
        meets = (row["anomaly"] >= threshold) if sign > 0 else (row["anomaly"] <= threshold)
        if meets:
            if run_start is None:
                run_start = i
            run_len += 1
        else:
            if run_len >= MIN_CONSECUTIVE_SEASONS:
                episodes.append(oni_rows[run_start])
            run_start = None
            run_len = 0
    if run_len >= MIN_CONSECUTIVE_SEASONS:
        episodes.append(oni_rows[run_start])
    return episodes


def add_months(year, month, n):
    total = (year * 12 + (month - 1)) + n
    return total // 12, total % 12 + 1


def forward_return(prices, year, month, horizon_months):
    start = prices.get((year, month))
    ty, tm = add_months(year, month, horizon_months)
    end = prices.get((ty, tm))
    if start is None or end is None or start == 0:
        return None
    return (end - start) / start * 100.0


def summarize(returns):
    clean = [r for r in returns if r is not None]
    if not clean:
        return {"n": 0, "mean_pct": None, "median_pct": None, "stdev_pct": None}
    return {
        "n": len(clean),
        "mean_pct": round(statistics.mean(clean), 2),
        "median_pct": round(statistics.median(clean), 2),
        "stdev_pct": round(statistics.stdev(clean), 2) if len(clean) > 1 else 0.0,
    }


def update_refresh_log():
    if not REFRESH_LOG_PATH.exists():
        return
    log = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8"))
    for dt in log.get("data_types", []):
        if dt["type"] == "enso_commodity_backtest":
            dt["last_run"] = datetime.now().isoformat(timespec="seconds")
    REFRESH_LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def main():
    try:
        oni_rows = fetch_oni_rows()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"Failed to fetch ONI data: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        prices = fetch_commodity_prices()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"Failed to fetch World Bank commodity data: {e}", file=sys.stderr)
        sys.exit(1)

    el_nino_onsets = find_episodes(oni_rows, EL_NINO_THRESHOLD, +1)
    la_nina_onsets = find_episodes(oni_rows, LA_NINA_THRESHOLD, -1)

    def onset_to_ym(episode):
        return episode["year"], SEASON_CENTER_MONTH[episode["season"]]

    all_months = sorted(set(ym for series in prices.values() for ym in series))

    results = {}
    for commodity in COMMODITY_COLUMNS:
        results[commodity] = {"el_nino": {}, "la_nina": {}, "unconditional": {}}
        for h in HORIZONS_MONTHS:
            el_nino_returns = [forward_return(prices[commodity], *onset_to_ym(e), h) for e in el_nino_onsets]
            la_nina_returns = [forward_return(prices[commodity], *onset_to_ym(e), h) for e in la_nina_onsets]
            unconditional_returns = [forward_return(prices[commodity], y, m, h) for (y, m) in all_months]
            results[commodity]["el_nino"][f"{h}mo"] = summarize(el_nino_returns)
            results[commodity]["la_nina"][f"{h}mo"] = summarize(la_nina_returns)
            results[commodity]["unconditional"][f"{h}mo"] = summarize(unconditional_returns)

    output = {
        "generated_on": date.today().isoformat(),
        "methodology": (
            "El Nino/La Nina episodes per NOAA's operational definition (ONI >= +-0.5 "
            "for >=5 consecutive overlapping 3-month seasons). Onset = center month of "
            "the first qualifying season. Forward returns computed from onset at 3/6/9/12 "
            "months. Compared against the unconditional return distribution across all "
            "months in the price history (1960-present) and against La Nina onsets."
        ),
        "el_nino_episode_count": len(el_nino_onsets),
        "la_nina_episode_count": len(la_nina_onsets),
        "el_nino_onsets": [f"{e['season']} {e['year']}" for e in el_nino_onsets],
        "sources": {
            "oni": ONI_URL,
            "commodity_prices": "World Bank Pink Sheet, CMO-Historical-Data-Monthly.xlsx",
        },
        "results": results,
    }

    OUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    update_refresh_log()

    print(f"Found {len(el_nino_onsets)} El Nino episodes, {len(la_nina_onsets)} La Nina episodes since {oni_rows[0]['year']}")
    print()
    for commodity in COMMODITY_COLUMNS:
        print(f"=== {commodity} ===")
        for h in HORIZONS_MONTHS:
            en = results[commodity]["el_nino"][f"{h}mo"]
            ln = results[commodity]["la_nina"][f"{h}mo"]
            base = results[commodity]["unconditional"][f"{h}mo"]
            print(f"  {h:>2}mo:  El Nino mean {en['mean_pct']:>7}% (n={en['n']:>2})  |  "
                  f"La Nina mean {ln['mean_pct']:>7}% (n={ln['n']:>2})  |  "
                  f"Baseline mean {base['mean_pct']:>7}% (n={base['n']})")
        print()

    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
