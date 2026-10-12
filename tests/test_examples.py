import importlib.util
from pathlib import Path

import numpy as np
import pytest

import good

EXAMPLES = Path(__file__).parent.parent / "examples"


def _load(name):

    spec = importlib.util.spec_from_file_location(name, EXAMPLES / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def test_two_region_example_runs():

    network, solution = _load("two_region").main()
    coast = solution.nodes["coast"]

    assert network.objective_value > 0
    assert sum(coast["shortfall"]) == pytest.approx(0, abs=1e-6)
    assert all(p >= -1e-6 for p in coast["clearing_price"])


@pytest.mark.slow
def test_california_example_one_day():

    graph = good.graph.graph_from_json(EXAMPLES / "data" / "California.json.gz")
    policies = good.utilities.read_json(EXAMPLES / "data" / "policies.json")

    network = good.Network(steps=(4608, 4632)).from_graph(graph, policies)
    network.build()
    network.solve()

    solution = network.solution_graph()
    frame = network.solution_dataframe(solution)

    assert frame.shape[0] == 24
    assert all(len(n["clearing_price"]) == 24 for _, n in solution.nodes(data=True))
    assert np.isfinite(network.objective_value)
