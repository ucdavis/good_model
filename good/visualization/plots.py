'''
Plots of GOOD solutions. Each function takes the input ``graph`` (for asset
attributes such as ``type`` and ``fuel``) and the ``solution`` graph from
``Network.solution_graph()``. Power is shown in GW and prices in $/MWh.

Requires matplotlib (``pip install good[plot]``).
'''

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FUEL_CATEGORIES = {
    "natural gas": "Natural Gas",
    "coal": "Coal",
    "oil": "Oil",
    "nuclear": "Nuclear",
    "hydro": "Hydro",
    "pump hydro": "Pumped Hydro",
    "wind": "Wind",
    "solar": "Solar",
    "biomass": "Biomass",
    "geothermal": "Geothermal",
    "battery": "Battery Storage",
    "waste": "Waste",
    "import": "Import",
    "non-fossil": "Other Non-Fossil",
}

FUEL_COLORS = {
    "Natural Gas": "#d9822b", "Coal": "#6b6b6b", "Oil": "#b5739d", "Nuclear": "#7a4fa3",
    "Hydro": "#2f6fb0", "Pumped Hydro": "#6fa3d8", "Wind": "#3d9970", "Solar": "#e3b505",
    "Biomass": "#8fbf5a", "Geothermal": "#9c5b36", "Battery Storage": "#c94c4c",
    "Waste": "#7d2e2e", "Import": "#40b0bf", "Other Non-Fossil": "#a7c7e7", "Other": "#bbbbbb",
}


def _style(ax, **kw):

    ax.set(facecolor="whitesmoke", **kw)
    ax.grid(ls="--")

    if ax.get_legend_handles_labels()[0]:

        ax.legend(fontsize="x-small")

    return ax


def _attribute(graph, region, handle, key, default=None):

    return graph.nodes[region]["assets"].get(handle, {}).get(key, default)


def fuel_category(asset):
    '''Display category for an asset attribute dictionary.'''

    if asset.get("_class") == "Store":

        fuel = str(asset.get("fuel") or asset.get("type") or "battery").lower()

        return "Pumped Hydro" if "pump" in fuel else "Battery Storage"

    fuel = asset.get("fuel") or asset.get("type")

    return FUEL_CATEGORIES.get(str(fuel).lower(), "Other") if fuel else "Other"


def plot_lmps(ax, graph, solution):
    '''Regional clearing prices ($/MWh).'''

    for region, node in solution.nodes(data=True):

        ax.plot(node.get("clearing_price", []), label=region)

    return _style(ax, ylabel="Regional clearing price [$/MWh]", xlabel="Step")


def plot_demand(ax, graph, solution):
    '''Total consumption of each region's loads (GW), after any flexible shifting.'''

    for region, node in solution.nodes(data=True):

        series = [a["consumption"] for a in node["assets"].values() if "consumption" in a]

        if series:

            ax.plot(np.sum(series, axis=0) / 1e3, label=region)

    return _style(ax, ylabel="Regional demand [GW]", xlabel="Step")


plot_base_loads = plot_demand


def plot_total_generation(ax, graph, solution):
    '''Output of producers and net discharge of stores by region (GW).'''

    for region, node in solution.nodes(data=True):

        series = [a["net"] for a in node["assets"].values() if "consumption" not in a]

        if series:

            ax.plot(np.sum(series, axis=0) / 1e3, label=region)

    return _style(ax, ylabel="Regional generation [GW]", xlabel="Step")


def plot_net_generation(ax, graph, solution):
    '''Generation minus demand by region (GW); positive regions export.'''

    for region, node in solution.nodes(data=True):

        ax.plot(np.sum([a["net"] for a in node["assets"].values()], axis=0) / 1e3, label=region)

    return _style(ax, ylabel="Regional net generation [GW]", xlabel="Step")


def _series_by(graph, solution, key_fun):

    totals = {}

    for region, node in solution.nodes(data=True):

        for handle, result in node["assets"].items():

            if "consumption" in result:

                continue

            key = key_fun(graph.nodes[region]["assets"].get(handle, {}))
            totals[key] = totals.get(key, 0) + np.asarray(result["net"])

    return totals


