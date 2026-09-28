# GOOD: Grid Optimized Operation Dispatch

GOOD is a linear economic dispatch and capacity expansion model for zonal
power systems, developed at the UC Davis Electric Vehicle Research Center. A
model is a graph of balancing regions holding generators, storage and loads,
joined by transmission lines, with policies (renewable portfolio standards,
capacity targets, reserve margins) that select assets by attribute across
region boundaries. GOOD minimizes operating cost plus annualized investment
cost over a chosen window of hours and reports dispatch, new capacity and
zonal prices.

GOOD is built on [linopy](https://linopy.readthedocs.io) and solves with
[HiGHS](https://highs.dev) by default. Units are MW, MWh, hours and $.

## Install

```bash
git clone https://github.com/ucdavis/good_model.git
cd good_model
pip install -e ".[plot]"
```

Python 3.10 or newer. HiGHS is installed with GOOD.

## Run

```bash
python examples/two_region.py
```

```python
import good

graph = good.graph.graph_from_json("examples/data/California.json.gz")
policies = good.utilities.read_json("examples/data/policies.json")

network = good.Network(steps=(4608, 4680)).from_graph(graph, policies)  # 12-14 July
network.build()
network.solve()

solution = network.solution_graph()
print(network.objective_value, solution.nodes["WEC_CALN"]["clearing_price"][:5])
```

`examples/Example.ipynb` walks through a full run with plots, and
`examples/California.ipynb` shows how to cut and aggregate a graph.

## Documentation

The documentation lives in `docs/` and builds with MkDocs:

```bash
pip install -e ".[docs]"
mkdocs serve
```

Start with [Quickstart](docs/quickstart.md), [Concepts](docs/concepts.md),
[Units](docs/units.md) and [Formulation](docs/formulation.md).
[Migrating from 1.x](docs/migration.md) covers the changes in 2.0.

## Test

```bash
pip install -e ".[dev]"
pytest -q
```

## Repository layout

| Path | Contents |
|---|---|
| `good/` | the package: `optimization/` (model components and `Network`), `schema.py` (inputs), `aggregate.py`, `migrate.py`, `visualization/` |
| `examples/` | example scripts, notebooks and data (`data/*.json.gz`) |
| `docs/` | documentation source; `docs/archive/` holds superseded 1.x documents |
| `scripts/` | data migration, benchmarking and documentation generation |
| `tests/` | test suite, including regression tests from the 2026 model review |

## Citation and license

Please cite GOOD using `CITATION.cff`. GOOD is released under the BSD 3-Clause
license; see `LICENSE`.
