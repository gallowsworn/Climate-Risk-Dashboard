# CLAUDE.md

Guidance for Claude Code sessions working in this repo. See [README.md](README.md) for user-facing setup/run instructions — this file is the denser, agent-facing reference: schema, conventions, history, gotchas.

## What this is

A personal investing research tool, **not financial advice**. It screens US-market-accessible stocks/ETFs/ETNs against climate/ecological risk drivers (El Nino 2026-27 is the current near-term stress test, one input among several — not the sole organizing frame). Every data field must trace to a specific, named source; thin or contested evidence is flagged explicitly in-line rather than smoothed into false confidence. That principle is the single most important thing to preserve when editing this repo.

## Layout

```
/data
  targets.json          the dataset — one object per ticker, schema below
  driver-taxonomy.json  the 13-key driver framework (key, label, time_horizon, remediation_confidence, note)
  refresh-log.json      per-data-type cadence + last-run tracking (not per-ticker — see targets.json for that)
  enso-status.json      cache written by fetch_enso.py (gitignore-able, regenerated)
  cot-cache.json         cache written by fetch_cot.py (gitignore-able, regenerated)
/scripts
  fetch_enso.py          pulls NOAA CPC ONI data (stdlib urllib, no deps), classifies ENSO phase
  fetch_cot.py            pulls CFTC Commitment of Traders positioning for NIB/JO/CANE/UNG (stdlib urllib)
  check_staleness.py     flags targets.json entries / refresh-log.json rows past their staleness window
  serve.ps1              zero-dependency PowerShell static file server (see "Dev environment" below for why this exists)
/dashboard
  index.html              single-file dashboard: fetches ../data/*.json, filters/renders client-side, no build step
README.md                 user-facing setup, run instructions, posture definitions, changelog-style "data status" notes
CLAUDE.md                 this file
```

There is no build step, no package.json, no server-side code. `dashboard/index.html` is plain HTML/CSS/JS that fetches the JSON files at runtime.

## Data schema (`data/targets.json`)

One object per ticker:

```
{
  "ticker": string,
  "name": string,
  "sector": string,
  "primary_drivers": [string],           // keys from driver-taxonomy.json, e.g. "enso", "grid_reliability"
  "direction": "benefit" | "risk" | "mixed",
  "time_horizon": "short" | "long" | "both",
  "risk_level": "low" | "med" | "high",
  "thesis_type": "structural" | "cyclical",
  "policy_stance": "tailwind" | "headwind" | "contested" | "neutral",
  "remediation_confidence": "high" | "moderate" | "low" | "n/a",
  "household_demand_effect": "tailwind" | "headwind" | "mixed" | null,
  "source_confidence": "corroborated" | "interested_party" | "state_discretionary",
  "posture": "hold" | "accumulate" | "tactical" | "watch" | "hedge",
  "positioning_check": string | null,    // COT data, valuation multiples, crowded-trade risk — hard checkable data
  "hedging_check": string | null,        // company-disclosed forward hedges from 10-K/earnings calls — hard checkable data
  "backtest_check": string | null,       // historical performance in prior analogous cycles — hard checkable data
  "analyst_consensus_check": string | null, // sell-side Wall Street consensus, kept as a cross-check ONLY — never blended into direction/posture. Ends with an explicit CORROBORATES/DIVERGES/MIXED-UNCLEAR verdict against the dashboard's own call. Prefers named industry-specialist/track-record-filtered analysts over raw consensus.
  "notes": {
    "core": string,
    "policy": string | null,
    "demand": string | null,
    "sourcing": string,                  // what kind of source underlies the claims here, named where possible
    "exit_signal": string,
    "signal_check": string | null        // qualitative conviction note — "this was revised", "lower conviction than X implies"
  },
  "last_verified": "YYYY-MM-DD",
  "confidence_stale_after_days": number  // 7-14 for positioning/commodity-driven tickers, 30 for active/fast-moving stories, 90 for quarterly-cadence structural theses
}
```

