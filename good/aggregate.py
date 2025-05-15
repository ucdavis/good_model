import time
import json

import numpy as np
import networkx as nx

from .progress_bar import ProgressBar

default_combination = {
    'oris_code': 'all',
    'egrid_id': 'all',
    'type': 'first',
    'fuel': 'first',
    '_class': 'first',
    'profile': 'first',
    'region': 'first',
    'jurisdiction': 'first',
    'nerc': 'first',
    'utility': 'all',
    'x': 'mean',
    'y': 'mean',
    'installed_capacity': 'sum',
    'capacity_factor': 'mean',
    'dispatchable': 'first',
    'combinable': 'first',
    'renewable': 'first',
    'extensible': 'first',
    'capex_capacity': 'sum',
    'capex_cost': 'sum',
    'operating_cost': 'mean',
    'heat_rate': 'mean',
    'nox': 'mean',
    'so2': 'mean',
    'co2': 'mean',
    'ch4': 'mean',
    'n2o': 'mean',
    'pm': 'mean',
}

default_clustering = {
    'weight': 'weight',
    'resolution': 1.1,
    'cutoff': 1,
}

default_feasibility = {
    'type': lambda s, t: s['type'] == t['type'],
    'fuel': lambda s, t: s.get('fuel', '') == t.get('fuel', ''),
    'combinable': (
        lambda s, t: (
            s.get('combinable', False) and t.get('combinable', False)
        )
    ),
}

default_distance = {
    'heat_rate': (
        lambda s, t: (
            np.abs(
                s.get('heat_rate', 0) - t.get('heat_rate', 0)
            ) * 3412 / 2000
        )
    ),
    'operating_cost': (
        lambda s, t: (
            np.abs(
                s.get('operating_cost', 0) - t.get('operating_cost', 0)
            ) * 3.6e9 / 2000
        )
    ),
    'co2': (
        lambda s, t: (
            np.abs(
                s.get('co2', 0) - t.get('co2', 0)
            ) * 1 / (0.453592 / 3.6e9) / 10
        )
    ),
}

def aggregate(graph, **kwargs):

    for source in ProgressBar(list(graph.nodes()), **kwargs.get('progress_bar', {})):

        graph._node[source]['assets'] = aggregate_assets(
            graph._node[source]['assets'], **kwargs
            )

    return graph

def aggregate_assets(assets, **kwargs):

    feasibility = kwargs.get('feasibility', default_feasibility)
    clustering = kwargs.get('clustering', default_clustering)
    combination = kwargs.get('combination', default_combination)
    distance = kwargs.get('distance', default_distance)

    edges = []

    for source_id, source_asset in assets.items():
        for target_id, target_asset in assets.items():

            if source_id == target_id:

                continue

            feasible = np.product(
                [True] + [fun(source_asset, target_asset) for fun in feasibility.values()]
                )

            if not feasible:

                continue

            weight = np.sum(
                [fun(source_asset, target_asset) for fun in distance.values()]
                )

            edge = {
                'weight': np.exp(-weight),
                }

            edges.append((source_id, target_id, edge))

    g = nx.Graph()
    g.add_edges_from(edges)

    communities = [
        list(c) for c in nx.community.greedy_modularity_communities(g, **clustering)
        ]

    included = list(g.nodes)
    excluded = list(set(list(assets.keys())) - set(included))

    aggregated = combine(assets, communities, functions = combination)

    aggregated = {**aggregated, **{k: v for k, v in assets.items() if k not in included}}

    return aggregated

def combine_values(values, weights, fun):

    if callable(fun):

        return fun(values)

    elif isinstance(fun, str):

        if fun == 'first':

            return values[0]

        if fun == 'all':

            return values

        if fun == 'sum':

            return sum(values)

        if fun == 'mean':

            n = len(values)
            denominator = 1 if sum(weights) == 0 else sum(weights)

            return sum([values[idx] * weights[idx] for idx in range(n)]) / denominator

    return values

def combine(plants, communities, **kwargs):

    weight = kwargs.get('weight', 'installed_capacity')
    functions = kwargs.get('functions', {})

    combined = {}

    for idx, community in enumerate(communities):

        members = [plants[key] for key in community]
        weights = [m[weight] for m in members]
        sum_weight = sum(weights)

        if sum_weight == 0:

            sum_weight = 1

        handle = f"{community[0]}_combined"

        plant = {
            'id': handle,
            "components": community,
            weight: sum([m[weight] for m in members])
            }

        for key, val in members[0].items():

            if key in ['id', weight]:

                continue

            if key not in functions:

                continue

            values = [m.get(key, None) for m in members if key in m]

            plant[key] = combine_values(values, weights, functions[key])

        combined[handle] = plant

    return combined