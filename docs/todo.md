# Geopolitical Dashboard – Remaining To-Do

_Last updated: 2026-03-03_

---

## High Priority — Data Gaps

| # | Item | Why it matters |
|---|---|---|
| 1 | **Backfill `region_code` in `fact_incident`** | All 385,918 rows are NULL — the regional filter and choropleth won't work in Tableau without it. One `UPDATE fact_incident SET region_code = (SELECT region_code FROM dim_country WHERE iso3 = fact_incident.country_iso3)` fixes it. |
| 2 | **Fill `region_code` in 152 `dim_country` rows** | These countries fall through the hardcoded mapping in `scripts/seed_dimensions.py` — extend `_ISO3_TO_REGION`. |
| 3 | **ACLED (2017–present)** | UCDP ends 2024-12-31; zero incident rows exist for 2025–2026. Register at acleddata.com, set `ACLED_API_KEY` + `ACLED_EMAIL`, then run `python3 scripts/run_pipeline.py --sources acled`. |
| 4 | **`fact_news_pulse` is empty** | GDELT DOC 2.0 API is blocked from datacenter/WSL IPs. Run from a residential or cloud IP, or switch to a curated RSS feed approach. |

---

## Medium Priority — Additional Data Sources

| # | Item | Notes |
|---|---|---|
| 5 | **SIPRI military expenditure** | World Bank `MS.MIL.XPND.GD.ZS` is loaded as a proxy, but SIPRI provides more authoritative figures. Requires manual download from [sipri.org/databases/milex](https://www.sipri.org/databases/milex). |
| 6 | **SIPRI arms transfers** | Not yet implemented; adds the militarization driver to GRS. Download from [sipri.org/databases/armstransfers](https://www.sipri.org/databases/armstransfers). |
| 7 | **Global Peace Index** | Annual index from [visionofhumanity.org/resources](https://www.visionofhumanity.org/resources/) — adds governance/peace sub-score to GRS. |
| 8 | **Alliance membership edges** | NATO/EU membership lists for the network graph panel — not yet implemented. Source: [nato.int/cps/en/natohq/nato_countries.htm](https://www.nato.int/cps/en/natohq/nato_countries.htm). |

---

## Low Priority — Completeness

| # | Item | Notes |
|---|---|---|
| 9 | **README.md** | Setup instructions: install deps, bootstrap DB, run pipeline, connect Tableau. |
| 10 | **Tests** | `tests/` directory exists but is empty. Transformer unit tests are most valuable. |
| 11 | **`plan.md` deleted** | Minor — restore or commit the deletion to clean up git status. |

---

## Current Pipeline State

| Source | Rows loaded | Status |
|---|---|---|
| UCDP GED v25.1 | 385,918 | ✅ Success (covers 1989–2024) |
| OFAC SDN | 18,710 | ✅ Success |
| World Bank API | 10,790 | ✅ Success (population, GDP/capita, mil. exp %) |
| Seed events | 41 | ✅ Success |
| ACLED | 0 | ⚠️ Needs `ACLED_API_KEY` + `ACLED_EMAIL` |
| GDELT | 0 | ⚠️ Blocked from this network IP |

## Quickest Win

**Items 1 + 2** (region backfill) can be done in ~5 minutes with a single script and unblock the entire regional filtering layer in Tableau.
