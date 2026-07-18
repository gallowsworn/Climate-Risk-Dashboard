# Climate & Ecological Risk Investment Dashboard

Personal investing research tool. Screens US-market-accessible investment
targets against climate/ecological risk drivers — El Nino 2026-27 is the
current near-term stress test inside a broader multi-driver framework, not
the sole organizing principle.

**Not financial advice.** This is a structured research and decision-support
tool, not a signal generator. Every entry needs a defensible rationale and a
named source; "I'm not sure" is a valid field value.

## Posture values

`posture` has five values — the dashboard's Legend panel (top of the filter
bar) and hover/focus tooltips on each badge show these same definitions
in-app:

- **hold** — maintain any existing position; not an active buy signal right now
- **accumulate** — stronger conviction; actively building or adding to a position
- **tactical** — sized for a specific, time-limited catalyst window, not a long-term hold
- **watch** — no position yet; monitoring for a clearer signal before acting
- **hedge** — sized to offset/protect against this risk, not to profit from it directly

`hold` vs. `accumulate` is the one nuance worth calling out: `hold` means the
thesis is real but currently fragile, reversible, or just-revised (e.g. CF's
Hormuz-driven pricing power could reverse as fast as the conflict created
it; GNRC's growth driver just shifted from storms to data centers and needs
more confirmation). `accumulate` means the thesis is structural,
well-evidenced, and currently reinforcing (e.g. AWK/XYL's rate-base
compounding, MP's DoD-backed reshoring position strengthened by China's own
retaliatory export controls).

## `analyst_consensus_check`

A field for cross-checking the dashboard's own `direction`/`posture` call
against sell-side Wall Street sentiment — deliberately kept separate from
(never blended into) the dashboard's own judgment fields, since sell-side
consensus is a lagging, herd signal with real structural bias (sell-side
rarely rates "Sell"). Prefers named industry-specialist analysts and
track-record-weighted "top analyst" consensus (e.g. TipRanks' accuracy-
filtered screen) over raw unfiltered ratings where findable; states plainly
when it can only find raw consensus. Each entry ends with an explicit
**CORROBORATES** / **DIVERGES** / **MIXED-UNCLEAR** verdict against the
dashboard's own call — divergence is flagged, not resolved in the dashboard's
favor. Populated 2026-07-18 for all 28 tickers via three background research
passes grouped by sector.

Two ETF/ETN-type tickers (UNG, and the three iPath products below) have no
traditional sell-side equity coverage by design — expected, not a gap.

## Data integrity note: NIB and JO trading status (found 2026-07-18)

While researching analyst consensus, cross-checking surfaced a real problem
predating this build: **NIB (iPath Bloomberg Cocoa Subindex ETN) was
redeemed/delisted by Barclays on June 14, 2023** — confirmed via Yahoo
Finance and TipRanks, both showing "no longer active." It had been sitting
in this dataset as a live tactical position the whole time; `notes.core` now
leads with an unmissable delisted warning, and it should be treated as
historical/reference content only, not an actionable position.

**JO (iPath Coffee ETN) is very likely delisted too (2026-07-18, high
confidence but not fully confirmed)** — 0 trading volume against a 10.82K
daily average, and multiple sources now describe it as "no longer active"
with stale pricing. Barclays ran two further iPath redemption waves after
2023 (18 ETNs in June 2024, 4 more in June 2025); which one JO fell into
wasn't pinned down, but the pattern matches NIB's confirmed-delisted profile
closely enough that `notes.core` treats it the same way — historical
reference only, not an actionable position, pending a final broker check.

**CANE (Teucrium) and DBA (Invesco) are unaffected** — different issuers,
both confirmed actively trading.

## Layout

```
/data
  targets.json          28 targets (20 from the original chat build + TMC, MP,
                         NEE, FLNC, PWR, CTVA, CSNVY, GWRS)
  driver-taxonomy.json  the driver framework (Section 3 of the build brief)
  refresh-log.json      cadence + last-run tracking per data type
/scripts
  fetch_cot.py           pulls CFTC Commitment of Traders positioning (weekly)
  fetch_enso.py          pulls NOAA CPC ONI data, classifies ENSO phase (monthly)
  check_staleness.py     flags targets/data types past their staleness window
  serve.ps1              zero-dependency local static server (see below)
/dashboard
  index.html             filterable dashboard, reads data/targets.json live
```

