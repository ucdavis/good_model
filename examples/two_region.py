"""
A two-region, 24-hour GOOD model: the quickstart example.

Region "coast" has demand, solar that can be expanded, a battery option and
flexible EV charging. Region "inland" has cheap gas and wind. A transmission
corridor links them. A 40% renewable standard applies to the coast.

Run it with ``python examples/two_region.py``; it finishes in a few seconds.
"""

import networkx as nx
import numpy as np

import good

HOURS = 24

solar = [0, 0, 0, 0, 0, 0.05, 0.2, 0.4, 0.6, 0.75, 0.85, 0.9,
         0.9, 0.85, 0.75, 0.6, 0.4, 0.2, 0.05, 0, 0, 0, 0, 0]
wind = [0.6, 0.62, 0.65, 0.63, 0.6, 0.55, 0.5, 0.42, 0.35, 0.3, 0.28, 0.27,
        0.27, 0.28, 0.3, 0.33, 0.38, 0.45, 0.52, 0.58, 0.6, 0.62, 0.63, 0.62]
demand = [0.62, 0.6, 0.58, 0.58, 0.6, 0.66, 0.75, 0.82, 0.85, 0.86, 0.87, 0.88,
          0.89, 0.9, 0.92, 0.95, 0.98, 1.0, 0.99, 0.95, 0.88, 0.8, 0.72, 0.66]
ev = [0.3] * 7 + [0.1] * 10 + [0.6] * 7  # arrives home in the evening


def build_graph():

    graph = nx.DiGraph()

    graph.add_node("coast", _class="Region", profiles={"demand": demand, "solar": solar, "ev": ev}, assets={
        "coast_demand": {"_class": "Load", "installed_capacity": 1000, "profile": "demand"},
        "coast_ev": {"_class": "Load", "installed_capacity": 200, "profile": "ev",
                     "flex_capacity": 100, "flex_max_delay": 8, "flex_max_advance": 8},
        "coast_peaker": {"_class": "Producer", "installed_capacity": 600, "operating_cost": 95,
                         "fuel": "natural gas", "type": "generator", "jurisdiction": "CA"},
        "coast_solar": {"_class": "Producer", "installed_capacity": 300, "profile": "solar",
                        "type": "solar", "fuel": "solar", "renewable": True, "jurisdiction": "CA",
                        "capex_capacity": 2000, "capex_cost": 1.0e6, "fom_cost": 11_000, "lifetime": 30,
                        "capacity_credit": 0.1},
        "coast_battery": {"_class": "Store", "duration": 4, "charge_efficiency": 0.92,
                          "discharge_efficiency": 0.92, "capex_capacity": np.inf, "capex_cost": 1.2e6,
                          "fom_cost": 30_000, "lifetime": 15, "type": "battery", "jurisdiction": "CA"},
    })

    graph.add_node("inland", _class="Region", profiles={"wind": wind}, assets={
        "inland_gas": {"_class": "Producer", "installed_capacity": 800, "operating_cost": 35,
                       "min_output": 0.2, "ramp_rate": 0.3, "fuel": "natural gas", "type": "generator",
                       "jurisdiction": "NV"},
        "inland_wind": {"_class": "Producer", "installed_capacity": 400, "profile": "wind",
                        "type": "wind", "fuel": "wind", "renewable": True, "jurisdiction": "NV",
                        "capacity_credit": 0.15},
    })

    line = {"_class": "Transmission", "installed_capacity": 300, "efficiency": 0.972, "operating_cost": 2,
            "corridor": "coast-inland", "capex_capacity": 1000, "capex_cost": 1.5e6, "lifetime": 40}

    graph.add_edge("inland", "coast", _class="Link", lines={"inland_to_coast": dict(line)})
    graph.add_edge("coast", "inland", _class="Link", lines={"coast_to_inland": dict(line)})

    return graph


policies = {
    "coast_rps": {
        "_class": "Portfolio_Standard",
        "ratio": 0.4,
        "include": {"renewable": True, "jurisdiction": "CA"},
        "exclude": {"renewable": {"not": True}, "_class": "Producer", "jurisdiction": "CA"},
    },
    "reserve_margin": {"_class": "Reserve_Margin", "margin": 0.15},
}


def main():

    graph = build_graph()

    network = good.Network(steps=(0, HOURS)).from_graph(graph, policies)
    network.build()
    network.solve()

    solution = network.solution_graph()
    coast = solution.nodes["coast"]

    print(f"Total cost for the day: ${network.objective_value:,.0f}")
    print(f"New solar: {max(0.0, coast['assets']['coast_solar']['new_capacity'][0]):,.0f} MW")
    print(f"New battery: {max(0.0, coast['assets']['coast_battery']['new_capacity'][0]):,.0f} MW "
          f"/ {max(0.0, coast['assets']['coast_battery']['new_energy'][0]):,.0f} MWh")
    print(f"New transmission: {max(0.0, solution.edges['inland', 'coast']['lines']['inland_to_coast']['new_capacity'][0]):,.0f} MW")
    print(f"Coast prices ($/MWh): min {min(coast['clearing_price']):.1f}, max {max(coast['clearing_price']):.1f}")

    return network, solution


if __name__ == "__main__":

    main()
