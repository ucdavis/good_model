"""
The six test systems from the September 2026 model review (T1-T6), each
asserting the corrected behaviour. They failed on GOOD 1.1.3.
"""

import numpy as np
import pytest

from helpers import H, energy, region_graph, solve


def test_t1_existing_storage_has_energy_capacity():
    """F1: a 100 MW, 10-hour pumped hydro plant covers a 6-hour outage."""

    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100},
        "gas": {"_class": "Producer", "installed_capacity": 200, "operating_cost": 50,
                "profile": [1.0] * 12 + [0.0] * 6 + [1.0] * 6},
        "phs": {"_class": "Store", "installed_capacity": 100, "duration": 10,
                "charge_efficiency": 0.9, "discharge_efficiency": 0.9},
    })

    _, solution = solve(graph)
    phs = solution.nodes["R"]["assets"]["phs"]

    assert max(phs["soc"]) > 600  # MWh, not 0.028 MWh
    assert energy(solution.nodes["R"]["shortfall"]) == pytest.approx(0, abs=1e-6)


def test_t2_new_battery_power_is_limited_and_paid_for():
    """F1: a 4-hour battery cannot discharge its whole energy in one hour."""

    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100},
        "gas": {"_class": "Producer", "installed_capacity": 200, "operating_cost": 50,
                "profile": [1.0] * 20 + [0.0] * 4},
        "bat": {"_class": "Store", "duration": 4, "capex_capacity": np.inf,
                "capex_cost": 1e5, "lifetime": 15, "charge_efficiency": 0.95, "discharge_efficiency": 0.95},
    })

    network, solution = solve(graph)
    bat = solution.nodes["R"]["assets"]["bat"]
    power = bat["new_capacity"][0]

    # 400 MWh delivered over the 4-hour gap draws 400 / 0.95 MWh from a 4-hour store
    assert power == pytest.approx(100 / 0.95, rel=1e-6)
    assert bat["new_energy"][0] == pytest.approx(4 * power)
    assert max(bat["discharge"]) <= power + 1e-6
    assert energy(solution.nodes["R"]["shortfall"]) == pytest.approx(0, abs=1e-6)


def test_t3_flexible_demand_is_conserved_and_bounded():
    """F2: shifted demand is paid back within the horizon; units are MW and MWh."""

    price = [1.0] * 12 + [0.0] * 12  # expensive gas in the first half
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100, "flex_capacity": 50, "flex_max_delay": 12},
        "cheap": {"_class": "Producer", "installed_capacity": 200, "operating_cost": 10},
        "dear": {"_class": "Producer", "installed_capacity": 200, "operating_cost": 90},
    }, profiles={})
    graph.nodes["R"]["assets"]["cheap"]["profile"] = [0.4] * 12 + [1.0] * 12

    _, solution = solve(graph)
    load = solution.nodes["R"]["assets"]["load"]

    assert energy(load["consumption"]) == pytest.approx(energy(load["demand"]))
    assert energy(load["deferred"]) > 0
    assert max(load["deferred"]) <= 50 + 1e-6
    assert sum(load["deferred"]) == pytest.approx(sum(load["served"]))


def test_t4_ev_load_consumes_energy():
    """F6: loads take positive MW; an EV load raises generation."""

    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100},
        "ev": {"_class": "Load", "installed_capacity": 10, "profile": [0.5] * H},
        "gas": {"_class": "Producer", "installed_capacity": 200, "operating_cost": 50},
    })

    _, solution = solve(graph)

    assert np.mean(solution.nodes["R"]["assets"]["gas"]["production"]) == pytest.approx(105)


def _reserve_margin_case(pv_credit):

    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100, "type": "load"},
        "gas": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 50},
        # Too little output to be worth building for energy, but cheaper per MW than a peaker.
        "pv": {"_class": "Producer", "profile": [0] * 6 + [0.01] * 18, "capacity_credit": pv_credit,
               "capex_capacity": np.inf, "capex_cost": 9e4, "capital_charge_rate": 0.1},
        "peaker": {"_class": "Producer", "operating_cost": 200, "capex_capacity": np.inf,
                   "capex_cost": 1e5, "capital_charge_rate": 0.1},
    })
    policies = {"rm": {"_class": "Reserve_Margin", "margin": 0.15}}

    _, solution = solve(graph, policies)

    return solution.nodes["R"]["assets"]


def test_t5_reserve_margin_uses_capacity_credits():
    """F4: with solar credited at 0, firm capacity is built for the reserve margin."""

    assets = _reserve_margin_case(pv_credit=0.0)

    assert assets["peaker"]["new_capacity"][0] == pytest.approx(15, rel=1e-6)
    assert assets["pv"]["new_capacity"][0] == pytest.approx(0, abs=1e-6)


def test_t5_full_credit_reproduces_the_old_behaviour():
    """With a credit of 1.0 (v1 behaviour) nameplate solar meets the margin instead."""

    assets = _reserve_margin_case(pv_credit=1.0)

    assert assets["pv"]["new_capacity"][0] == pytest.approx(15, rel=1e-6)
    assert assets["peaker"]["new_capacity"][0] == pytest.approx(0, abs=1e-6)


def test_t6_solar_is_curtailed_not_wasted():
    """F3: surplus solar is curtailed at no cost instead of paying a wastage penalty."""

    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100},
        "pv": {"_class": "Producer", "installed_capacity": 300, "profile": [0] * 6 + [0.8] * 12 + [0] * 6},
        "gas": {"_class": "Producer", "installed_capacity": 200, "operating_cost": 50},
    })

    network, solution = solve(graph, wastage_cost=1e3)
    pv = solution.nodes["R"]["assets"]["pv"]

    assert energy(solution.nodes["R"]["wastage"]) == pytest.approx(0, abs=1e-6)
    assert max(pv["production"]) == pytest.approx(100)  # curtailed to demand
    assert network.objective_value == pytest.approx(50 * 100 * 12)  # gas at night only
