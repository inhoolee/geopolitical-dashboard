# ACLED Data Description

_Source: Armed Conflict Location & Event Data Project (acleddata.com)_
_Exported and converted from XLSX to CSV: 2026-03-03_
_Location: `data/raw/acled/`_

---

## Overview

Twelve CSV files fall into two categories:

| Category | Files | Purpose |
|---|---|---|
| **Regional aggregated** | 6 files | Weekly event counts and fatalities by country + admin1 district — primary input for `fact_incident` |
| **Country-level summaries** | 6 files | Annual (and monthly) country totals for KPI tiles and trend validation |

---

## Regional Aggregated Files (Primary)

These six files share an identical 13-column schema. Each row represents one **event-type / admin1 / week** combination.

### Files

| File | Size | Rows | Date range |
|---|---|---|---|
| `Africa_aggregated_data_up_to-2026-02-21.csv` | 34.1 MB | 266,316 | 1996-12-28 → 2026-02-21 |
| `Asia-Pacific_aggregated_data_up_to-2026-02-14.csv` | 26.1 MB | 205,458 | 2009-12-26 → 2026-02-14 |
| `Europe-Central-Asia_aggregated_data_up_to-2026-02-14.csv` | 14.0 MB | 116,621 | 2017-12-30 → 2026-02-14 |
| `Latin-America-the-Caribbean_aggregated_data_up_to-2026-02-21.csv` | 21.3 MB | 168,748 | 2017-12-30 → 2026-02-21 |
| `Middle-East_aggregated_data_up_to-2026-02-21.csv` | 18.1 MB | 143,605 | 2014-12-27 → 2026-02-21 |
| `US-and-Canada_aggregated_data_up_to-2026-02-14.csv` | 2.8 MB | 21,941 | 2019-12-28 → 2026-02-14 |

**Total: 922,689 rows across all regions.**

### Schema

| Column | Type | Description | Nulls |
|---|---|---|---|
| `WEEK` | date | Monday start-of-week (ISO format `YYYY-MM-DD`) | None |
| `REGION` | string | ACLED macro-region name (17 values — see taxonomy below) | None |
| `COUNTRY` | string | Country name | None |
| `ADMIN1` | string | First-level administrative division (state/province/governorate) | Rare (≤17 rows in Europe file) |
| `EVENT_TYPE` | string | Broad event category (6 values) | None |
| `SUB_EVENT_TYPE` | string | Detailed event sub-category (25 values) | None |
| `EVENTS` | integer | Count of individual events in this week × admin1 × event_type cell | None |
| `FATALITIES` | integer | Reported fatalities (sum for the cell); max observed: 12,268 (Africa) | None |
| `POPULATION_EXPOSURE` | float | Estimated population in the affected admin1 area | ~7–36% null depending on file |
| `DISORDER_TYPE` | string | High-level disorder classification (4 values) | None |
| `ID` | float | ACLED internal district/location ID | Rare nulls (≤36 rows) |
| `CENTROID_LATITUDE` | float | Latitude of the admin1 centroid | None |
| `CENTROID_LONGITUDE` | float | Longitude of the admin1 centroid | None |

### Event taxonomy

**`EVENT_TYPE`** (6 values):

| Value | `DISORDER_TYPE` | Description |
|---|---|---|
| `Battles` | Political violence | Armed engagements between organised groups |
| `Explosions/Remote violence` | Political violence | Air/drone strikes, shelling, IEDs, grenades |
| `Violence against civilians` | Political violence | Attacks, abductions, sexual violence targeting non-combatants |
| `Riots` | Demonstrations | Violent crowd events, mob violence |
| `Protests` | Demonstrations | Peaceful protests, marches, demonstrations |
| `Strategic developments` | Strategic developments | Non-violent actor/territory changes, agreements, arrests |

**`SUB_EVENT_TYPE`** (25 values):

```
Abduction/forced disappearance  Agreement                      Air/drone strike
Armed clash                      Arrests                        Attack
Change to group/activity         Chemical weapon                Disrupted weapons use
Excessive force against protesters  Government regains territory  Grenade
Headquarters or base established  Looting/property destruction  Mob violence
Non-state actor overtakes territory  Non-violent transfer of territory  Other
Peaceful protest                 Protest with intervention      Remote explosive/landmine/IED
Sexual violence                  Shelling/artillery/missile attack  Suicide bomb
Violent demonstration
```

**`DISORDER_TYPE`** (4 values):

```
Demonstrations
Political violence
Political violence; Demonstrations
Strategic developments
```

**`REGION`** (17 ACLED macro-regions):

