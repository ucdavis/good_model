'''
Aggregate similar assets within each region to shrink the model.

Assets are first split into groups that must never merge: different class,
type, fuel, profile, jurisdiction, dispatchability or renewable status. Only
assets marked ``combinable`` and not expandable are merged. Within a group,
k-means on standardized features (heat rate, operating cost and CO2 rate by
default) forms clusters, and each cluster becomes one asset.

Grouping by profile keeps wind and solar sites with different resource
profiles apart; grouping by jurisdiction keeps state policies correct.
Merged assets add capacities and take capacity-weighted means of costs and
rates, so total capacity and capacity-weighted averages are preserved.

The work is linear in the number of assets (k-means), replacing the pairwise
similarity graph used before GOOD 2.0.
'''

import math
import warnings

import numpy as np
from scipy.cluster.vq import kmeans2

from .exceptions import GOOD_LegacyInput
from .progress_bar import ProgressBar

default_group_keys = (
    '_class', 'type', 'fuel', 'profile', 'jurisdiction', 'dispatchable', 'renewable',
)

default_features = {
    'heat_rate': 1.0,
    'operating_cost': 1.0,
    'co2': 1.0,
}

default_combination = {
    # identifiers
    'oris_code': 'all',
    'egrid_id': 'all',
    'utility': 'all',
    # capacities add
    'installed_capacity': 'sum',
    'installed_energy': 'sum',
    'capex_capacity': 'sum',
    'x': 'mean',
    'y': 'mean',
    # per-MW quantities are capacity-weighted means
    'capacity_factor': 'mean',
    'capacity_credit': 'mean',
    'min_output': 'mean',
    'ramp_rate': 'mean',
    'duration': 'mean',
    'charge_efficiency': 'mean',
    'discharge_efficiency': 'mean',
    'capex_cost': 'mean',
    'fom_cost': 'mean',
    'operating_cost': 'mean',
    'heat_rate': 'mean',
    'nox': 'mean',
    'so2': 'mean',
    'co2': 'mean',
    'ch4': 'mean',
    'n2o': 'mean',
    'pm': 'mean',
}
'''How to combine each attribute. Attributes not listed keep the first member's value.'''


def _hashable(value):

    if isinstance(value, (list, tuple, np.ndarray)):

        return tuple(np.round(np.asarray(value, dtype=float), 9).tolist())

    if isinstance(value, dict):

        return tuple(sorted((k, _hashable(v)) for k, v in value.items()))

    return value


def _expandable(asset):

    capex_capacity = asset.get('capex_capacity', 0) or 0

    return capex_capacity > 0


def aggregate(graph, ratio=0.1, max_clusters=None, features=None, group_keys=default_group_keys,
              combination=None, seed=0, progress_bar=None, **kwargs):
    '''
    Aggregate the assets of every node in ``graph`` in place and return it.

    ``ratio`` is the target number of clusters as a fraction of each group's
    size (0.1 turns 50 similar plants into 5); ``max_clusters`` caps it.
    ``features`` maps attribute name to weight for clustering.
    '''

    for legacy in ('clustering', 'feasibility', 'distance'):

        if legacy in kwargs:

            raise GOOD_LegacyInput(
                f"aggregate(..., {legacy}=...) was removed in GOOD 2.0; aggregation now uses k-means. "
                "Use ratio=, max_clusters=, features= and group_keys= instead."
            )

    if kwargs:

        raise TypeError(f"aggregate() got unexpected keyword arguments {sorted(kwargs)}")

    nodes = list(graph.nodes())

    for source in ProgressBar(nodes, **(progress_bar or {'disp': False})):

        graph._node[source]['assets'] = aggregate_assets(
            graph._node[source].get('assets', {}),
            ratio=ratio, max_clusters=max_clusters, features=features,
            group_keys=group_keys, combination=combination, seed=seed,
        )

    return graph


def aggregate_assets(assets, ratio=0.1, max_clusters=None, features=None, group_keys=default_group_keys,
                     combination=None, seed=0):
    '''Aggregate one node's asset dictionary (handle to attributes).'''

    features = default_features if features is None else features
    combination = default_combination if combination is None else combination

    groups = {}
    result = {}

    for handle, asset in assets.items():

        if not asset.get('combinable', False) or _expandable(asset):

            result[handle] = asset

            continue

        key = tuple(_hashable(asset.get(k)) for k in group_keys)
        groups.setdefault(key, []).append(handle)

    for members in groups.values():

        for community in cluster(assets, members, features, ratio, max_clusters, seed):

            if len(community) == 1:

                result[community[0]] = assets[community[0]]

            else:

                result.update(combine(assets, [community], functions=combination))

    return result


def cluster(assets, members, features, ratio, max_clusters, seed):
    '''Split ``members`` into clusters with k-means; returns lists of handles.'''

    n = len(members)

    if n == 1:

        return [members]

    names = list(features)

    if names:

        data = np.array(
            [[float(assets[h].get(name, 0.0) or 0.0) for name in names] for h in members]
        )

        spread = data.std(axis=0)
        scaled = np.divide(data - data.mean(axis=0), spread, out=np.zeros_like(data), where=spread > 0)
        scaled = scaled * np.array([features[name] for name in names])

    else:

        scaled = np.zeros((n, 1))

    k = max(1, math.ceil(n * ratio))

    if max_clusters is not None:

        k = min(k, max_clusters)

    distinct = len(np.unique(scaled, axis=0))
    k = min(k, distinct)

    if k == 1:

        return [list(members)]

    with warnings.catch_warnings():

        warnings.simplefilter("ignore")  # empty clusters are dropped below

        _, labels = kmeans2(scaled, k, seed=seed, minit='++')

    communities = {}

    for handle, label in zip(members, labels):

        communities.setdefault(int(label), []).append(handle)

    return list(communities.values())


def combine_values(values, weights, fun):

    if callable(fun):

        return fun(values)

    if fun == 'first':

        return values[0]

    if fun == 'all':

        return values

    if fun == 'sum':

        return sum(values)

    if fun == 'mean':

        total = sum(weights)

        if total == 0:

            return sum(values) / len(values)

        return sum(v * w for v, w in zip(values, weights)) / total

    raise ValueError(f"Unknown combination {fun!r}; use 'first', 'all', 'sum', 'mean' or a function")


def combine(plants, communities, weight='installed_capacity', functions=None):
    '''Merge each community of assets into one asset named "<first member>_combined".'''

    functions = default_combination if functions is None else functions

    combined = {}

    for community in communities:

        members = [plants[key] for key in community]
        weights = [abs(float(m.get(weight, 0.0) or 0.0)) for m in members]

        handle = f"{community[0]}_combined"

        plant = {'id': handle, 'components': list(community)}

        keys = []

        for member in members:

            keys.extend(k for k in member if k not in keys)

        for key in keys:

            if key in ('id', 'components'):

                continue

            present = [(m[key], w) for m, w in zip(members, weights) if key in m]
            values = [v for v, _ in present]
            member_weights = [w for _, w in present]

            fun = functions.get(key, 'first')

            if fun == 'mean' and not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):

                fun = 'first'

            plant[key] = combine_values(values, member_weights, fun)

        combined[handle] = plant

    return combined
