# GOOD: Grid Optimized Operation Dispatch

GOOD is a linear economic dispatch and capacity expansion model for zonal
power systems, developed at the UC Davis Electric Vehicle Research Center to
study how transportation electrification and energy policy interact with the
grid.

A GOOD model is a directed graph. Nodes are balancing regions that hold
assets (generators, storage and loads); edges hold transmission lines.
Policies such as renewable portfolio standards select assets by attribute,
so they can follow state borders that do not line up with balancing regions.
GOOD minimizes the cost of operating the system over a chosen window of
hours, plus the annualized cost of any new capacity, and reports dispatch,
new capacity and zonal clearing prices.

Models are built with [linopy](https://linopy.readthedocs.io) and solved with
[HiGHS](https://highs.dev) by default; any solver linopy supports can be used.

## Where to start

* [Installation](installation.md)
* [Quickstart](quickstart.md): a two-region model that runs in seconds
* [Concepts](concepts.md): how graphs, assets, lines and policies fit together
* [Units](units.md): MW, MWh, hours and $
* [Formulation](formulation.md): the optimization problem
* [Migrating from 1.x](migration.md): what changed in 2.0 and how to convert old inputs

## Citing GOOD

See `CITATION.cff` in the repository. GOOD is released under the BSD
3-Clause license.
