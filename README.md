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

Five fund/ETF/ETN-type tickers (NIB, JO, CANE, DBA, UNG) have no traditional
sell-side equity coverage by design — expected, not a gap. Only two of the
five (NIB, JO) are iPath products; CANE and DBA are unrelated issuers.

## `driver_dominance`

A field answering a different question than any other in the schema: is the
climate/ecological driver this ticker is *tagged* with actually the reason
its price is moving *right now* — or has something else (a war, an M&A deal,
a mine accident, a sector cycle) taken over as the real story? Three values,
plus a fourth for delisted tickers:

- **dominant** — the tagged driver genuinely is the binding variable right now
- **contested** — real tension, two factors are plausibly co-dominant
- **secondary** — a clearly different, named factor is what's actually moving the thesis
- **n/a** — delisted, no current thesis to evaluate (NIB, JO)

This exists because an independent review (see below) found that a growing
share of entries kept admitting, in their own notes, that the tagged driver
wasn't the real story — without the schema ever acting on that admission.
It's deliberately cheap to maintain: set from the same reasoning already
going into `notes.signal_check`, not a separate research task. Distribution
as of 2026-07-18, across the 26 non-delisted tickers: **8 dominant / 2
contested / 16 secondary** — only about 31% of the dataset currently has its
tagged driver as the actual binding variable. That fraction is surfaced as
its own dashboard stat tile so it can't quietly drift without being visible.
`secondary`/`n/a` entries are dimmed (not hidden) in the dashboard — they
still have research value, they're just not the headline story right now.

## Data integrity note: NIB and JO are both delisted (confirmed 2026-07-18)

While researching analyst consensus, cross-checking surfaced a real problem
predating this build: **NIB (iPath Bloomberg Cocoa Subindex ETN) and JO
(iPath Coffee ETN) were both redeemed/delisted by Barclays on the SAME date
— June 14, 2023 — in the SAME 21-ETN redemption wave** (announced Apr 18,
2023; trading suspended Jun 8, 2023). Both had been sitting in this dataset
as live tactical positions for the entire build. Confirmed via Yahoo
Finance/TipRanks (NIB) and the original Barclays/Businesswire redemption
announcement, which explicitly names the coffee ETN among the products
closing (JO) — an earlier pass on JO had only gotten as far as "likely
delisted, exact wave unconfirmed" before this was pinned down. `notes.core`
on both entries now leads with an unmissable delisted warning; both should
be treated as historical/reference content only, not actionable positions.

**Known gap, not yet fixed:** `posture`/`direction` on both entries still
read `"tactical"`/`"benefit"` — the schema has no "inactive" state, so every
filter, stat tile, and badge in the dashboard currently presents these two
dead instruments as live positions; only the prose in `notes.core` says
otherwise. See CLAUDE.md's "Known open items" for the proposed fix (a 6th
posture value or an `active` flag) — not implemented yet, pending a decision
on the right schema shape.

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
| Drought status | Weekly | NIDIS/US Drought Monitor — `scripts/fetch_drought.py` |
| Sea level trend | Quarterly (slow-moving) | NOAA CO-OPS tide gauges — `scripts/fetch_sea_level.py` |
| Global temperature anomaly | Monthly | NASA GISTEMP — `scripts/fetch_temp_anomaly.py` |
| Wildfire (active-fire detections) | On-demand | NASA FIRMS, California — `scripts/fetch_wildfire.py` (needs a free `NASA_FIRMS_MAP_KEY`) |

## Earth-science data sources (added 2026-07-18)

Three new fetch scripts pull primary government/institutional climate data,
following the same stdlib-only, no-API-key pattern as `fetch_enso.py`:

- **`fetch_drought.py`** — NIDIS/US Drought Monitor severity (D0-D4, % of
  CONUS area), weekly. Used to replace aggregator-sourced wildfire/drought
  claims (CB, AWK, XYL, CTVA) with a primary federal measurement.
- **`fetch_sea_level.py`** — NOAA CO-OPS tide-gauge monthly means, with the
  30-year linear trend (mm/yr) computed locally rather than relying on
  NOAA's own "sea level trends" derived-product endpoint, which was
  returning 502 Bad Gateway during testing (likely down/deprecated, not an
  auth issue). This filled a total void: `sea_level_coastal` previously had
  *zero* physical measurement behind it (LEN, BLDR), only insurance-market
  proxies. Real finding: Florida coastal gauges (Miami +6.81mm/yr, Key West
  +6.14mm/yr) are rising more than twice as fast as California ones (LA
  +2.58mm/yr, SF +2.87mm/yr) — a genuine tension with LEN's thesis, since
  Florida's *insurance* pricing is currently improving even as its
  *physical* sea-level risk accelerates faster than California's. Flagged
  explicitly in LEN's `signal_check`, not resolved.
- **`fetch_temp_anomaly.py`** — NASA GISTEMP global land-ocean temperature
  anomaly. Used as brief corroborating context for the `secular_warming`
  tag on GNRC and NEE specifically (their tagged driver has a genuine
  multi-decade component, unlike CF/NTR where a near-term war dominates).

**NIFC/InciWeb wildfire *perimeter* data was assessed and not built.** Every
endpoint tested on NIFC's ArcGIS org (including metadata-only requests)
returned `Token Required` — a real, current access restriction, not
something specific to this project's queries, and it breaks the no-auth
pattern every other script here follows.

- **`fetch_wildfire.py`** — built instead using **NASA FIRMS**, which
  requires a free `MAP_KEY` (email only, no account/password, delivered
  instantly at [firms.modaps.eosdis.nasa.gov/api/map_key](https://firms.modaps.eosdis.nasa.gov/api/map_key/) —
  set it as the `NASA_FIRMS_MAP_KEY` environment variable before running).
  This returns point-level active-fire *detections* (satellite hotspots),
  not fire *perimeters*/acreage like NIFC would have — a coarser but still
  genuinely primary data type, for a California bounding box relevant to
  CB/BLDR/LEN. Not yet run against a real key as of this writing.

**Deliberately not applied to every `secular_warming`/`wildfire_drought_baseline`/`water_scarcity` entry.**
Per Fable's own advice, new primary data was NOT added to CF, NTR, UNG, or
HD — their current stories (a Hormuz-linked gas shock, a pending merger,
futures-roll mechanics, general consumer health) aren't actually about the
tagged climate driver right now (see `driver_dominance: secondary` on
each), so better climate data there would be sourcing rigor spent on the
wrong variable.

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
