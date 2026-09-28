import json
from pathlib import Path

import networkx as nx
import numpy as np
import pytest

import good
from good import criteria, economics, migrate
from good.exceptions import GOOD_LegacyInput, GOOD_ValidationError
from helpers import H, region_graph, solve

DATA = Path(__file__).parent / "data"


# ---------------------------------------------------------------- economics

def test_capital_recovery_factor():

    assert economics.capital_recovery_factor(0.07, 20) == pytest.approx(0.0943929, rel=1e-6)
    assert economics.capital_recovery_factor(0.0, 20) == pytest.approx(0.05)


def test_implied_discount_rate_round_trips():

    rate = economics.implied_discount_rate(0.0978, 20)

    assert economics.capital_recovery_factor(rate, 20) == pytest.approx(0.0978, rel=1e-8)


def test_annualized_cost_prefers_charge_rate():

    assert economics.annualized_cost(1000, fom_cost=10, capital_charge_rate=0.1) == pytest.approx(110)
    assert economics.annualized_cost(0, fom_cost=10) == pytest.approx(10)


# ---------------------------------------------------------------- validation

def test_all_problems_reported_together():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": -100},
        "old_store": {"_class": "Store", "installed_capacity": 5, "efficiency": 0.9},
        "hydro": {"_class": "Producer", "profile": "R:hydro:"},
        "mystery": {"_class": "Nonexistent"},
    }, profiles={"R:hydro": [1.0] * H})

    with pytest.raises(GOOD_ValidationError) as error:

        good.Network(steps=(0, H)).from_graph(graph)

    text = str(error.value)

    assert len(error.value.problems) == 4
    assert "loads take positive MW" in text
    assert "charge_efficiency" in text
    assert "'R:hydro:' is not in the node's profiles" in text
    assert "Nonexistent" in text


def test_profile_shorter_than_horizon_is_rejected():
    graph = region_graph({"pv": {"_class": "Producer", "installed_capacity": 1, "profile": [0.5] * 10}})
    network = good.Network(steps=(0, H)).from_graph(graph)

    with pytest.raises(GOOD_ValidationError, match="profile has 10 values"):

        network.build()


def test_legacy_network_arguments_are_explained():

    with pytest.raises(GOOD_LegacyInput, match="amortization_period"):

        good.Network(amortization_period=31536000)


def test_legacy_load_shifting_fields_are_explained():
    graph = region_graph({"load": {"_class": "Load", "installed_capacity": 1, "shift_capacity": 1e9}})

    with pytest.raises(GOOD_ValidationError, match="flex_capacity"):

        good.Network(steps=(0, H)).from_graph(graph)


def test_expansion_needs_annualization():
    graph = region_graph({"pv": {"_class": "Producer", "capex_capacity": 10, "capex_cost": 1e6}})

    with pytest.raises(GOOD_ValidationError, match="lifetime"):

        good.Network(steps=(0, H)).from_graph(graph)


def test_json_schema_covers_every_component():

    schema = good.schema.json_schema()

    assert {"Producer", "Store", "Load", "Transmission", "Region", "Reserve_Margin"} <= set(schema)
    assert "duration" in schema["Store"]["properties"]


# ---------------------------------------------------------------- criteria and policies

def test_filters():
    assets = {
        "a": {"renewable": True, "jurisdiction": "CA", "_class": "Producer", "installed_capacity": 10},
        "b": {"renewable": False, "jurisdiction": "NV", "_class": "Producer", "installed_capacity": 100},
        "c": {"_class": "Store", "jurisdiction": "CA"},
    }

    assert criteria.select(assets, {"renewable": True}) == ["a"]
    assert criteria.select(assets, {"renewable": {"not": True}}) == ["b", "c"]
    assert criteria.select(assets, {"jurisdiction": ["CA", "NV"], "_class": {"not": "Store"}}) == ["a", "b"]
    assert criteria.select(assets, {"installed_capacity": {">=": 50}}) == ["b"]
    assert criteria.select(assets, {}) == ["a", "b", "c"]


def test_lambda_strings_are_refused_not_evaluated():

    with pytest.raises(GOOD_LegacyInput, match="convert_policies"):

        criteria.select({"a": {}}, {0: "lambda a: __import__('os').system('echo pwned')"})


def test_convert_policies_translates_the_v1_file_without_eval():

    v1 = json.loads((DATA / "policies_v1.json").read_text())
    v2 = migrate.convert_policies(v1)

    assert v2["rps_CA"]["include"] == {
        "renewable": True, "_class": {"not": "Store"}, "type": {"not": "load"}, "jurisdiction": "CA",
    }
    assert v2["rps_CA"]["exclude"]["renewable"] == {"not": True}
    assert "inclusion_criteria" not in v2["rps_CA"]

    with pytest.raises(ValueError):

        migrate.lambda_to_filter("lambda a: len(a) > 3")


