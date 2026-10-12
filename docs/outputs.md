# Outputs

After `network.solve()`:

* `network.objective_value`: total cost of the window ($).
* `network.solution_graph()`: a graph shaped like the input, holding results.
* `network.solution_dataframe()`: the same time series in one table.
* `network.model`: the linopy model, for anything else (duals, reduced costs).

## Solution graph

Values are lists with one entry per step; capacities are one-element lists.

**Nodes** (regions)

| Key | Unit | Meaning |
|---|---|---|
| `clearing_price` | $/MWh | dual of the regional balance divided by the step length |
| `shortfall` | MW | unserved demand |
| `wastage` | MW | surplus that could not be absorbed |
| `assets` | | dictionary of asset results, below |

**Producers**

| Key | Unit | Meaning |
|---|---|---|
| `production` | MW | output |
| `net` | MW | injection into the region (equals production) |
| `new_capacity` | MW | capacity built |

**Stores**

| Key | Unit | Meaning |
|---|---|---|
| `charge`, `discharge` | MW | power drawn and delivered |
| `soc` | MWh | state of charge at the end of each step |
| `net` | MW | discharge minus charge |
| `new_capacity` | MW | power capacity built |
| `new_energy` | MWh | energy capacity built |

**Loads**

| Key | Unit | Meaning |
|---|---|---|
| `demand` | MW | base demand |
| `consumption` | MW | demand after flexible shifting |
| `deferred`, `served`, `backlog` | MW, MW, MWh | flexible loads only |
| `net` | MW | minus consumption |

**Edges** hold `lines`, each with `flow` (MW sent), `received` (MW arriving
after losses) and `new_capacity` (MW, shared across a corridor).

**Graph attributes**: `solution.graph["policies"]` holds each policy's
`non_compliance`; `objective`, `steps` and `time_step` describe the run.

## DataFrame

`solution_dataframe()` has one row per step and columns named

* `region::key` for region results,
* `region:asset::key` for assets,
* `source:target:line::key` for lines.

Single values such as `new_capacity` appear in the first row, with NaN below.

## Saving

```python
good.graph.graph_to_json(solution, "outputs/solution.json.gz")
network.solution_dataframe(solution).to_csv("outputs/solution.csv")
```

`outputs/` folders are ignored by git.

## Plots

`good.visualization` (needs matplotlib) plots prices, demand, generation by
type or fuel, new capacity and the regional fuel mix from the input graph and
the solution graph. See `examples/Example.ipynb`.