```
Antarctica              Caribbean               Caucasus and Central Asia
Central America         East Asia               Eastern Africa
Europe                  Middle Africa           Middle East
North America           Northern Africa         Oceania
South America           South Asia              Southeast Asia
Southern Africa         Western Africa
```

### Notes on coverage gaps

- **Africa** has the longest history (back to 1996); other regions start between 2010 and 2020.
- **Europe-Central-Asia** and **Latin America** both start 2017-12-30 — aligned with the dashboard's Jan 2017 baseline.
- **US-and-Canada** starts 2019-12-28.
- ACLED data through February 2026 fills the gap left by UCDP GED (which ends 2024-12-31).

### Pipeline mapping → `fact_incident`

| CSV column | `fact_incident` column | Transformation |
|---|---|---|
| `WEEK` | `event_date` | Parsed as date (Monday = week start) |
| `COUNTRY` | `country_iso3` | `name_to_iso3()` lookup |
| `ADMIN1` | `admin1` | Direct |
| `ADMIN1` | `location_name` | Same as admin1 |
| `EVENT_TYPE` | `event_type` | Direct |
| `SUB_EVENT_TYPE` | `sub_event_type` | Direct |
| `DISORDER_TYPE` | `disorder_type` | Direct |
| `EVENTS` | `event_count` | Direct (integer) |
| `FATALITIES` | `fatalities_best` / `_low` / `_high` | All three set to same value |
| `CENTROID_LATITUDE` | `latitude` | Direct |
| `CENTROID_LONGITUDE` | `longitude` | Direct |
| `EVENT_TYPE == "Violence against civilians"` | `civilian_targeting` | Boolean flag |
| Composite key (WEEK\|COUNTRY\|ADMIN1\|EVENT_TYPE\|SUB_EVENT_TYPE\|ID) | `source_event_id` | Concatenated string |
| SHA-256 of `"ACLED" + source_event_id` | `incident_id` | Stable UUID |

---

## Country-Level Summary Files (Reference)

These six files provide annual (and one monthly) country totals. They are **not** currently loaded into `fact_incident` but are useful for KPI validation and cross-checking the regional aggregates.

### Files

| File | Size | Rows | Columns | Date range |
|---|---|---|---|---|
| `number_of_political_violence_events_by_country-year_as-of-20Feb2026.csv` | 0.05 MB | 2,685 | `COUNTRY, YEAR, EVENTS` | 1997–2026 |
| `number_of_political_violence_events_by_country-month-year_as-of-20Feb2026.csv` | 0.7 MB | 28,507 | `COUNTRY, MONTH, YEAR, EVENTS` | 1997–2026 |
| `number_of_demonstration_events_by_country-year_as-of-20Feb2026.csv` | 0.1 MB | 2,892 | `COUNTRY, YEAR, EVENTS` | 1997–2026 |
| `number_of_events_targeting_civilians_by_country-year_as-of-20Feb2026.csv` | 0.05 MB | 2,649 | `COUNTRY, YEAR, EVENTS` | 1997–2026 |
| `number_of_reported_fatalities_by_country-year_as-of-20Feb2026.csv` | 0.1 MB | 2,927 | `COUNTRY, YEAR, FATALITIES` | 1997–2026 |
| `number_of_reported_civilian_fatalities_by_country-year_as-of-20Feb2026.csv` | 0.05 MB | 2,649 | `COUNTRY, YEAR, FATALITIES` | 1997–2026 |

### Suggested use

- Cross-validate annual incident totals against `country_month_agg` view in DuckDB.
- Seed the `fact_risk_indicator` table with pre-computed annual country-level ACLED KPIs (future enhancement — see `docs/todo.md` item 5).
- Drive Tableau KPI tiles for "incidents last 12 months" and "civilian fatalities trend."

---

## Data Quality Notes

| Issue | Affected files | Severity |
|---|---|---|
| `POPULATION_EXPOSURE` nulls | All regional files (7–36% null) | Low — column is supplementary; not used in GRS |
| `ID` nulls | All regional files (≤36 rows each) | Negligible — ID is not the primary key in the pipeline |
| `ADMIN1` nulls | Europe-Central-Asia (8 rows) | Negligible |
| Fatality underreporting | All files | Inherent — ACLED fatalities are reported/verified figures and may lag events |
| `Asia-Pacific` lat/lon anomaly | `Asia-Pacific` | `CENTROID_LATITUDE` shows a min of −159.77° (outside valid lat range) — likely a swapped lat/lon for one Pacific island record; flagged in validation query |
