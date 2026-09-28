"""Small builders shared by the tests."""

import networkx as nx
import numpy as np

import good

H = 24


def region_graph(assets, profiles=None, name="R"):
    """A one-region graph."""

    graph = nx.DiGraph()
    graph.add_node(name, _class="Region", assets=assets, profiles=profiles or {})

    return graph


def solve(graph, policies=None, steps=(0, H), **kwargs):
    """Build and solve; return the network and its solution graph."""

    network = good.Network(steps=steps, **kwargs).from_graph(graph, policies or {})
    network.build()
    network.solve()

    return network, network.solution_graph()


def energy(series, dt=1.0):

    return float(np.sum(series)) * dt
