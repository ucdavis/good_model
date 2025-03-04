import time

import networkx as nx
import pyomo.environ as pyomo

from copy import deepcopy

from .base import Node, Edge, Asset, Policy
from .buses import Region, Jurisdiction
from .assets import Producer, Load, Store
from .edges import Line
from .policies import RPS
from .exceptions import *

from ..utilities import cprint
from ..graph import remove_self_edges

default_classes = ['Region', 'Jurisdiction', 'Producer', 'Load', 'Store', 'Line', 'RPS']
base_classes = ['Node', 'Edge', 'Asset', 'Policy']

# Network class

class Network:

    def __init__(self, **kwargs):

        self.verbose = kwargs.get('verbose', False)
        self.steps = kwargs.get('steps', 1)
        self.time_step = kwargs.get('time_step', 3600.) # [s]

        self.shortfall_capacity = kwargs.get('shortfall_capacity', None)
        self.shortfall_cost = kwargs.get('shortfall_cost', None)

        self.wastage_capacity = kwargs.get('wastage_capacity', None)
        self.wastage_cost = kwargs.get('wastage_cost', None)

        self.graph = nx.DiGraph()

    def collect_results(self):

        self.results = {}

        for source, node in self.graph._node.items():

            self.results = node['object'].results(self.model, self.results)

            for target, edge in self.graph._adj[source].items():

                self.results = edge['object'].results(self.model, self.results)

    def solve(self, **kwargs):

        self.verbose = kwargs.get('verbose', self.verbose)
        tee = kwargs.get('tee', False)
        solver_kw = kwargs.get('solver', {'_name': 'appsi_highs'})

        #Generating the solver object
        solver = pyomo.SolverFactory(**solver_kw)

        # Building and solving as a linear problem
        t0 = time.time()
        self.result = solver.solve(self.model, tee=tee, load_solutions=False)
        cprint(f'Problem Solved: {time.time() - t0}', self.verbose)

        # Check solver status
        if hasattr(self.result, 'solver'):
            status = str(self.result.solver.termination_condition)
            if status in ['infeasible', 'infeasibleOrUnbounded']:
                raise Exception(f"Problem is infeasible: {status}")
            elif status != 'optimal':
                if status == 'unknown' and self.result.solver.status == 'ok':
                    # Some solvers return unknown even when solution is valid
                    pass
                else:
                    raise Exception(f"Solver terminated with status: {status}")

        # Load solution if we got here
        self.model.solutions.load_from(self.result)
        
        # Collect results
        t0 = time.time()
        self.collect_results()
        cprint(f'Results Collected: {time.time() - t0}', self.verbose)

        return self

    def build(self):

        self.model = pyomo.ConcreteModel()

        # Define time steps
        self.model.steps = pyomo.Set(initialize = list(range(self.steps)))
        self.model.time_step = pyomo.Param(initialize = self.time_step)

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

                # print(source_node)

                target_node = self.graph._node[target]

                source_node['object'].imports.append(edge)
                target_node['object'].exports.append(edge)

    def build_objective(self):

        cost = 0

        for source, node in self.graph._node.items():

            cost += node['object'].objective(self.model)

            for target, edge in self.graph._adj[source].items():

                cost += edge['object'].objective(self.model)

        self.model.objective = pyomo.Objective(
            expr = cost, sense = pyomo.minimize
            )

    def build_constraints(self):

        for source, node in self.graph._node.items():

            self.model = node['object'].constraints(self.model)

            for target, edge in self.graph._adj[source].items():

                self.model = edge['object'].constraints(self.model)

    def build_variables(self):

        for source, node in self.graph._node.items():

            self.model = node['object'].variables(self.model)

            for target, edge in self.graph._adj[source].items():

                self.model = edge['object'].variables(self.model)

    def build_parameters(self):

        for source, node in self.graph._node.items():

            self.model = node['object'].parameters(self.model)

            for target, edge in self.graph._adj[source].items():

                self.model = edge['object'].parameters(self.model)

    def from_graph(self, graph):

        graph = deepcopy(graph)

        graph = remove_self_edges(graph)

        for source, node in graph._node.items():

            _class = node.pop('_class')
            profiles = node.pop('profiles', {})

            assets = node.pop('assets', [])
            policies = node.pop('policies', [])

            self.add(_class, source, **node)

            for asset in assets:

                _class = asset.pop('_class')

                asset['region'] = source

                # Handle profile if it's a string reference and exists
                if 'profile' in asset and isinstance(asset['profile'], str):
                    asset['profile'] = profiles.get(asset['profile'], None)

                # Use 'handle' if available, otherwise use 'id'
                if 'handle' in asset:
                    asset_id = asset['handle']
                elif 'id' in asset:
                    asset_id = asset['id']
                    asset['handle'] = asset_id  # Add handle for consistency
                else:
                    asset_id = f"{source}_{asset.get('type', 'asset')}"
                    asset['handle'] = asset_id  # Add handle for consistency

                # Remove handle from kwargs to avoid duplicate argument
                asset_handle = asset.pop('handle')
                
                self.add(_class, asset_handle, **asset)

            for policy in policies:

                _class = policy.pop('_class')

                # Use 'handle' if available, otherwise use 'id' or generate one
                if 'handle' in policy:
                    policy_id = policy['handle']
                elif 'id' in policy:
                    policy_id = policy['id']
                    policy['handle'] = policy_id  # Add handle for consistency
                else:
                    policy_id = f"{source}_policy"
                    policy['handle'] = policy_id  # Add handle for consistency
                    
                policy['jurisdiction'] = source

                # Remove handle from kwargs to avoid duplicate argument
                policy_handle = policy.pop('handle')
                
                self.add(_class, policy_handle, **policy)

        for source, _adj in graph._adj.items():
            for target, edge in _adj.items():

                _class = edge.pop('_class')

                edge['source'] = source
                edge['target'] = target

                # Use 'handle' if available, otherwise generate one
                if 'handle' in edge:
                    edge_id = edge['handle']
                else:
                    edge_id = f"{source}_{target}"
                    edge['handle'] = edge_id  # Add handle for consistency
                
                # Remove handle from kwargs to avoid duplicate argument
                edge_handle = edge.pop('handle')
                
                self.add(_class, edge_handle, **edge)

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

        # print(_base, Node, _base is Node)

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

            jurisdiction = kwargs.pop('jurisdiction', None)

            # Add an asset
            self.add_policy(_class, handle, jurisdiction, **kwargs)

        else:

            # print(_base)

            raise GOOD_InvalidBaseClass

    def add_asset(self, _class, handle, region, **kwargs):

        kwargs['object'] = _class(handle, **kwargs)

        # Checking for node
        if region not in self.graph.nodes:

            raise GOOD_NodeNotFound(region)

        self.graph._node[region]['object'].assets.append(kwargs)

        jurisdiction = kwargs.get('jurisdiction', None)

        if jurisdiction is not None:
            
            if jurisdiction in self.graph.nodes:

                self.graph._node[jurisdiction]['object'].assets.append(kwargs)

    def add_policy(self, _class, handle, jurisdiction, **kwargs):

        kwargs['object'] = _class(handle, **kwargs)

        # print(self.graph._node['object'])

        self.graph._node[jurisdiction]['object'].policies.append(kwargs)

    def add_node(self, _class, handle, **kwargs):

        self.graph.add_node(handle, object = _class(handle, **kwargs), **kwargs)

    def add_edge(self, _class, handle, source, target, **kwargs):

        edge_obj = _class(handle, **kwargs)

        self.graph.add_edge(source, target, object = edge_obj, **kwargs)