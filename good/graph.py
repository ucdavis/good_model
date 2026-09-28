'''
Reading, writing and slicing power system graphs.

Graphs are stored as NetworkX node-link JSON, optionally gzip-compressed
(".json.gz"). Edges are stored under the "links" key.
'''

import networkx as nx

from .utilities import read_json, write_json


def cypher(graph):

    encoder = {k: idx for idx, k in enumerate(graph.nodes)}
    decoder = {idx: k for idx, k in enumerate(graph.nodes)}

    return encoder, decoder


def graph_from_nlg(nlg, **kwargs):
    '''Build a graph from node-link data whose edges are under "links".'''

    try:

        return nx.node_link_graph(nlg, edges="links", **kwargs)

    except TypeError:  # NetworkX < 3.4 has no "edges" keyword

        return nx.node_link_graph(nlg, **kwargs)


def nlg_from_graph(graph, **kwargs):
    '''Node-link data for a graph, with edges under "links".'''

    try:

        return nx.node_link_data(graph, edges="links", **kwargs)

    except TypeError:  # NetworkX < 3.4 has no "edges" keyword

        return nx.node_link_data(graph, **kwargs)


def graph_to_json(graph, filename, indent=None, **kwargs):
    '''Write a graph to node-link JSON; a ".gz" suffix compresses it.'''

    write_json(nlg_from_graph(graph, **kwargs), filename, indent=indent)


def graph_from_json(filename, **kwargs):
    '''Load a graph from node-link JSON (".json" or ".json.gz").'''

    return graph_from_nlg(read_json(filename), **kwargs)


def subgraph(graph, nodes):
    '''A copy of ``graph`` restricted to ``nodes`` and the edges among them.'''

    node_list = [(n, graph._node[n]) for n in nodes]

    edge_list = [
        (source, target, graph._adj[source][target])
        for source in nodes for target in nodes
        if target in graph._adj[source]
    ]

    result = graph.__class__()
    result.add_nodes_from(node_list)
    result.add_edges_from(edge_list)
    result.graph.update(graph.graph)

    return result


def supergraph(graphs):
    '''Union of several graphs; later graphs win where they overlap.'''

    result = graphs[0].__class__()

    for graph in graphs:

        result.add_nodes_from(graph.nodes(data=True))
        result.add_edges_from(graph.edges(data=True))
        result.graph.update(graph.graph)

    return result


def remove_self_edges(graph):

    graph.remove_edges_from(list(nx.selfloop_edges(graph)))

    return graph
