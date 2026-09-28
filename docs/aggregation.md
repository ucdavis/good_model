# Aggregation

The WECC example graph has 5,592 assets; most are small plants that behave
alike. `good.aggregate.aggregate` merges similar assets within each region to
shrink the model.

```python
graph = good.graph.graph_from_json("examples/data/WEC.json.gz")
graph = good.aggregate.aggregate(graph, ratio=0.1)
```

## How assets are grouped

Assets are first split into groups that are never merged. Two assets can only
merge when they share the same

`_class`, `type`, `fuel`, `profile`, `jurisdiction`, `dispatchable` and `renewable`

(change this with `group_keys=`). Keeping profiles apart preserves the
resource diversity of wind and solar sites. Keeping jurisdictions apart keeps
state policies correct in multi-state regions. Assets without
`combinable: True`, and all expandable assets, are left as they are.

Within a group, k-means on standardized features forms `ceil(ratio × n)`
clusters (at most `max_clusters`). The default features are heat rate,
operating cost and CO2 rate, equally weighted; pass `features={"heat_rate": 2.0,
"co2": 1.0}` to change them. Groups whose members are identical in every
feature collapse to one asset.

## How attributes combine

| Attribute | Combined as |
|---|---|
| `installed_capacity`, `installed_energy`, `capex_capacity` | sum |
| costs, heat rate, emission rates, `capacity_factor`, `capacity_credit`, `min_output`, `ramp_rate`, `duration`, efficiencies | capacity-weighted mean |
| `oris_code`, `egrid_id`, `utility` | list of members' values |
| anything else | first member's value |

A merged asset is named after its first member with `_combined` appended and
lists its members under `components`. Total capacity by technology, region and
jurisdiction is unchanged.

## Effect on results and run time

On the California example, `ratio=0.1` reduces 1,091 assets to 263 in 0.01 s.
Merging plants removes some flexibility, so costs rise slightly: the 720-hour
run's objective was 1.8% higher than with all assets, and it solved about
twice as fast.
