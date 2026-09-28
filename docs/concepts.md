# Concepts

## The power system graph

A GOOD model is a NetworkX `DiGraph`:

* **Nodes** are balancing regions (`Region`). Each has an `assets`
  dictionary (handle to attributes) and may have a `profiles` dictionary
  (key to list of per-step values) that its assets refer to by key.
* **Edges** are directed links (`Link`) from a source region to a target
  region. Each holds a `lines` dictionary of `Transmission` lines. The two
  directions of a path are separate edges so their limits can differ; lines
  that share a `corridor` name share expansion decisions.

Graphs are saved as node-link JSON (`good.graph.graph_to_json`), optionally
gzip-compressed with a `.json.gz` name.

## Components

Every node, edge, asset, line and policy is a component: an instance of a
class registered by name. The `_class` key in the graph names the class.

| Kind | Classes | Role |
|---|---|---|
| Node | `Region` | Balances energy in every step |
| Edge | `Link` | Holds lines between two regions |
| Asset | `Producer`, `Store`, `Load` | Produce, store or consume energy |
| Line | `Transmission` | Moves energy between regions, with losses |
| Policy | `Portfolio_Standard`, `Capacity_Target`, `Reserve_Margin` | Constrain sets of assets |

Each class validates its inputs (see [Inputs](inputs.md)) and adds its
variables, constraints and costs to the model for all of its instances at
once. That keeps the model vectorized: one linopy variable per class and
quantity, indexed by instance and time.

### Adding a component class

Subclass an existing class, or `Asset`, `Line` or `Policy` directly. A
subclass registers itself when Python defines it, so graphs can name it in
`_class` straight away:

```python
from good.optimization import Producer

class Nuclear(Producer):
    """Producer with a must-run floor unless the input overrides it."""

    def __init__(self, handle, **kwargs):
        kwargs.setdefault("min_output", 0.9)
        super().__init__(handle, **kwargs)
```

A new asset class implements the class method `build(net, objs)`, which adds
variables and constraints for every instance and registers its contribution
to regional balances with `net.add_injection(expression, regions)`. Classes
used by policies also implement `generation`, `capacity` or `demand`. See
`good/optimization/assets/producer.py` for a complete example.

## Assets

* **Producer**: thermal plants, hydro, geothermal, wind and solar. Output
  is limited by `capacity_factor × profile × capacity`, so wind and solar are
  curtailable. `dispatchable=False` fixes output at that level (must-take or
  must-run); `min_output`, `ramp_rate` and `energy_budget_window` add further
  limits.
* **Store**: batteries and pumped hydro, with separate power (MW) and
  energy (MWh) capacity and one-way charge and discharge efficiencies. The
  state of charge is cyclic by default.
* **Load**: demand in MW. A load can have a flexible part that is deferred
  or served early within set time limits.

## Policies

Policies apply to sets of assets chosen by attribute filters such as
`{"renewable": True, "jurisdiction": "CA"}`, independent of region
boundaries. See [Policies and filters](policies.md).

## A model run

1. `Network(steps=..., time_step=...)` sets the time window and defaults.
2. `from_graph(graph, policies)` creates and validates every component and
   reports all input problems at once.
3. `build()` creates the linopy model.
4. `solve()` runs the solver.
5. `solution_graph()` and `solution_dataframe()` return the results.