## Running the dashboard

Browsers block `fetch()` of local files opened via `file://`, so the
dashboard needs to be served over HTTP:

```
powershell -ExecutionPolicy Bypass -File scripts\serve.ps1
```

then open `http://localhost:8000/dashboard/`. This uses .NET's
`HttpListener` directly — no Python or Node install required. If you do have
Python or Node available, `python -m http.server 8000` from the project
root (or the VS Code "Live Server" extension) works the same way.

## Running the scripts

`scripts/*.py` require Python 3, installed via winget on 2026-07-17
(`Python.Python.3.12`). They're stdlib-only, no `pip install` needed. Note:
in this dev environment, a fresh terminal session must refresh `PATH` from
the registry before `python` resolves (`$env:Path =
[System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
[System.Environment]::GetEnvironmentVariable("Path","User")` in PowerShell)
since the shell was already open when Python was installed.

```
python scripts/check_staleness.py            # human-readable staleness report
python scripts/check_staleness.py --json      # machine-readable, for tooling
python scripts/fetch_enso.py                  # updates data/enso-status.json
python scripts/fetch_cot.py                   # updates data/cot-cache.json (NIB/JO/CANE/UNG only)
```

## Data status as of this build

**A full verification pass ran on 2026-07-17.** All 22 entries in
`targets.json` now carry `last_verified: "2026-07-17"` with real, named
current sources (SEC filings, company earnings calls, NOAA/EIA/USDA/CFTC
data, and dated trade-press reporting) — replacing the `2026-01-01`
placeholder used at initial build time. Live pulls also ran:
NOAA's ONI reading is **+1.0 (El Nino)** as of AMJ 2026, and CFTC COT data
(week of 2026-07-07) is cached in `data/cot-cache.json`.

The research pass surfaced several corrections to the original chat-build
theses, each flagged inline in the relevant entry's `signal_check` field
rather than silently smoothed over:

- **MDLZ was wrongly assumed to share Hershey's cocoa-hedging cushion.**
  Mondelez's Q1 2026 gross margin actually fell 580bps (hedges are
  currently a headwind), the opposite of Hershey's improvement to 39.4%.
- **GNRC's growth driver has shifted from storms to data centers.** The
  2026 Atlantic hurricane season is forecast/observed as quiet (El
  Nino-suppressed), while C&I sales (+28%, data-center demand) now drive
  growth — the storm-frequency thesis is weaker than originally framed.
- **BLDR's disaster-rebuild demand is real but small**, currently swamped
  by a broad housing-starts slump (-10% sales) — downgraded from "benefit"
  to "mixed".
- **LEN's FL and CA insurance markets are diverging**, not moving together:
  Florida rates are falling and private insurers are re-entering, while
  California's FAIR Plan is up 29% and expanding market share. The
  single "FL/CA" risk framing may now overstate Florida and understate
  California.
- **FCX's dominant near-term risk is Indonesia (Grasberg force-majeure
  guidance cut), not Peru** — don't conflate with SCCO's separate,
  concrete Peru story (Tia Maria permit revocation, 2026).