def plot_generation_by_type(ax, graph, solution):
    '''Generation by asset ``type`` (GW), with total unserved and dumped energy.'''

    for key, values in sorted(_series_by(graph, solution, lambda a: a.get("type", "other")).items()):

        ax.plot(values / 1e3, label=key)

    shortfall = np.sum([n["shortfall"] for _, n in solution.nodes(data=True)], axis=0)
    wastage = np.sum([n["wastage"] for _, n in solution.nodes(data=True)], axis=0)

    ax.plot(shortfall / 1e3, ls="--", label="shortfall")
    ax.plot(wastage / 1e3, ls="--", label="wastage")

    return _style(ax, ylabel="Power [GW]", xlabel="Step")


def plot_generation_by_fuel(ax, graph, solution):
    '''Generation by fuel category (GW), stacked.'''

    series = _series_by(graph, solution, fuel_category)
    order = [k for k in FUEL_COLORS if k in series]

    positive = [np.clip(series[k], 0, None) / 1e3 for k in order]
    ax.stackplot(range(len(positive[0])) if positive else [], *positive,
                 labels=order, colors=[FUEL_COLORS[k] for k in order])

    return _style(ax, ylabel="Generation [GW]", xlabel="Step")


def plot_new_capacity(ax, graph, solution):
    '''New capacity built, by asset type (GW; storage is power capacity).'''

    totals = {}

    for region, node in solution.nodes(data=True):

        for handle, result in node["assets"].items():

            new = result.get("new_capacity", [0.0])[0]

            if new > 0:

                kind = _attribute(graph, region, handle, "type", "other")
                totals[kind] = totals.get(kind, 0.0) + new / 1e3

    ax.barh(list(totals), list(totals.values()), color="xkcd:seafoam", ec="k")

    return _style(ax, xlabel="New capacity [GW]")


plot_capex_by_type = plot_new_capacity


def generation_mix(graph, solution, regions=None):
    '''Energy (MWh) by region and fuel category as a DataFrame.'''

    dt = solution.graph.get("time_step", 1.0)
    rows = []

    for region, node in solution.nodes(data=True):

        if regions is not None and region not in regions:

            continue

        for handle, result in node["assets"].items():

            if "consumption" in result:

                continue

            asset = graph.nodes[region]["assets"].get(handle, {})
            rows.append((region, fuel_category(asset), float(np.sum(result["net"])) * dt))

    frame = pd.DataFrame(rows, columns=["region", "fuel", "energy"])

    return frame.pivot_table(index="region", columns="fuel", values="energy", aggfunc="sum", fill_value=0.0)


def plot_dispatch_fuel_mix(graph, solution, regions=None, total_label="All regions"):
    '''
    Share of generation by fuel for each region and for all regions together
    (stacked bars), and total generation against total demand.
    Returns the matplotlib figure.
    '''

    mix = generation_mix(graph, solution, regions)
    mix.loc[total_label] = mix.sum()

    shares = mix.clip(lower=0)
    shares = shares.div(shares.sum(axis=1), axis=0).fillna(0.0)
    order = [k for k in FUEL_COLORS if k in shares.columns]

    fig, (left, right) = plt.subplots(1, 2, figsize=(16, 6), gridspec_kw={"width_ratios": [3, 1]})

    shares[order].plot(kind="bar", stacked=True, ax=left, color=[FUEL_COLORS[k] for k in order])
    left.set(ylabel="Generation share", xlabel="Region", title="Fuel mix by region")
    left.legend(title="Fuel", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize="small")

    dt = solution.graph.get("time_step", 1.0)
    demand = sum(
        float(np.sum(r["consumption"])) * dt
        for region, node in solution.nodes(data=True) if regions is None or region in regions
        for r in node["assets"].values() if "consumption" in r
    )
    generation = float(mix.drop(index=total_label).to_numpy().sum())

    right.bar(["Generation", "Demand"], [generation, demand], color=["steelblue", "orange"])
    right.set(ylabel="Energy [MWh]", title="Generation and demand")

    for i, value in enumerate([generation, demand]):

        right.text(i, value * 1.01, f"{value:,.0f}", ha="center")

    fig.tight_layout()

    return fig
