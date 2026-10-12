# Installation

GOOD needs Python 3.10 or newer.

```bash
git clone https://github.com/ucdavis/good_model.git
cd good_model
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
```

This installs GOOD with HiGHS, so no separate solver is needed.

Optional extras:

| Command | Adds |
|---|---|
| `pip install -e ".[plot]"` | matplotlib, for `good.visualization` |
| `pip install -e ".[docs]"` | MkDocs, to build this site with `mkdocs serve` |
| `pip install -e ".[dev]"` | everything above plus pytest |

## Checking the install

```bash
python examples/two_region.py
pytest -q
```

The example prints the day's system cost and new capacity. The test suite
runs in about ten seconds; `pytest -m "not slow"` skips the California example.

## Other solvers

Pass any solver name linopy supports, for example `network.solve("gurobi")`,
after installing that solver and its Python interface. Commercial solvers are
much faster on large capacity expansion problems; see [Performance](performance.md).