- Several commodity theses (coffee's "El Nino dryness" mechanism, cocoa's
  ENSO correlation, sugar's fundamentals-vs-positioning) turned up
  genuine internal contradictions in current reporting — see each
  ticker's `signal_check` and `backtest_check` fields rather than a
  summary here, since the nuance matters.

`check_staleness.py` now passes cleanly for all 28 targets. The
`company_hedging_valuation` and `policy_regulatory_status` rows in
`refresh-log.json` were updated to reflect this manual research pass
(no automated fetch script exists for those categories — they require
reading filings/news, not a scriptable API). `insurance_reinsurance_loss_estimates`
was not covered in this pass and is still flagged `NEVER RUN`.

**Six new targets were added** (NEE, FLNC, PWR, CTVA, CSNVY, GWRS) — see
"Candidate additions" below, now folded into the main dataset. Two are worth
flagging as thin/indirect on arrival, not just carried-forward-and-untested:

- **CTVA (Corteva)** is spinning off its seed-genetics business as a new
  company, "Vylor, Inc.," targeted for Q4 2026 — the drought-resistant-seed
  thesis this entry is built on will structurally migrate to Vylor, a
  different ticker, once that separation happens. Revisit then.
- **CSNVY (Corbion)** and **GWRS (Global Water Resources)** — the two
  "research needed" slots from the original brief — are both real but
  *indirect* plays: Corbion's fish-oil-substitute business is a
  single-digit share of company revenue wrapped in an illiquid unsponsored
  ADR; GWRS serves the Colorado River basin region but runs on groundwater
  and recycled water, not a direct river-water allocation. Both are
  `posture: watch`, not `hold` or `accumulate`, for this reason.

## Design principles carried from the original build

- Every field should be traceable to a specific, named source. Where
  evidence is thin, say so explicitly rather than smoothing it over (e.g.
  cocoa's ENSO correlation is flagged as weaker than the 2023-24 narrative
  implied; pollinator decline is *compounded by*, not *caused by*, El Nino).
- Across water rights, grid reliability, and managed retreat, the
  private-capital/market-based response consistently shows higher
  remediation confidence than the formal government policy process — weight
  "what capital is already doing" over "what has been proposed."
- `positioning_check` / `hedging_check` / `backtest_check` are for hard,
  checkable data (COT positioning, disclosed forward hedges, historical
  analog performance). `notes.signal_check` is for a qualitative conviction
  note (e.g. "this thesis was revised" or "lower conviction than the
  headline narrative implies").

## Refresh cadence

| Data type | Suggested refresh | Source |
|---|---|---|
| ENSO status | Monthly | NOAA CPC ENSO Diagnostic Discussion; cross-check WMO/JMA/BOM/C3S |
| Futures positioning (COT) | Weekly | CFTC Commitment of Traders reports |
| Company hedging/valuation | Quarterly (earnings) | SEC 10-K/10-Q, earnings call transcripts |
| Policy/regulatory status | As-announced, check monthly | EU Commission (EUDR), NOAA/BOEM (deep-sea mining), state insurance regulators, USDA/India Ministry of Commerce |
| Insurance/reinsurance loss estimates | Quarterly | Aon, Gallagher Re, Munich Re, Swiss Re reports (flag as interested-party) |

## Candidate additions (status)

All of the original brief's Section 4 candidates are now built out:

| Ticker | Name | Primary driver(s) | Status |
|---|---|---|---|
| TMC | The Metals Company | `deep_sea_mining`, `critical_minerals` | Added first, to validate the schema-fill process |
| MP | MP Materials | `critical_minerals` | Added first, to validate the schema-fill process |
| NEE | NextEra Energy | `grid_reliability`, `secular_warming` | Added 2026-07-17 |
| FLNC | Fluence Energy | `grid_reliability` | Added 2026-07-17 |
| PWR | Quanta Services | `grid_reliability`, `logistics_disruption` | Added 2026-07-17 |
| CTVA | Corteva | `water_scarcity`, `secular_warming` | Added 2026-07-17; watch for the Vylor spinoff (Q4 2026) |
| CSNVY | Corbion N.V. (unsponsored ADR) | `ecosystem_service`, `enso` | Added 2026-07-17; the resolved "research needed" pick — indirect exposure, flagged in-entry |
| GWRS | Global Water Resources | `water_rights_compact`, `water_scarcity` | Added 2026-07-17; the resolved "research needed" pick — indirect exposure, flagged in-entry |

Adding a new ticker doesn't require any dashboard code changes — it's purely
a `targets.json` addition following the schema in this README. The process
used for all of the above: research current, named-source data (directly or
via a background research agent), write the entry with an honest
`signal_check` for anything thin or contested, and it shows up in every
filter/stat automatically on next load.