`positioning_check`/`hedging_check`/`backtest_check` are for hard, checkable data. `notes.signal_check` is for a qualitative flag ("this thesis was revised," "weaker than the headline narrative implies"). Don't blur the two.

### `posture` — the one field with a non-obvious split

`hold` and `accumulate` are deliberately different, not synonyms:
- **hold** — thesis is real but currently fragile, reversible, or just-revised (e.g. CF's Hormuz-driven pricing power could unwind as fast as the conflict created it; GNRC's growth driver just shifted from storms to data centers and needs more confirmation before treating it as settled)
- **accumulate** — thesis is structural, well-evidenced, and currently reinforcing (e.g. AWK/XYL's regulated rate-base compounding; MP's DoD-backed reshoring position, strengthened rather than undermined by China's own retaliatory export controls)
- `tactical` / `watch` / `hedge` are unchanged from the original design: time-limited catalyst window / no position yet, monitoring / sized to offset risk rather than profit from it

Full definitions also live in `dashboard/index.html`'s `GLOSSARY` JS object (source of truth for the in-app tooltips/legend) and in README.md's "Posture values" section — keep those two and this file in sync if the definitions change.

## Driver taxonomy (`data/driver-taxonomy.json`)

13 keys: `enso`, `secular_warming`, `wildfire_drought_baseline`, `water_scarcity`, `sea_level_coastal`, `ecosystem_service`, `water_rights_compact`, `grid_reliability`, `logistics_disruption`, `managed_retreat`, `critical_minerals`, `deep_sea_mining`, `carbon_border_adjustment`. Each has a `remediation_confidence` note. Standing principle recorded there: across water rights, grid reliability, and managed retreat, **the private-capital/market-based response consistently shows higher remediation confidence than the formal government policy process** — weight "what capital is already doing" over "what has been proposed."

## Dev environment gotchas (this machine, as of 2026-07-17)

- **Python 3.12 was installed via winget mid-project** (`Python.Python.3.12`). Each fresh PowerShell tool invocation in this harness does not inherit an updated `PATH` automatically — prefix `python` calls with:
  ```powershell
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
  ```
  until confirmed unnecessary in a genuinely fresh user-opened terminal.
- **No Node/npm installed.** Nothing in this repo needs it, but don't assume `npx` works.
- **Browsers block `fetch()` of local `file://` JSON** — `dashboard/index.html` needs to be served over HTTP. `scripts/serve.ps1` is a zero-dependency `HttpListener`-based server written specifically because this machine had neither Python nor Node when the dashboard was first built (Python was added later; the script is still the simplest zero-install path).
- **The Claude Browser preview pane caches `fetch()` responses across `navigate()` reloads of the same file://, even with cache-busting.** If verifying dashboard behavior after a `data/*.json` edit, re-fetch with `{cache: 'no-store'}` and manually reassign `TARGETS`/re-render rather than trusting a plain reload.

## Build history summary

1. Initial build (this session, earlier): stood up the schema, ported the 20-ticker dataset from a prior chat-based research session, added TMC and MP Materials as the first two schema-validation adds, built the dashboard and staleness-check tooling. All `last_verified` dates were deliberately set to a stale placeholder (`2026-01-01`) rather than fabricated, since original per-fact citations weren't preserved in the chat-to-repo handoff.
2. Verification pass: three parallel background research agents (WebSearch-equipped) re-verified all 22 tickers with real, named, dated sources; corrected several theses rather than just re-dating them (notably: MDLZ wrongly assumed to mirror Hershey's cocoa-hedge cushion — it doesn't; GNRC's growth driver shifted from storms to data centers; BLDR downgraded benefit→mixed; LEN's FL/CA insurance markets found to be diverging, not moving together). `last_verified` set to `2026-07-17` across the board.
3. Expansion pass: added the remaining Section-4 candidate tickers from the original build brief — NEE, FLNC, PWR, CTVA, plus two research-and-select picks for previously-open slots (CSNVY/Corbion for `ecosystem_service`, GWRS/Global Water Resources for `water_rights_compact`). Dataset is now 28 tickers.
4. UI pass: added hover/focus tooltips and a collapsible glossary/legend panel to the dashboard, and split `posture: hold` into `hold` + `accumulate` (user-requested schema change — see above). Tooltips were later rewritten from CSS `::before`/`::after` (which got clipped by `.card`'s `overflow:hidden`) to a single JS-positioned `position:fixed` element — if touching tooltip code, keep it that way, don't revert to the CSS pseudo-element approach.
5. Analyst-consensus pass: added `analyst_consensus_check` (see schema above) and populated it for all 28 tickers via three background research passes grouped by sector, each explicitly told to prefer named industry-specialist/track-record-filtered ratings over raw consensus. While cross-checking sources, discovered **NIB (iPath Cocoa ETN) was actually delisted by Barclays on 2023-06-14** — it had been sitting in the dataset as a live tactical position the whole time; `notes.core` now leads with an unmissable warning.
6. Liveness pass: checked all 26 non-NIB tickers for "is this still a tradable instrument" (a distinct question from "is the thesis accurate," which is all prior passes had checked). All 26 confirmed fine. Follow-up research on **JO (iPath Coffee ETN)** raised its status from "unresolved" to "likely delisted" (0 trading volume vs. a 10.82K average, multiple sources calling it "no longer active") — not at NIB's confirmed-certain level, but treated the same way in `notes.core` pending a final broker-side check.

## Known open items / caveats worth remembering

- **NIB (iPath Cocoa ETN) is delisted (confirmed, 2023-06-14)** and **JO (iPath Coffee ETN) is very likely delisted (high-confidence, unconfirmed exact date)** — Barclays ran three redemption waves (21 ETNs in 2023, 18 in 2024, 4 in 2025) and JO's 0-volume/stale-price pattern matches NIB's confirmed profile closely; neither is tradable. Both kept in the dataset for historical/reference value only, with loud warnings at the top of `notes.core`. The schema has no dedicated "inactive/delisted" posture value — if a third ticker turns up this way, consider whether a 6th posture value or a top-level `active: boolean` flag is warranted, but don't add one unilaterally without checking with the user first (schema changes have consistently been discussed before implementing in this project).
- **Liveness/listing check completed 2026-07-18** across all other 26 tickers — all confirmed actively trading, no further NIB-style issues found. Two minor notes recorded in-entry: TMC had a Nasdaq minimum-bid-price non-compliance notice (Nov 2024, resolved Jul 2025 — re-check if price drops toward $1 again) and CSNVY's thin OTC trading was confirmed genuine (real trade prints, not a frozen quote) rather than assumed. This kind of check — "is the ticker still a real, tradable instrument" — should be an explicit step in any future full verification pass, not assumed as covered by a thesis refresh.
- **CTVA (Corteva)** is spinning off its seed-genetics business into a new company, "Vylor, Inc.," targeted for Q4 2026. The drought-resistant-seed thesis this entry is built on will structurally migrate to Vylor, not stay with CTVA — revisit this entry (and consider adding Vylor as its own ticker) once that separation happens.
- **CSNVY (Corbion)** and **GWRS (Global Water Resources)** are both *indirect* plays, not clean direct exposure to their driver — flagged explicitly in each entry's `signal_check` and deliberately left at `posture: watch` rather than a stronger posture.
- `refresh-log.json`'s `insurance_reinsurance_loss_estimates` row has never been run — no ticker in this dataset has had its insurance/reinsurance loss-estimate sourcing refreshed against Aon/Gallagher Re/Munich Re/Swiss Re.
- No standing/scheduled process discovers new candidate tickers on its own — deciding what to research next is still a manual, user-driven step. The repeatable workflow (background WebSearch research agents grouped by sector → manual synthesis into `targets.json`, preserving explicit uncertainty flags rather than smoothing agent findings) is proven and worth reusing as-is for future refresh/expansion passes.
- `fetch_cot.py`'s CFTC market-name strings can go stale silently (e.g. natural gas's CFTC listing renamed from "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE" to "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE" at some point after Feb 2022) — if a ticker starts returning old dates, re-check the current market name via a `like` query against the Socrata API before assuming the fetch is broken.
