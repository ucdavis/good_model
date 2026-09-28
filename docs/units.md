# Units

GOOD 2.x uses the units of power system planning. Inputs and outputs share them.

| Quantity | Unit | Examples |
|---|---|---|
| Power and capacity | MW | `installed_capacity`, `capex_capacity`, `flex_capacity`, production, flow |
| Energy | MWh | storage `installed_energy`, state of charge, policy totals |
| Time step | hours | `Network(time_step=1.0)` |
| Durations and delays | hours | storage `duration`, `flex_max_delay`, `flex_max_advance` |
| Variable costs | $/MWh | `operating_cost`, `shortfall_cost`, `wastage_cost`, `flex_cost` |
| Overnight capital cost | $/MW | `capex_cost` (storage energy: `energy_capex_cost` in $/MWh) |
| Fixed O&M | $/MW-yr | `fom_cost` |
| Rates and shares | fraction | `efficiency`, `capacity_factor`, `ratio`, `margin`, `discount_rate` |
| Profiles | per-unit of capacity | one value per time step |
| Prices (output) | $/MWh | `clearing_price` |
| Objective (output) | $ | cost of the modeled window |

Free-form attributes carried in the example data use these units after
migration: heat rate in Btu/kWh and emission rates (`co2`, `nox`, `so2`, `ch4`,
`n2o`, `pm`) in kg/MWh. The optimization does not use them.

## Why not SI units

GOOD 1.x worked in watts, joules and $/J. The resulting linear program had cost
coefficients spanning 13 orders of magnitude (7e-10 to 1e3) and right-hand
sides up to 5e13. HiGHS stalled on a 720-hour California run in those units,
while the same problem restated in MW, MWh and $/MWh solved in about six
seconds. Keep inputs in the units above; values of order 1e-6 or 1e9 usually
mean a unit slip.

## Converting 1.x inputs

`good.migrate.from_v1(graph)` converts a 1.x graph: W to MW (÷1e6), J to MWh
(÷3.6e9), $/J to $/MWh (×3.6e9) and $/W to $/MW (×1e6). See
[Migrating from 1.x](migration.md).
