import json

import numpy as np
import networkx as nx

# Building a graph to use as a Network input

def build_graph(assets, lines, profiles, policies, **kwargs):

    nodes = build_nodes(assets, profiles, policies)

    graph = graph_from_nlg({'nodes': nodes, 'links': lines}, directed = True)

    return graph

def build_nodes(assets, profiles, policies):

    # Getting unique regions
    regions = np.unique([p['region'] for p in assets])

    # Getting unique jurisdictions
    jurisdictions = np.unique(
        [p['jurisdiction'] for p in assets if p['jurisdiction'] is not None]
        )

    nodes = []

    for region in regions:

        node = {'id': region, '_class': 'Region'}

        # Adding assets
        node['assets'] = [p for p in assets if p['region'] == region]

        # Adding profiles
        node['profiles'] = (
            {k: v for k, v in profiles.items() if k.split(':')[0] == region}
            )

        nodes.append(node)

    for jurisdiction in jurisdictions:

        node = {'id': jurisdiction, '_class': 'Jurisdiction'}

        # Adding policies
        node['policies'] = [p for p in policies if p['jurisdiction'] == jurisdiction]

        nodes.append(node)

    return nodes

# General utilities

def cypher(graph):

	encoder = {k: idx for idx, k in enumerate(graph.nodes)}
	decoder = {idx: k for idx, k in enumerate(graph.nodes)}

	return encoder, decoder

# Functions for NLG JSON handling 

class NpEncoder(json.JSONEncoder):
	'''
	Encoder to allow for numpy types to be converted to default types for
	JSON serialization. For use with json.dump(s)/load(s).
	'''
	def default(self, obj):

		if isinstance(obj, np.integer):

			return int(obj)

		if isinstance(obj, np.floating):

			return float(obj)

		if isinstance(obj, np.ndarray):

			return obj.tolist()

		return super(NpEncoder, self).default(obj)

def nlg_to_json(nlg, filename):
	'''
	Writes nlg to JSON, overwrites previous
	'''

	with open(filename, 'w') as file:

		json.dump(nlg, file, indent = 4, cls = NpEncoder)

def append_nlg(nlg, filename):
	'''
	Writes nlg to JSON, appends to existing - NEEDS UPDATING
	'''

	nlg_from_file = Load(filename)

	nlg = dict(**nlg_from_file, **nlg)

	with open(filename, 'a') as file:

		json.dump(nlg, file, indent = 4, cls = NpEncoder)

def nlg_from_json(filename):
	'''
	Loads graph from nlg JSON
	'''

	with open(filename, 'r') as file:

		nlg = json.load(file)

	return nlg

# Functions for NetworkX graph .json handling

def graph_to_json(graph, filename, **kwargs):
	'''
	Writes graph to JSON, overwrites previous
	'''

	with open(filename, 'w') as file:

		json.dump(nlg_from_graph(graph, **kwargs), file, indent = 4, cls = NpEncoder)

def graph_from_json(filename, **kwargs):
	'''
	Loads graph from nlg JSON
	'''

	with open(filename, 'r') as file:

		nlg = json.load(file)

	return nx.node_link_graph(nlg, **kwargs)

# Functions for converting between NLG and NetworkX graphs

def graph_from_nlg(nlg, **kwargs):

	return nx.node_link_graph(nlg, multigraph = False, **kwargs)

def nlg_from_graph(nlg, **kwargs):

	nlg = nx.node_link_data(nlg, **kwargs)

	return nlg

# Functions for graph operations

def subgraph(graph, nodes):

	_node = graph._node
	_adj = graph._adj

	node_list = [(n, _node[n]) for n in nodes]

	edge_list = []

	for source in nodes:
		for target in nodes:

			edge_list.append((source, target, _adj[source].get(target, None)))

	edge_list = [e for e in edge_list if e[2] is not None]

	subgraph = graph.__class__()

	subgraph.add_nodes_from(node_list)

	subgraph.add_edges_from(edge_list)

	subgraph.graph.update(graph.graph)

	return subgraph

def supergraph(graphs):

	supergraph = graphs[0].__class__()

	nodes = []

	edges = []

	names = []

	show = True

	for graph in graphs:

		for source, adj in graph._adj.items():

			names.append(source)

			coords_s = (graph._node[source]['x'], graph._node[source]['y'])

			nodes.append((coords_s, graph._node[source]))

			for target, edge in adj.items():

				coords_t = (graph._node[target]['x'], graph._node[target]['y'])

				edges.append((coords_s, coords_t, edge))

	supergraph.add_nodes_from(nodes)

	supergraph.add_edges_from(edges)

	supergraph = nx.relabel_nodes(
		supergraph, {k: names[idx] for idx, k in enumerate(supergraph.nodes)}
		)

	return supergraph

def remove_self_edges(graph):

	graph.remove_edges_from(nx.selfloop_edges(graph))

	return graph