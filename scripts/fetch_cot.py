#!/usr/bin/env python3
"""
Pull the latest CFTC Commitment of Traders (Legacy, Futures Only) positioning
for the commodity-linked tickers in targets.json, via CFTC's public Socrata
API. Stdlib-only (urllib), no API key required (unauthenticated Socrata
requests are rate-limited but functional for weekly use).

Only covers tickers with a direct single-commodity futures market (cocoa,
coffee, sugar, natural gas). Diversified baskets (DBA) and non-futures names
are out of scope for this script by design.

Usage:
    python fetch_cot.py
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

SOCRATA_BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

# ticker -> CFTC "market_and_exchange_names" value (exact match required by the API).
# CFTC renames these strings occasionally (e.g. natural gas went from "NATURAL GAS -
# NEW YORK MERCANTILE EXCHANGE" to "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE" at
# some point after Feb 2022, silently orphaning the old string) - if a ticker starts
# returning stale dates, re-check the current name via a `like` query before assuming
# the API is broken.
TICKER_TO_MARKET = {
    "NIB": "COCOA - ICE FUTURES U.S.",
    "JO": "COFFEE C - ICE FUTURES U.S.",
    "CANE": "SUGAR NO. 11 - ICE FUTURES U.S.",
    "UNG": "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE",
}

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "cot-cache.json"
REFRESH_LOG_PATH = ROOT / "data" / "refresh-log.json"


def fetch_latest(market_name):
    params = {
        "$where": f"market_and_exchange_names='{market_name}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": "1",
    }
    url = f"{SOCRATA_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "climate-risk-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        rows = json.loads(resp.read().decode("utf-8"))
    return rows[0] if rows else None


def summarize(row):
    def num(key):
        try:
            return float(row.get(key, 0))
        except (TypeError, ValueError):
            return 0.0

    noncomm_long = num("noncomm_positions_long_all")
    noncomm_short = num("noncomm_positions_short_all")
    net_spec = noncomm_long - noncomm_short

    return {
        "report_date": row.get("report_date_as_yyyy_mm_dd"),
        "noncommercial_long": noncomm_long,
        "noncommercial_short": noncomm_short,
        "net_speculative_position": net_spec,
        "net_speculative_stance": "net long" if net_spec > 0 else ("net short" if net_spec < 0 else "flat"),
        "open_interest_all": num("open_interest_all"),
    }


def update_refresh_log():
    if not REFRESH_LOG_PATH.exists():
        return
    log = json.loads(REFRESH_LOG_PATH.read_text(encoding="utf-8"))
    for dt in log.get("data_types", []):
        if dt["type"] == "futures_positioning_cot":
            dt["last_run"] = datetime.now().isoformat(timespec="seconds")
    REFRESH_LOG_PATH.write_text(json.dumps(log, indent=2), encoding="utf-8")


def main():
    results = {}
    had_error = False
    for ticker, market in TICKER_TO_MARKET.items():
        try:
            row = fetch_latest(market)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"[{ticker}] fetch failed: {e}", file=sys.stderr)
            had_error = True
            continue
        if row is None:
            print(f"[{ticker}] no rows returned for market '{market}' — CFTC may have renamed it.", file=sys.stderr)
            had_error = True
            continue
        summary = summarize(row)
        results[ticker] = summary
        print(f"[{ticker:6s}] {summary['report_date']}  net spec: {summary['net_speculative_position']:+.0f} "
              f"({summary['net_speculative_stance']})")

    if results:
        out = {"fetched_on": date.today().isoformat(), "source": SOCRATA_BASE, "positions": results}
        OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
        update_refresh_log()
        print(f"Wrote {OUT_PATH.relative_to(ROOT)}")

    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
