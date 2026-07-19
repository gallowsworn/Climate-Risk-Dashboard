#!/usr/bin/env python3
"""
Append a price snapshot for every non-delisted ticker in targets.json,
alongside SPY and a sector-benchmark ETF, so posture calls (accumulate/
hold/tactical/watch/hedge) can eventually be graded against what actually
happened to the price — not just whether the written thesis sounded right.

This is forward-looking only. The dashboard didn't capture prices when
each entry's posture was originally set, so there is no way to backfill
"performance since the call was made" — every ticker's baseline is
whenever this script is first run for it. A ticker's baseline resets
automatically if its posture changes (see compute_returns()), so what
gets reported is always "how has this done since we started tracking it
in its CURRENT posture," not since some earlier, different call.

Price source: Yahoo Finance's unofficial chart JSON endpoint
(query1.finance.yahoo.com/v8/finance/chart/{ticker}). This is the ONE
data source in this project that is NOT a documented, published API like
NOAA/NASA/USDA/CFTC — it's an unauthenticated endpoint Yahoo's own site
uses internally, works with just a User-Agent header, and covers equities,
funds, and thin OTC names alike (confirmed against CANE/DBA/GWRS/CSNVY and
even the delisted NIB, which correctly returns its frozen 2023-06-08 last
price). It could change or get blocked without notice. If it breaks, swap
the URL/parsing in fetch_price() for a documented alternative — the rest
of this script doesn't care where the number comes from.

Benchmarking: each ticker is compared against BOTH SPY (broad market) and
a sector ETF where one reasonably exists (see SECTOR_BENCHMARKS below).
About a third of sectors here (soft commodities, deep-sea mining,
aquaculture inputs) have no clean sector ETF and compare against SPY only
— that's a real gap in the benchmark, not an oversight, and is left
explicit rather than forced into a bad-fit ETF.

Unlike the fetch_*.py caches (enso-status.json, drought-status.json, etc.,
which are disposable point-in-time snapshots and gitignored),
data/posture-log.json is NOT gitignored — it accumulates an irreplaceable
time series. Once a run's snapshot date passes, there's no way to
regenerate that exact "posture as of that date" pairing later, so it's
tracked in git like the rest of the research record.

Usage:
    python log_posture_performance.py
"""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
REQUEST_DELAY_SECONDS = 0.4  # be polite to an unofficial/unauthenticated endpoint

BROAD_MARKET_BENCHMARK = "SPY"

# Sector -> single most-relevant sector ETF, confirmed to exist on Yahoo's
# chart endpoint. Deliberately left unmapped (None) where no ETF is a
# reasonable fit rather than forcing a loose match.
SECTOR_BENCHMARKS = {
    "Ag trading": "MOO",              # VanEck Agribusiness ETF
    "Agriculture inputs": "MOO",
    "Aquaculture inputs": None,       # no clean sector ETF exists
    "Consumer staples": "XLP",        # Consumer Staples Select Sector SPDR
    "Critical minerals": "REMX",      # VanEck Rare Earth/Strategic Metals ETF
    "Deep-sea mining": None,          # no sector ETF exists (TMC is a single-name story)
    "Energy": "XLE",                  # Energy Select Sector SPDR
    "Fertilizer": "XLB",              # Materials Select Sector SPDR (closest available proxy)
    "Grid infrastructure": "GRID",    # First Trust NASDAQ Clean Edge Smart Grid Infrastructure ETF
    "Homebuilding": "ITB",            # iShares US Home Construction ETF
    "Insurance": "KIE",               # SPDR S&P Insurance ETF
    "Mining": "XME",                  # SPDR S&P Metals & Mining ETF
    "Resilience & rebuild": "XHB",    # SPDR S&P Homebuilders ETF (closest available proxy)
    "Soft commodities": None,         # these tickers ARE commodity funds; no equity sector ETF fits
    "Utilities": "XLU",               # Utilities Select Sector SPDR
    "Water infrastructure": "PHO",    # Invesco Water Resources ETF
}

ROOT = Path(__file__).resolve().parent.parent
TARGETS_PATH = ROOT / "data" / "targets.json"
OUT_PATH = ROOT / "data" / "posture-log.json"
REFRESH_LOG_PATH = ROOT / "data" / "refresh-log.json"


