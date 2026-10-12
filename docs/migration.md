# Migrating from 1.x

GOOD 2.0 changes units, several component inputs and the solver layer. Old
inputs are rejected with a message naming the replacement, and
`good.migrate` converts 1.x graphs and policy files.

## Converting inputs

```python
import good

graph = good.graph.graph_from_json("old/California.json")
policies = good.utilities.read_json("old/policies.json")

graph = good.migrate.from_v1(graph)                  # units, classes and data repairs
policies = good.migrate.convert_policies(policies)   # lambda strings to filters

print(graph.graph["migration_notes"])                # what was changed, with counts
good.graph.graph_to_json(graph, "California.json.gz")
```

Review [Data assumptions](assumptions.md) before using converted graphs for
published results.

## API changes

| 1.x | 2.0 |
|---|---|
| `import good` then `deep_reload(good)` before building | `import good` is enough |
| `good.optimization.network.Network(**kw)` | `good.Network(...)` (the old path still works) |
| `Network(amortization_period=31536000)` | removed; each expandable asset gives `lifetime` or `capital_charge_rate` |
| `Network(shortfall_cost=1e3, wastage_cost=1e3)` in $/J | $/MWh; defaults are $10,000/MWh with unlimited capacity |
| `network.solve(solver={'_name': 'cbc'})` | `network.solve("highs")`; HiGHS is the default and ships with GOOD |
| Pyomo model in `network.model` | linopy model in `network.model` |
| `visualizations.py` at the repository root | `good.visualization` |
| `aggregate(graph, clustering={'resolution': 2})` | `aggregate(graph, ratio=0.1)` (k-means; see [Aggregation](aggregation.md)) |

## Input changes

| Component | 1.x | 2.0 |
|---|---|---|
| all | W, J, $/J, $/W | MW, MWh, $/MWh, $/MW ([Units](units.md)) |
| `Load` | negative `installed_capacity` for demand | positive MW of demand |
| `Load` | wind and solar modeled as loads (cannot be curtailed) | wind and solar are `Producer` assets with a profile |
| `Load` | `shift_capacity`, `shift_window` | `flex_capacity` (MW), `flex_max_delay`, `flex_max_advance` (hours) |
| `Load` | `capex_capacity`, `capex_cost` | removed: loads are demand only |
| `Store` | one `installed_capacity` used as both energy (J) and power | `installed_capacity` (MW) with `duration` (h) or `installed_energy` (MWh) |
| `Store` | `efficiency`, `production_rate`, `consumption_rate`, `initial` | `charge_efficiency`, `discharge_efficiency`; `cyclic` (default) or `initial_soc` |
| `Producer` | `dispatchable` read but ignored | `dispatchable=False` fixes output at availability |
| `Producer` | none | `min_output`, `energy_budget_window`, `capacity_credit` |
| expandable assets | `capex_cost` recovered over `amortization_period` | overnight `capex_cost` ($/MW) annualized with `lifetime` or `capital_charge_rate`, plus `fom_cost` |
| `Transmission` | one line per direction, each expanded and paid separately | lines sharing a `corridor` share one expansion |
| policies | `inclusion_criteria` and similar as lambda strings | `include`, `exclude`, `supply`, `demand` as [filters](policies.md) |
| `Reserve_Margin` | `sign=-1` for negative loads; nameplate for every asset | no sign; each asset counts `capacity_credit × capacity` |

## Behavior changes that affect results

* Wind and solar are curtailed rather than paying the wastage penalty.
* Storage is cyclic by default instead of starting and ending empty.
* Flexible demand is always paid back inside the window, and the last step
  is constrained like the rest.
* Capital costs are annualized, not recovered in one year.
* Transmission has losses in the converted example data.

Results produced with 1.x that involve storage, load flexibility, high
renewable shares or capacity expansion should be re-run.