def test_portfolio_standard_binds():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 100},
        "wind": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 60, "renewable": True},
        "gas": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 30, "renewable": False},
    })
    policies = {"rps": {"_class": "Portfolio_Standard", "ratio": 0.4,
                        "include": {"renewable": True}, "exclude": {"renewable": False}}}

    _, solution = solve(graph, policies)
    wind = sum(solution.nodes["R"]["assets"]["wind"]["production"])

    assert wind == pytest.approx(0.4 * 100 * H)


def test_capacity_target_builds_capacity():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 10},
        "gas": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 30},
        "pv": {"_class": "Producer", "type": "solar", "capex_capacity": 500, "capex_cost": 1e5,
               "capital_charge_rate": 0.1, "profile": [0.0] * H},
    })
    policies = {"ct": {"_class": "Capacity_Target", "target": 70, "include": {"type": "solar"}}}

    _, solution = solve(graph, policies)

    assert solution.nodes["R"]["assets"]["pv"]["new_capacity"][0] == pytest.approx(70)


def test_non_compliance_slack_prices_a_shortfall():
    graph = region_graph({
        "load": {"_class": "Load", "installed_capacity": 10},
        "gas": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 30},
    })
    policies = {"ct": {"_class": "Capacity_Target", "target": 70, "include": {"type": "solar"},
                       "non_compliance_capacity": 1000, "non_compliance_cost": 5}}

    network, solution = solve(graph, policies)

    assert solution.graph["policies"]["ct"]["non_compliance"] == [pytest.approx(70)]
    assert network.objective_value == pytest.approx(30 * 10 * H + 70 * 5)


# ---------------------------------------------------------------- aggregation

def _plants():
    base = {"_class": "Producer", "type": "generator", "fuel": "natural gas", "combinable": True,
            "jurisdiction": "CA", "profile": None}

    plants = {
        f"g{i}": {**base, "installed_capacity": 100 + i, "heat_rate": 7000 + 50 * i,
                  "operating_cost": 30 + i, "co2": 400 + i}
        for i in range(20)
    }
    plants["nv"] = {**base, "jurisdiction": "NV", "installed_capacity": 50, "heat_rate": 7000,
                    "operating_cost": 30, "co2": 400}
    plants["s5"] = {"_class": "Producer", "type": "solar", "combinable": True, "profile": "R:solar:5",
                    "installed_capacity": 10, "capex_cost": 0}
    plants["s6"] = {"_class": "Producer", "type": "solar", "combinable": True, "profile": "R:solar:6",
                    "installed_capacity": 20, "capex_cost": 0}
    plants["s6b"] = {"_class": "Producer", "type": "solar", "combinable": True, "profile": "R:solar:6",
                     "installed_capacity": 30, "capex_cost": 0}
    plants["new"] = {**base, "capex_capacity": 100, "installed_capacity": 0}

    return plants


def test_aggregation_preserves_capacity_and_boundaries():
    plants = _plants()
    merged = good.aggregate.aggregate_assets(plants, ratio=0.2)

    total = lambda d, **kw: sum(a["installed_capacity"] for a in d.values()
                                if all(a.get(k) == v for k, v in kw.items()))

    assert total(merged) == pytest.approx(total(plants))
    assert total(merged, jurisdiction="NV") == pytest.approx(50)  # never merged across states
    assert total(merged, profile="R:solar:5") == pytest.approx(10)  # never merged across profiles
    assert total(merged, profile="R:solar:6") == pytest.approx(50)
    assert "new" in merged  # expandable assets are left alone
    assert len([a for a in merged.values() if a.get("fuel") == "natural gas" and a.get("jurisdiction") == "CA"
                and a.get("capex_capacity", 0) == 0]) == 4


def test_aggregation_uses_capacity_weighted_means():
    plants = {
        "a": {"_class": "Producer", "combinable": True, "installed_capacity": 100, "operating_cost": 10, "capex_cost": 1000},
        "b": {"_class": "Producer", "combinable": True, "installed_capacity": 300, "operating_cost": 10, "capex_cost": 2000},
    }
    merged = good.aggregate.aggregate_assets(plants, ratio=0.1)
    (plant,) = merged.values()

    assert plant["installed_capacity"] == pytest.approx(400)
    assert plant["capex_cost"] == pytest.approx(1750)


def test_aggregate_rejects_v1_arguments():

    with pytest.raises(GOOD_LegacyInput):

        good.aggregate.aggregate(nx.DiGraph(), clustering={"resolution": 1.1})


# ---------------------------------------------------------------- migration