def fetch_price(ticker):
    url = CHART_URL.format(ticker=ticker)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (climate-risk-dashboard/1.0)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    result = payload["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    timestamps = result["timestamp"]
    for ts, px in zip(reversed(timestamps), reversed(closes)):
        if px is not None:
            return round(px, 4), datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
    raise ValueError("no non-null close price in range")


def load_targets():
    return json.loads(TARGETS_PATH.read_text(encoding="utf-8"))


def load_log():
    if OUT_PATH.exists():
        return json.loads(OUT_PATH.read_text(encoding="utf-8"))
    return {"sector_benchmark_map": SECTOR_BENCHMARKS, "runs": []}


def update_refresh_log():
    if not REFRESH_LOG_PATH.exists():
        return
    log = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8"))
    for dt in log.get("data_types", []):
        if dt["type"] == "posture_performance_log":
            dt["last_run"] = datetime.now().isoformat(timespec="seconds")
    REFRESH_LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def compute_returns(runs, ticker):
    """Baseline = the earliest run where this ticker appears with its CURRENT
    posture, walking backward from the latest run until the posture changes.
    Returns None if there's only one run so far (nothing to compare yet)."""
    ticker_runs = [
        (r["date"], next(t for t in r["tickers"] if t["ticker"] == ticker))
        for r in runs if any(t["ticker"] == ticker for t in r["tickers"])
    ]
    if len(ticker_runs) < 2:
        return None
    current_posture = ticker_runs[-1][1]["posture"]
    baseline_date, baseline_row = ticker_runs[-1]
    for d, row in reversed(ticker_runs):
        if row["posture"] != current_posture:
            break
        baseline_date, baseline_row = d, row
    latest_date, latest_row = ticker_runs[-1]
    if baseline_date == latest_date:
        return None

    def pct(a, b):
        return round((b - a) / a * 100.0, 2) if a else None

    ticker_return = pct(baseline_row["price"], latest_row["price"])
    spy_return = pct(baseline_row["spy_price"], latest_row["spy_price"])
    result = {
        "baseline_date": baseline_date,
        "latest_date": latest_date,
        "posture_held_since": baseline_date,
        "ticker_return_pct": ticker_return,
        "spy_return_pct": spy_return,
        "alpha_vs_spy_pct": round(ticker_return - spy_return, 2) if ticker_return is not None and spy_return is not None else None,
    }
    sb_ticker = baseline_row.get("sector_benchmark")
    if sb_ticker and baseline_row.get("sector_benchmark_price") and latest_row.get("sector_benchmark_price"):
        sector_return = pct(baseline_row["sector_benchmark_price"], latest_row["sector_benchmark_price"])
        result["sector_benchmark"] = sb_ticker
        result["sector_benchmark_return_pct"] = sector_return
        result["alpha_vs_sector_pct"] = round(ticker_return - sector_return, 2) if ticker_return is not None and sector_return is not None else None
    return result


def main():
    targets = load_targets()
    live_targets = [t for t in targets if t.get("posture") != "delisted"]

    needed_benchmarks = {BROAD_MARKET_BENCHMARK}
    for t in live_targets:
        sb = SECTOR_BENCHMARKS.get(t["sector"])
        if sb:
            needed_benchmarks.add(sb)

    print(f"Fetching prices for {len(live_targets)} tickers + {len(needed_benchmarks)} benchmarks...")

    benchmark_prices = {}
    for sym in sorted(needed_benchmarks):
        try:
            px, asof = fetch_price(sym)
            benchmark_prices[sym] = px
            print(f"  {sym:>6}: {px} (as of {asof})")
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as e:
            print(f"  {sym:>6}: FAILED ({e})", file=sys.stderr)
        time.sleep(REQUEST_DELAY_SECONDS)

    if BROAD_MARKET_BENCHMARK not in benchmark_prices:
        print("Could not fetch SPY — aborting run (every comparison needs a market baseline).", file=sys.stderr)
        sys.exit(1)

    run_tickers = []
    failures = []
    for t in live_targets:
        ticker = t["ticker"]
        try:
            px, asof = fetch_price(ticker)
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as e:
            print(f"  {ticker:>6}: FAILED ({e})", file=sys.stderr)
            failures.append(ticker)
            time.sleep(REQUEST_DELAY_SECONDS)
            continue
        sb = SECTOR_BENCHMARKS.get(t["sector"])
        row = {
            "ticker": ticker,
            "posture": t["posture"],
            "sector": t["sector"],
            "price": px,
            "price_as_of": asof,
            "spy_price": benchmark_prices.get(BROAD_MARKET_BENCHMARK),
            "sector_benchmark": sb,
            "sector_benchmark_price": benchmark_prices.get(sb) if sb else None,
        }
        run_tickers.append(row)
        time.sleep(REQUEST_DELAY_SECONDS)

    log = load_log()
    run = {
        "date": date.today().isoformat(),
        "benchmark_prices": benchmark_prices,
        "tickers": run_tickers,
        "failed_tickers": failures,
    }
    log["runs"].append(run)
    log["sector_benchmark_map"] = SECTOR_BENCHMARKS
    OUT_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")
    update_refresh_log()

    print(f"\nWrote {OUT_PATH.relative_to(ROOT)} — run #{len(log['runs'])} for {date.today().isoformat()}")
    if failures:
        print(f"Failed to fetch: {', '.join(failures)}")

    if len(log["runs"]) < 2:
        print("\nThis is the first snapshot — no performance deltas yet. Run again later (weekly/monthly) to start seeing returns since baseline.")
        return

    print("\n=== Performance since posture baseline ===")
    for t in run_tickers:
        r = compute_returns(log["runs"], t["ticker"])
        if r is None:
            continue
        sector_part = ""
        if "sector_benchmark_return_pct" in r:
            sector_part = f"  |  {r['sector_benchmark']} {r['sector_benchmark_return_pct']:>6}%  (alpha {r['alpha_vs_sector_pct']:>6}%)"
        print(
            f"  {t['ticker']:>6} ({t['posture']:>10}, since {r['baseline_date']}): "
            f"{r['ticker_return_pct']:>6}%  |  SPY {r['spy_return_pct']:>6}%  (alpha {r['alpha_vs_spy_pct']:>6}%)"
            f"{sector_part}"
        )


if __name__ == "__main__":
    main()
