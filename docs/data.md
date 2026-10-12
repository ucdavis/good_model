# Data sources

The example graphs in `examples/data/` (California, ERCOT and WECC) were built
from EPA and EIA data by a pipeline that is not part of this repository, then
converted to GOOD 2.0 with `good.migrate.from_v1()` (see
`scripts/migrate_examples.py`). This page records where each quantity comes
from and what the conversion changed.

## Sources

| Source | Provides |
|---|---|
| EPA eGRID 2020 (`egrid2020_data_plants.csv`) | plant location (state, county, NERC and eGRID subregion, coordinates), primary fuel (`PLPRMFL`), annual emission rates for NOx, SO2, CO2, CH4 and N2O |
| EPA NEEDS v6 (`needs_v617_parsed.csv`) | unit capacity, IPM region, plant and fuel type, annual fuel cost and use, variable O&M |
| EPA Platform v6 (IPM), November 2018 reference case | inter-regional transmission capacity and wheeling cost, wind and solar profiles and resource potential, capital cost adders, load shapes, cost and performance of new units, capital charge rates |
| EPA AP-42 chapter 1 (`c01s01.pdf` to `c01s11.pdf`) | condensable particulate emission rates by boiler type |

eGRID and NEEDS records are joined on the ORIS plant code.

## Processing in the upstream pipeline

* **Fuel type.** eGRID's primary fuel (`PLPRMFL`) is used; blanks, mostly
  small or exempt plants, are filled from NEEDS plant categories.
* **Fuel cost.** Dispatch cost is annual fuel cost divided by annual fuel use,
  times heat rate, plus variable O&M. Hydro and pumped storage are set to zero
  fuel cost. Fossil plants reporting zero fuel cost take a cost sampled from
  plants of the same fuel, region and size.
* **Emission rates.** Non-combustion plants are set to zero (their reported
  rates come from backup generators). Fossil plants without rates take the
  average of plants with the same fuel, capacity and heat rate.
* **Aggregation.** Plants in each region are clustered to keep the model
  tractable; see [Aggregation](aggregation.md).

## Problems found in the 1.x example data

The 2026 review found these problems in the files the pipeline produced. The
conversion to 2.0 repairs them in the example data, but **the upstream
pipeline still needs the same fixes** before it regenerates data:

| Problem | Cause | Repair in `from_v1()` |
|---|---|---|
| Wind profiles had 9,125 values (365 × 25), drifting one hour per day against load and solar | IPM Table 4-39's `Day Of Month` column was read as a 25th hourly value (day / 1000) | the day-of-month column is dropped, after checking it matches |
| Hydro profiles were never used | assets referred to `REGION:hydro:` but the key was `REGION:hydro` | the key is matched |
| Hydro profiles ranged 1.0 to 5.6 and had 8,759 values | they are monthly generation indices normalized to the lowest month, one hour short | converted to a per-unit shape with mean 1 and used as a daily energy budget |
| Wind and solar capital cost of about $1/kW | IPM base cost plus regional adder in $/kW was divided by 1e6 instead of 1e3 | multiplied by 1,000 (to about $950 to $2,160/kW) |
| Batteries priced at $300/kWh for energy only, with unlimited power | no power cost or duration | IPM Table 4-35 costs for 4-hour batteries |
| Existing storage had no duration or efficiency | not carried from the source | assumed durations and efficiencies |
| Transmission was lossless | losses not carried from IPM | IPM losses: 2.8% in WECC, 2.4% elsewhere |
| Biomass and waste flagged `renewable: False` | pipeline flag | **not changed**; biomass is RPS-eligible in California, so review this flag |
| Geothermal `capacity_factor` of 1.0 with `dispatchable: False` | pipeline values | **not changed**; geothermal now runs as must-run at that factor |

Every value the conversion introduces, with its source, is listed in
[Data assumptions](assumptions.md). Values marked PLACEHOLDER (pumped hydro
duration and efficiency, wind and solar capacity credits) need review.

## Profiles and time

Profiles are per-unit and indexed by hour of a 365-day, 8,760-hour year
starting 1 January at 00:00. Hour 4,608 is 12 July at 00:00. Load profiles
are normalized so that each region's peak is 1.0 and are multiplied by the
load's `installed_capacity` (MW).
