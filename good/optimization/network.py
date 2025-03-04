import time

import numpy as np
import networkx as nx
import pyomo.environ as pyomo
import pyomo.opt as opt
import pyomo.util.model_size as model_size

from copy import deepcopy

from .base import Node, Edge, Asset, Policy
from .buses import Region
from .assets import Producer, Load, Store
from .edges import Line
from .policies import RPS
from .exceptions import *

from ..utilities import cprint
from ..graph import remove_self_edges

default_classes = ['Region', 'Producer', 'Load', 'Store', 'Line', 'RPS']
base_classes = ['Node', 'Edge', 'Asset', 'Policy']

# Network class

class Network:

    def __init__(self, **kwargs):

        self.verbose = kwargs.get('verbose', False)
        self.steps = kwargs.get('steps', (0, 1))
        self.time_step = kwargs.get('time_step', 3600.) # [s]

        self.shortfall_capacity = kwargs.get('shortfall_capacity', None)
        self.shortfall_cost = kwargs.get('shortfall_cost', None)

        self.wastage_capacity = kwargs.get('wastage_capacity', None)
        self.wastage_cost = kwargs.get('wastage_cost', None)

        self.graph = nx.DiGraph()
        self.assets = []
        self.policies = []

    def size(self):

        return model_size.build_model_size_report(self.model)

    # def build_solution(self):

    #     nodes = []
    #     edges = []

    #     for source, node in self.graph._node.items():

    #         # for asset in node.assets:

    #         #     asset_results = asset['object'].results(self.model)
    #         #     asset = {**asset, **asset_results}

    #         node_results = node['object'].results(self.model)

    #         nodes.append((source, {**node, **node_results}))

    #         for target, edge in self.graph._adj[source].items():

    #             edge_results = edge['object'].results(self.model)

    #             edges.append((source, target, {**edge, **edge_results}))


    #     self.solution = nx.DiGraph()
    #     self.solution.add_nodes_from(nodes)
    #     self.solution.add_edges_from(edges)

    def collect_results(self):

        self.results = {}

        for source, node in self.graph._node.items():

            self.results = node['object'].results(self.model, self.results)

            edge_results = {}

            for target, edge in self.graph._adj[source].items():

                edge_results = edge['object'].results(self.model, edge_results)

            self.results[source]['edges'] = edge_results

    def solve(self, **kwargs):

        self.verbose = kwargs.get('verbose', self.verbose)
        tee = kwargs.get('tee', False)
        solver_kw = kwargs.get('solver', {'_name': 'glpk'})

        #Generating the solver object
        solver = opt.SolverFactory(**solver_kw)
        # solver = opt.SolverFactory('cplex_direct')

        self.model.dual = pyomo.Suffix(direction = pyomo.Suffix.IMPORT)

        # Building and solving as a linear problem
        t0 = time.time()
        self.result = solver.solve(self.model, tee = tee)
        cprint(f'Problem Solved: {time.time() - t0}', self.verbose)

        # Making solution dictionary
        t0 = time.time()
        self.collect_results()
        # self.build_solution()
        cprint(f'Results Collected: {time.time() - t0}', self.verbose)

    def build(self):

        self.model = pyomo.ConcreteModel()

        # Define time steps
        self.model.steps = pyomo.Set(
            initialize = list(range(self.steps[1] - self.steps[0]))
            )
        self.model.start = pyomo.Param(initialize = self.steps[0], domain = pyomo.Integers)
        self.model.stop = pyomo.Param(initialize = self.steps[1], domain = pyomo.Integers)
        self.model.time_step = pyomo.Param(initialize = self.time_step)
        # self.model.total_time = len(self.model.steps) * self.model.time_step

        # self.model.steps.pprint()

        # t0 = time.time()
        self.feasibility_parameters()
        self.assign_edge_objects()
        # cprint(f'Parameters Built: {time.time() - t0}', self.verbose)

        t0 = time.time()
        self.build_parameters()
        cprint(f'Parameters Built: {time.time() - t0}', self.verbose)

        t0 = time.time()
        self.build_variables()
        cprint(f'Variables Built: {time.time() - t0}', self.verbose)

        t0 = time.time()
        self.build_constraints()
        cprint(f'Constraints Built: {time.time() - t0}', self.verbose)

        t0 = time.time()
        self.build_objective()
        cprint(f'Objective Built: {time.time() - t0}', self.verbose)

    def feasibility_parameters(self):

        for source, node in self.graph._node.items():

            if self.shortfall_capacity is not None:

                node['object'].shortfall_capacity = self.shortfall_capacity

            if self.shortfall_cost is not None:

                node['object'].shortfall_cost = self.shortfall_cost

            if self.wastage_capacity is not None:

                node['object'].wastage_capacity = self.wastage_capacity

            if self.wastage_cost is not None:

                node['object'].wastage_cost = self.wastage_cost

    def assign_edge_objects(self):

        for source, node in self.graph._node.items():

            node['imports'] = []
            node['exports'] = []

        for source, _adj in self.graph._adj.items():

            source_node = self.graph._node[source]

            for target, edge in _adj.items():

                target_node = self.graph._node[target]

                source_node['object'].imports.append(edge)
                target_node['object'].exports.append(edge)

    def build_objective(self):

        cost = 0

        for source, node in self.graph._node.items():

            cost += node['object'].objective(self.model)

            for target, edge in self.graph._adj[source].items():

                cost += edge['object'].objective(self.model)

        for policy in self.policies:

            cost += policy['object'].objective(self.model)

        self.model.objective = pyomo.Objective(
            expr = cost, sense = pyomo.minimize
            )

    def build_constraints(self):

        for source, node in self.graph._node.items():

            self.model = node['object'].constraints(self.model)

            for target, edge in self.graph._adj[source].items():

                self.model = edge['object'].constraints(self.model)

        for policy in self.policies:

            self.model = policy['object'].constraints(self.model)

    def build_variables(self):

        for source, node in self.graph._node.items():

            self.model = node['object'].variables(self.model)

            for target, edge in self.graph._adj[source].items():

                self.model = edge['object'].variables(self.model)

        for policy in self.policies:

            self.model = policy['object'].variables(self.model)

    def build_parameters(self):

        for source, node in self.graph._node.items():

            self.model = node['object'].parameters(self.model)

            for target, edge in self.graph._adj[source].items():

                self.model = edge['object'].parameters(self.model)

        for policy in self.policies:

            self.model = policy['object'].parameters(self.model)

    def from_graph(self, graph, policies = []):

        graph = deepcopy(graph)
        policies = deepcopy(policies)

        graph = remove_self_edges(graph)

        for source, node in graph._node.items():

            _class = node.pop('_class')
            profiles = node.pop('profiles', {})

            assets = node.pop('assets', [])

            self.add(_class, source, **node)

            for asset in assets:

                _class = asset.pop('_class')

                asset['region'] = source

                if isinstance(asset.get('profile', ''), str):

                    asset['profile'] = profiles.get(asset['profile'], None)

                self.add(_class, asset['id'], **asset)

        for source, _adj in graph._adj.items():
            for target, edge in _adj.items():

                _class = edge.pop('_class')

                edge['source'] = source
                edge['target'] = target

                self.add(_class, f"{source}_{target}", **edge)

        for policy in policies:

            # print(policy)

            _class = policy.pop('_class')
            policy['assets'] = self.assets

            self.add(_class, policy['id'], **policy)

        return self

    def add(self, _class, handle, **kwargs):
        '''
        Adds and object to the network
        '''

        # Processing class
        if isinstance(_class, str):
            if _class in default_classes:

                _class = eval(_class)

            else:

                raise GOOD_ClassNotFound

        # What is the base class of the object?
        _base = _class.__base__

        if _base is Node:

            # Add a node
            self.add_node(_class, handle, **kwargs)

        elif _base is Edge:

            source = kwargs.pop('source', None)
            target = kwargs.pop('target', None)

            # Add an edge
            self.add_edge(_class, handle, source, target, **kwargs)

        elif _base is Asset:

            region = kwargs.pop('region', None)

            # Add an asset
            self.add_asset(_class, handle, region, **kwargs)

        elif _base is Policy:

            # Add an asset
            self.add_policy(_class, handle, **kwargs)

        else:

            raise GOOD_InvalidBaseClass

    def add_asset(self, _class, handle, region, **kwargs):

        kwargs['object'] = _class(handle, **kwargs)

        # Checking for node
        if region not in self.graph.nodes:

            raise GOOD_NodeNotFound(region)

        self.assets.append(kwargs)

        self.graph._node[region]['object'].assets.append(kwargs)

    def add_policy(self, _class, handle, **kwargs):

        # print('s')

        kwargs['object'] = _class(handle, **kwargs)

        # print(self.graph._node['object'])

        self.policies.append(kwargs)

    def add_node(self, _class, handle, **kwargs):

        self.graph.add_node(handle, object = _class(handle, **kwargs), **kwargs)

    def add_edge(self, _class, handle, source, target, **kwargs):

        edge_obj = _class(handle, **kwargs)

        self.graph.add_edge(source, target, object = edge_obj, **kwargs)