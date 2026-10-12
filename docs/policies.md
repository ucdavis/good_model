# Policies and filters

Policies constrain sets of assets. Each set is chosen with an **attribute
filter**, so a policy can follow a state, a technology or any other attribute,
regardless of which regions the assets sit in.

## Filters

A filter is a dictionary from attribute name to condition. An asset matches
when every condition holds.

| Condition | Matches when the attribute | Example |
|---|---|---|
| a value | equals it | `{"renewable": True}` |
| a list | equals one of the values | `{"jurisdiction": ["CA", "NV"]}` |
| `{"not": value}` | differs from the value, or is missing | `{"_class": {"not": "Store"}}` |
| `{"not": [values]}` | is none of the values, or is missing | `{"type": {"not": ["load", "battery"]}}` |
| `{">": x}`, `{">=": x}`, `{"<": x}`, `{"<=": x}` | compares as stated | `{"installed_capacity": {">=": 50}}` |

An asset that lacks an attribute fails every condition except `not`. An
empty filter matches every asset. Besides the asset's own keys, filters can
use `_class` (the class name) and `node` (the region).

Filters are plain data, so policy files can be stored as JSON and are never
executed. GOOD 1.x used Python lambda strings run with `eval`; those are now
refused. `good.migrate.convert_policies()` translates the lambda patterns in
the 1.x example files.

## Portfolio_Standard

A share of generation over the window must come from included assets:

```json
{
  "_class": "Portfolio_Standard",
  "ratio": 0.6,
  "include": {"renewable": true, "jurisdiction": "CA"},
  "exclude": {"renewable": {"not": true}, "_class": "Producer", "jurisdiction": "CA"}
}
```

The denominator is included plus excluded generation. An asset that matches
both filters counts as included. This is a share of in-jurisdiction
*generation*; it does not model retail sales, imports or REC trading.

## Capacity_Target

Total capacity (existing plus new, MW) of included assets must reach `target`:

```json
{"_class": "Capacity_Target", "target": 70000, "include": {"type": ["solar", "wind"], "jurisdiction": "CA"}}
```

## Reserve_Margin

Credited capacity must exceed peak demand by `margin`:

```json
{"_class": "Reserve_Margin", "margin": 0.15, "demand": {"_class": "Load"}, "supply": {"_class": {"not": "Load"}}}
```

Each supply asset counts `capacity_credit × capacity`. The default credit is
1.0, so give wind, solar and short-duration storage realistic credits (see
[Data assumptions](assumptions.md)). Demand is the matching loads' base demand
before flexible shifting.

## Soft enforcement

Every policy accepts `non_compliance_capacity` (default 0, strict) and
`non_compliance_cost`. A positive capacity lets the model fall short of the
policy at that cost per unit: MWh for portfolio standards, MW for the others.