def _v1_graph():
    wind = np.zeros((365, 25))
    days = np.concatenate([np.arange(1, n + 1) for n in [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]])
    wind[:, 0] = days / 1000
    wind[:, 1:] = np.tile(np.linspace(0.1, 0.9, 24), (365, 1))

    hydro_index = np.repeat([1.0, 1.5, 2.0], [3000, 3000, 2759])

    graph = nx.DiGraph()
    graph.add_node("WEC_X", _class="Region", profiles={
        "WEC_X:load": [1.0] * 8760, "WEC_X:wind:": wind.ravel().tolist(), "WEC_X:hydro": hydro_index.tolist(),
    }, assets={
        "base_load": {"_class": "Load", "type": "load", "installed_capacity": -2.0e9, "profile": "WEC_X:load"},
        "w": {"_class": "Load", "type": "wind", "installed_capacity": 1e8, "profile": "WEC_X:wind:",
              "capex_capacity": 5e8, "capex_cost": 0.00146802, "renewable": True, "dispatchable": False},
        "h": {"_class": "Producer", "type": "hydro", "installed_capacity": 1e8, "capacity_factor": 0.4,
              "profile": "WEC_X:hydro:", "operating_cost": 1e-10},
        "g": {"_class": "Producer", "type": "generator", "installed_capacity": 5e8, "profile": "WEC_X:generator:",
              "operating_cost": 7.1e-9, "co2": 1.2e-7, "heat_rate": 2.7},
        "phs": {"_class": "Store", "type": "storage", "fuel": "pump hydro", "installed_capacity": 1.4e9},
        "bat": {"_class": "Store", "type": "battery", "installed_capacity": 0, "capex_capacity": np.inf,
                "capex_cost": 8.3e-5},
    })
    graph.add_node("WEC_Y", _class="Region", assets={})
    line = {"_class": "Transmission", "installed_capacity": 2.75e9, "operating_cost": 2.2e-9, "capex_capacity": 0,
            "capex_cost": 0}
    graph.add_edge("WEC_X", "WEC_Y", _class="Link", lines={"l1": dict(line)})
    graph.add_edge("WEC_Y", "WEC_X", _class="Link", lines={"l2": dict(line)})

    return graph


def test_migration_converts_units_and_repairs_data():
    v1 = _v1_graph()

    assert migrate.is_v1(v1)

    v2 = migrate.from_v1(v1)
    node = v2.nodes["WEC_X"]
    assets = node["assets"]

    assert not migrate.is_v1(v2)
    assert assets["base_load"]["installed_capacity"] == pytest.approx(2000)
    assert assets["w"]["_class"] == "Producer" and assets["w"]["dispatchable"] is True
    assert assets["w"]["capex_cost"] == pytest.approx(1_468_020)  # $/MW
    assert assets["w"]["capex_capacity"] == pytest.approx(500)
    assert len(node["profiles"]["WEC_X:wind:"]) == 8760
    assert node["profiles"]["WEC_X:wind:"][:24] == pytest.approx(np.linspace(0.1, 0.9, 24))
    assert assets["h"]["profile"] == "WEC_X:hydro"
    assert np.mean(node["profiles"]["WEC_X:hydro"]) == pytest.approx(1.0)
    assert assets["h"]["energy_budget_window"] == 24
    assert assets["g"]["profile"] is None
    assert assets["g"]["operating_cost"] == pytest.approx(25.56, rel=1e-3)
    assert assets["g"]["co2"] == pytest.approx(432, rel=1e-3)  # kg/MWh
    assert assets["phs"]["duration"] == 10 and assets["phs"]["installed_capacity"] == pytest.approx(1400)
    assert assets["bat"]["capex_cost"] == pytest.approx(1_977_000)
    assert assets["bat"]["charge_efficiency"] == pytest.approx(np.sqrt(0.85))

    line = v2.edges["WEC_X", "WEC_Y"]["lines"]["l1"]

    assert line["installed_capacity"] == pytest.approx(2750)
    assert line["efficiency"] == pytest.approx(0.972)
    assert line["corridor"] == "WEC_X|WEC_Y"


def test_migrated_graph_solves():
    v2 = migrate.from_v1(_v1_graph())
    network = good.Network(steps=(0, 48)).from_graph(v2)
    network.build()
    network.solve()

    assert network.objective_value > 0


def test_wind_repair_refuses_unexpected_layouts():

    with pytest.raises(ValueError):

        migrate.repair_25_hour_days(np.ones(9125))


def test_graph_json_round_trip(tmp_path):
    graph = region_graph({"load": {"_class": "Load", "installed_capacity": 1}})

    for name in ("g.json", "g.json.gz"):

        good.graph.graph_to_json(graph, tmp_path / name)
        loaded = good.graph.graph_from_json(tmp_path / name)

        assert loaded.nodes["R"]["assets"]["load"]["installed_capacity"] == 1
