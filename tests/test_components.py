import importlib
import subprocess
import sys

import numpy as np
import pytest

import good
from good.optimization import REGISTRY, Producer
from helpers import H, energy, region_graph, solve


def test_import_needs_no_reload():
    """B1/B2: a fresh interpreter can import good and build a network by class name."""

    code = (
        "import good, networkx as nx\n"
        "g = nx.DiGraph(); g.add_node('R', _class='Region', assets={'l': {'_class': 'Load', 'installed_capacity': 1},"
        " 'g': {'_class': 'Producer', 'installed_capacity': 2}})\n"
        "n = good.Network(steps=(0, 2)).from_graph(g); n.build(); n.solve(); print(round(n.objective_value, 6))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)

    assert result.stdout.strip() == "0.0"


def test_subclasses_register_and_build():
    """Classes defined by users register themselves; a subclass of a subclass works."""

    class Nuclear(Producer):
        pass

    assert REGISTRY["Nuclear"] is Nuclear

    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 50},
        "n1": {"_class": "Nuclear", "installed_capacity": 100, "operating_cost": 5},
    })

    _, solution = solve(graph)

    assert solution.nodes["R"]["assets"]["n1"]["production"][0] == pytest.approx(50)


def test_visualization_imports_lazily():

    assert importlib.import_module("good.visualization").plot_lmps


# ---------------------------------------------------------------- storage

def test_storage_losses_and_cycling():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100},
        "cheap": {"_class": "Producer", "installed_capacity": 200, "operating_cost": 10,
                  "profile": [1.0] * 12 + [0.0] * 12},
        "dear": {"_class": "Producer", "installed_capacity": 200, "operating_cost": 100},
        "bat": {"_class": "Store", "installed_capacity": 50, "duration": 4,
                "charge_efficiency": 0.9, "discharge_efficiency": 0.9},
    })

    _, solution = solve(graph)
    bat = solution.nodes["R"]["assets"]["bat"]

    charged = energy(bat["charge"]) * 0.9
    discharged = energy(bat["discharge"]) / 0.9

    assert charged == pytest.approx(discharged, rel=1e-6)  # cyclic: stored energy balances
    assert max(bat["soc"]) <= 200 + 1e-6
    assert max(bat["discharge"]) <= 50 + 1e-6
    assert energy(bat["discharge"]) > 0


def test_acyclic_store_starts_at_initial_soc():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 10},
        "bat": {"_class": "Store", "installed_capacity": 10, "duration": 5, "cyclic": False, "initial_soc": 1.0},
    })

    _, solution = solve(graph, steps=(0, 4))
    bat = solution.nodes["R"]["assets"]["bat"]

    assert energy(bat["discharge"]) == pytest.approx(40)
    assert energy(solution.nodes["R"]["shortfall"]) == pytest.approx(0, abs=1e-6)


def test_store_energy_capex_is_charged_per_mw_of_duration():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 10},
        "gas": {"_class": "Producer", "installed_capacity": 20, "operating_cost": 50, "profile": [1.0] * 23 + [0.0]},
        "bat": {"_class": "Store", "duration": 2, "capex_capacity": np.inf, "capex_cost": 1000.0,
                "energy_capex_cost": 500.0, "capital_charge_rate": 1.0},
    })

    network, solution = solve(graph, steps=(0, 24))
    new = solution.nodes["R"]["assets"]["bat"]["new_capacity"][0]
    capex = new * (1000 + 2 * 500) * 24 / 8760

    assert new == pytest.approx(10)
    assert network.objective_value == pytest.approx(capex + 50 * 10 * 23 + 50 * 10 * 1, rel=1e-6)


# ---------------------------------------------------------------- flexible demand

def test_flexible_demand_respects_max_delay():
    """With a 2-hour limit, demand deferred from the expensive hours must be served within 2 hours."""

    profile = [1.0] * H
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100, "flex_capacity": 100, "flex_max_delay": 2},
        "cheap": {"_class": "Producer", "installed_capacity": 300, "operating_cost": 10,
                  "profile": [1.0] * 6 + [0.0] * 12 + [1.0] * 6},
        "dear": {"_class": "Producer", "installed_capacity": 300, "operating_cost": 100},
    })

    _, solution = solve(graph)
    load = solution.nodes["R"]["assets"]["load"]
    backlog = np.array(load["backlog"])

    for t in range(H):

        served_next = sum(load["served"][(t + j) % H] for j in (1, 2))

        assert served_next >= backlog[t] - 1e-6

    assert energy(load["consumption"]) == pytest.approx(100 * H)


