# Quickstart

`examples/two_region.py` builds and solves a one-day model with two regions.
This page walks through it.

## 1. Describe the system as a graph

Each node is a region with an `assets` dictionary and, optionally, a
`profiles` dictionary that assets can refer to by key. Values are in MW and
$/MWh.

```python
import networkx as nx
import good

graph = nx.DiGraph()

graph.add_node("coast", _class="Region", profiles={"demand": demand, "solar": solar}, assets={
    "coast_demand": {"_class": "Load", "installed_capacity": 1000, "profile": "demand"},
    "coast_peaker": {"_class": "Producer", "installed_capacity": 600, "operating_cost": 95},
    "coast_solar": {"_class": "Producer", "installed_capacity": 300, "profile": "solar",
                    "renewable": True, "jurisdiction": "CA",
                    "capex_capacity": 2000, "capex_cost": 1.0e6, "fom_cost": 11_000, "lifetime": 30},
})
graph.add_node("inland", _class="Region", assets={
    "inland_gas": {"_class": "Producer", "installed_capacity": 800, "operating_cost": 35},
})
graph.add_edge("inland", "coast", _class="Link", lines={
    "inland_to_coast": {"_class": "Transmission", "installed_capacity": 300, "efficiency": 0.972},
})
```

* A `Load`'s demand is `installed_capacity × profile`.
* A `Producer`'s output is limited by `installed_capacity × profile`; wind and
  solar can therefore be curtailed.
* `capex_capacity > 0` lets the model build up to that many MW more, at
  `capex_cost` $/MW overnight, annualized over `lifetime` years.

## 2. Add policies

Policies choose assets with attribute filters (see [Policies](policies.md)):

```python
policies = {
    "coast_rps": {
        "_class": "Portfolio_Standard",
        "ratio": 0.4,
        "include": {"renewable": True, "jurisdiction": "CA"},
        "exclude": {"renewable": {"not": True}, "_class": "Producer", "jurisdiction": "CA"},
    },
}
```

## 3. Build, solve and read results

```python
network = good.Network(steps=(0, 24)).from_graph(graph, policies)
network.build()
network.solve()               # HiGHS by default

solution = network.solution_graph()
coast = solution.nodes["coast"]

print(network.objective_value)                        # $ for the modeled window
print(coast["clearing_price"])                        # $/MWh, one value per step
print(coast["assets"]["coast_solar"]["new_capacity"]) # MW built
```

`network.solution_dataframe()` returns the same results as one table indexed
by time step. [Outputs](outputs.md) lists every result key.

## 4. Choose the time window

`steps=(start, stop)` selects steps `start` to `stop - 1` of every profile, so
`steps=(4608, 4776)` is the week starting 12 July in an hourly 8,760-step year.
Capacity costs are scaled by the modeled fraction of a year, so a week's run
charges 168/8,760 of a year's capacity cost. How long a window to use, and
whether to aggregate time or space, is up to you; see [Performance](performance.md).