def test_flexible_demand_cannot_exceed_the_load():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 10, "flex_capacity": 50},
        "gas": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 10,
                "profile": [0.0] * 4 + [1.0] * 20},
    })

    _, solution = solve(graph)

    assert max(solution.nodes["R"]["assets"]["load"]["deferred"]) <= 10 + 1e-6


# ---------------------------------------------------------------- transmission

def test_transmission_losses_and_prices(two_regions):
    _, solution = solve(two_regions)
    flow = solution.edges["B", "A"]["lines"]["ba"]
    price_a = solution.nodes["A"]["clearing_price"][0]
    price_b = solution.nodes["B"]["clearing_price"][0]

    assert flow["flow"][0] == pytest.approx(40)
    assert flow["received"][0] == pytest.approx(38)
    assert price_a == pytest.approx(80)
    assert price_b == pytest.approx(20)


def test_corridor_expansion_is_shared_and_paid_once(two_regions):
    for line in (("B", "A", "ba"), ("A", "B", "ab")):

        two_regions.edges[line[:2]]["lines"][line[2]].update(
            corridor="AB", capex_capacity=100, capex_cost=10.0, capital_charge_rate=1.0
        )

    network, solution = solve(two_regions)
    ba = solution.edges["B", "A"]["lines"]["ba"]
    ab = solution.edges["A", "B"]["lines"]["ab"]

    assert ba["new_capacity"][0] == pytest.approx(60 / 0.95 - 40, rel=1e-6)
    assert ab["new_capacity"][0] == pytest.approx(ba["new_capacity"][0])
    assert "Transmission-new_capacity" in network.model.variables
    assert network.model.variables["Transmission-new_capacity"].shape == (1,)


def test_corridor_members_must_agree(two_regions):
    two_regions.edges["B", "A"]["lines"]["ba"].update(corridor="AB", capex_capacity=100, capex_cost=1, lifetime=40)
    two_regions.edges["A", "B"]["lines"]["ab"].update(corridor="AB", capex_capacity=50, capex_cost=1, lifetime=40)

    network = good.Network(steps=(0, H)).from_graph(two_regions)

    with pytest.raises(good.exceptions.GOOD_ValidationError, match="corridor"):

        network.build()


# ---------------------------------------------------------------- producers

def test_must_take_and_min_output():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 50},
        "geo": {"_class": "Producer", "installed_capacity": 30, "capacity_factor": 0.9, "dispatchable": False,
                "operating_cost": 60},
        "coal": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 30, "min_output": 0.4},
        "cheap": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 1},
    })

    _, solution = solve(graph)
    assets = solution.nodes["R"]["assets"]

    assert assets["geo"]["production"] == pytest.approx([27.0] * H)
    assert min(assets["coal"]["production"]) == pytest.approx(40)


def test_ramp_limit_binds():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100, "profile": [0.1] * 12 + [1.0] * 12},
        "slow": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 10, "ramp_rate": 0.2},
        "fast": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 90},
    })

    _, solution = solve(graph)
    slow = np.array(solution.nodes["R"]["assets"]["slow"]["production"])

    assert np.max(np.abs(np.diff(slow))) <= 20 + 1e-6
    assert solution.nodes["R"]["assets"]["fast"]["production"][12] > 0


def test_energy_budget_limits_daily_energy_but_not_hourly_output():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100, "profile": [0.5] * 12 + [1.0] * 12},
        "hydro": {"_class": "Producer", "installed_capacity": 100, "capacity_factor": 0.25,
                  "energy_budget_window": 24, "operating_cost": 0},
        "gas": {"_class": "Producer", "installed_capacity": 200, "operating_cost": 50},
    })

    _, solution = solve(graph)
    hydro = solution.nodes["R"]["assets"]["hydro"]["production"]

    assert energy(hydro) == pytest.approx(0.25 * 100 * 24)
    assert max(hydro) == pytest.approx(100)  # concentrated in the peak hours


def test_expansion_cost_scales_with_year_fraction():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 10},
        "new": {"_class": "Producer", "capex_capacity": 100, "capex_cost": 8760.0, "capital_charge_rate": 1.0},
    })

    network, _ = solve(graph, steps=(0, 48))

    assert network.objective_value == pytest.approx(10 * 8760 * 48 / 8760)
