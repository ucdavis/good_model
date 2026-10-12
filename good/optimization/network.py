__all__ = ['Network']

import time
import warnings
from copy import deepcopy

import linopy
import networkx as nx
import numpy as np
import pandas as pd
import xarray as xr
from pydantic import ValidationError

from ..economics import HOURS_PER_YEAR
from ..exceptions import (
    GOOD_ClassNotFound,
    GOOD_EdgeNotFound,
    GOOD_InvalidBaseClass,
    GOOD_LegacyInput,
    GOOD_NodeNotFound,
    GOOD_SolveError,
    GOOD_ValidationError,
)
from ..graph import remove_self_edges
from ..utilities import cprint
from .base import REGISTRY, Asset, Edge, Line, Node, Policy

_LEGACY_KWARGS = {
    "amortization_period": "Capital costs are now annualized per asset (lifetime or capital_charge_rate) "
                           "and scaled by the modeled fraction of a year.",
}


class Network:
    '''
    A power system to optimize: regions (nodes) joined by links (edges), with
    assets in regions, transmission lines on links, and policies over assets.

    Units are MW, MWh, hours and $. ``steps=(start, stop)`` selects time steps
    ``start`` to ``stop - 1`` of every profile; each step lasts ``time_step``
    hours. Capacity costs are annualized and multiplied by the modeled
    fraction of a year, ``(stop - start) * time_step / 8760``.

    Regions without their own slack settings use ``shortfall_cost``
    (value of lost load, $/MWh), ``shortfall_capacity``, ``wastage_cost`` and
    ``wastage_capacity`` given here. Wind and solar are curtailed through
    their own output, so wastage only occurs when must-run output exceeds
    what the system can absorb; it is priced like unserved energy by default
    so that it stands out. Lower ``wastage_cost`` to allow free dumping.

    Typical use::

        network = Network(steps=(0, 168)).from_graph(graph, policies)
        network.build()
        network.solve()
        solution = network.solution_graph()
    '''

    def __init__(self, steps=(0, 24), time_step=1.0, discount_rate=0.07,
                 shortfall_cost=10_000.0, shortfall_capacity=np.inf,
                 wastage_cost=10_000.0, wastage_capacity=np.inf, verbose=False, **kwargs):

        for key in kwargs:

            if key in _LEGACY_KWARGS:

                raise GOOD_LegacyInput(f"'{key}' was removed in GOOD 2.0. {_LEGACY_KWARGS[key]}")

            raise TypeError(f"Network() got an unexpected keyword argument {key!r}")

        start, stop = int(steps[0]), int(steps[-1])

        if stop <= start:

            raise ValueError(f"steps must satisfy start < stop, got {steps!r}")

        self.steps = (start, stop)
        self.time_step = float(time_step)
        self.discount_rate = float(discount_rate)
        self.shortfall_cost = float(shortfall_cost)
        self.shortfall_capacity = float(shortfall_capacity)
        self.wastage_cost = float(wastage_cost)
        self.wastage_capacity = float(wastage_capacity)
        self.verbose = verbose

        self.graph = nx.DiGraph()
        self.objects = {}
        self.assets = {}
        self.lines = {}
        self.policies = {}

        self.model = None
        self._problems = None

    # ------------------------------------------------------------------ inputs

    @property
    def time(self):

        return pd.RangeIndex(self.steps[0], self.steps[1], name="time")

    @property
    def year_fraction(self):

        return len(self.time) * self.time_step / HOURS_PER_YEAR

    @property
    def regions(self):

        return pd.Index(list(self.graph.nodes), name="region")

    @property
    def asset_attributes(self):
        '''Attributes of every asset, keyed by handle, as seen by policy filters.'''

        return {
            handle: {**obj.attrs, "_class": type(obj).__name__, "node": obj.node}
            for handle, obj in self.assets.items()
        }

    def group_handles(self, handles):
        '''Group asset handles by class, keeping class order stable.'''

        grouped = {}

        for handle in handles:

            grouped.setdefault(type(self.objects[handle]), []).append(handle)

        return grouped

    def profile_window(self, obj, profile):
        '''The slice of ``profile`` covering the modeled steps.'''

        start, stop = self.steps

        if len(profile) < stop:

            raise GOOD_ValidationError([
                f"{type(obj).__name__} {obj.handle!r}: profile has {len(profile)} values but "
                f"steps run to {stop}"
            ])

        return np.asarray(profile[start:stop], dtype=float)

    def from_graph(self, graph=None, policies=None):
        '''
        Add the regions, assets, links, lines and policies described by a
        NetworkX graph and a policy dictionary. Every problem found is
        reported at once in a single ``GOOD_ValidationError``.

        Each node needs ``_class`` and may carry ``assets`` (handle to
        attribute dictionary) and ``profiles`` (key to list). An asset's
        ``profile`` may name a key in its node's ``profiles``. Each edge needs
        ``_class`` and may carry ``lines``.
        '''

        graph = remove_self_edges(deepcopy(graph if graph is not None else nx.DiGraph()))
        policies = deepcopy(policies or {})

        self._problems = []

        for source, node in graph._node.items():

            node = dict(node)
            _class = node.pop("_class", "Region")
            profiles = node.pop("profiles", {}) or {}
            assets = node.pop("assets", {}) or {}
            node.pop("id", None)

            self._try(self.add, _class, source, **node)

            for key, asset in assets.items():

                asset = dict(asset)
                asset_class = asset.pop("_class", None)
                asset["node"] = source

                reference = asset.get("profile")

                if isinstance(reference, str):

                    if reference in profiles:

                        asset["profile"] = profiles[reference]

                    elif reference == "":

                        asset["profile"] = None

                    else:

                        self._problems.append(
                            f"Asset {key!r} in {source!r}: profile {reference!r} is not in the "
                            f"node's profiles"
                        )

                        continue

                self._try(self.add, asset_class, key, **asset)

        for source, adjacency in graph._adj.items():

            for target, edge in adjacency.items():

                edge = dict(edge)
                edge_class = edge.pop("_class", "Link")
                lines = edge.pop("lines", {}) or {}
                handle = edge.pop("id", f"{source}:{target}")
                edge.pop("source", None)
                edge.pop("target", None)

                self._try(self.add, edge_class, handle, source=source, target=target, **edge)

                for key, line in lines.items():

                    line = dict(line)
                    line_class = line.pop("_class", "Transmission")
                    line.pop("source", None)
                    line.pop("target", None)
                    line["edge"] = (source, target)

                    self._try(self.add, line_class, key, **line)

        for key, policy in policies.items():

            policy = dict(policy)
            policy_class = policy.pop("_class", None)
            policy.pop("assets", None)

            self._try(self.add, policy_class, key, **policy)

        problems, self._problems = self._problems, None

        if problems:

            raise GOOD_ValidationError(problems)

        return self

    def _try(self, method, *args, **kwargs):

        try:

            method(*args, **kwargs)

        except ValidationError as error:

            name = args[1] if len(args) > 1 else "?"
            label = args[0] if isinstance(args[0], str) else getattr(args[0], "__name__", args[0])

            for detail in error.errors():

                where = ".".join(str(x) for x in detail["loc"])
                where = f" field {where!r}" if where else ""
                message = detail["msg"].removeprefix("Value error, ")

                self._problems.append(f"{label} {name!r}{where}: {message}")

        except (GOOD_ClassNotFound, GOOD_NodeNotFound, GOOD_EdgeNotFound, GOOD_InvalidBaseClass,
                GOOD_LegacyInput, ValueError) as error:

            self._problems.append(f"{args[1] if len(args) > 1 else ''}: {error}")

    def add(self, _class, handle, **kwargs):
        '''Add one component. ``_class`` is a class or the name of a registered class.'''

        if isinstance(_class, str):

            if _class not in REGISTRY:

                raise GOOD_ClassNotFound(_class, REGISTRY)

            _class = REGISTRY[_class]

        if not isinstance(_class, type):

            raise GOOD_InvalidBaseClass(_class)

        if handle in self.objects:

            raise ValueError(f"handle {handle!r} is used twice; handles must be unique")

        if issubclass(_class, Node):

            obj = _class(handle, **kwargs)
            self.graph.add_node(handle, object=obj)

        elif issubclass(_class, Edge):

            source, target = kwargs.pop("source", None), kwargs.pop("target", None)

            for node in (source, target):

                if node not in self.graph.nodes:

                    raise GOOD_NodeNotFound(node)

            obj = _class(handle, source=source, target=target, **kwargs)
            self.graph.add_edge(source, target, object=obj)

        elif issubclass(_class, Asset):

            node = kwargs.pop("node", None)

            if node not in self.graph.nodes:

                raise GOOD_NodeNotFound(node)

            obj = _class(handle, node=node, **kwargs)
            self.graph.nodes[node]["object"].assets[handle] = obj
            self.assets[handle] = obj

        elif issubclass(_class, Line):

            edge = tuple(kwargs.pop("edge", ("", "")))

            if edge not in self.graph.edges:

                raise GOOD_EdgeNotFound(edge)

            obj = _class(handle, edge=edge, **kwargs)
            self.graph.edges[edge]["object"].lines[handle] = obj
            self.lines[handle] = obj

        elif issubclass(_class, Policy):

            obj = _class(handle, **kwargs)
            self.policies[handle] = obj

        else:

            raise GOOD_InvalidBaseClass(_class)

        self.objects[handle] = obj

        return obj

    # ------------------------------------------------------------------ model

    def add_injection(self, expression, region):
        '''Add a (class, time) expression to the balance of each object's region.'''

        self._injections.append((expression, region))

    def add_fixed_injection(self, values, region):
        '''Add a constant (class, time) injection; demand is negative.'''

        self._fixed.append((values, region))

    def add_cost(self, expression):

        self._costs.append(expression)

    def add_policy_constraint(self, constraint, name):

        return self.model.add_constraints(constraint, name=name)

    def injections(self):
        '''Balance contributions summed by region, each covering every region.'''

        for expression, region in self._injections:

            region = region.rename("region")

            yield expression.groupby(region).sum().reindex(region=self.regions)

    def fixed_demand(self):
        '''Constant demand by region and step (MW), the balance right-hand side.'''

        total = xr.DataArray(
            np.zeros((len(self.regions), len(self.time))), coords=[self.regions, self.time]
        )

        for values, region in self._fixed:

            if values.size == 0:

                continue

            grouped = values.groupby(region.rename("region")).sum().reindex(region=self.regions, fill_value=0.0)

            total = total - grouped.transpose("region", "time")

        return total

    def _classes(self, objects):

        groups = {}

        for obj in objects:

            groups.setdefault(type(obj), []).append(obj)

        return groups

    def build(self):
        '''Create the linopy model: assets and lines first, then regional balances, then policies.'''

        self.model = linopy.Model(force_dim_names=True)
        self._injections, self._fixed, self._costs = [], [], []

        timings = {}

        def timed(label, groups):

            t0 = time.time()

            for cls, objs in groups.items():

                cls.build(self, objs)

            timings[label] = time.time() - t0

        timed("assets", self._classes(self.assets.values()))
        timed("lines", self._classes(self.lines.values()))

        regions = [data["object"] for _, data in self.graph.nodes(data=True)]
        timed("regions", self._classes(regions))
        timed("policies", self._classes(self.policies.values()))

        t0 = time.time()

        objective = 0.0

        for cost in self._costs:

            objective = cost + objective

        self.model.add_objective(objective)

        timings["objective"] = time.time() - t0

        for label, seconds in timings.items():

            cprint(f"Built {label}: {seconds:.2f} s", self.verbose)

        return self

    def solve(self, solver="highs", options=None, tee=False, **kwargs):
        '''
        Solve with any solver linopy supports; HiGHS is the default.

        ``options`` is a dictionary passed to the solver unchanged. For HiGHS,
        ``options={"solver": "ipm"}`` selects the interior-point method and
        ``{"time_limit": 600}`` caps run time. ``tee=True`` prints the solver log.
        Other keyword arguments are added to ``options``.
        '''

        if self.model is None:

            self.build()

        if isinstance(solver, dict):

            warnings.warn("solver={'_name': ...} is deprecated; pass solver='name'", DeprecationWarning)
            solver = solver.get("_name", "highs")

        options = {**(options or {}), **kwargs}

        if solver == "highs":

            options.setdefault("output_flag", bool(tee))

        t0 = time.time()
        status, condition = self.model.solve(solver_name=solver, **options)
        cprint(f"Solved: {time.time() - t0:.2f} s ({condition})", self.verbose)

        if status != "ok":

            raise GOOD_SolveError(f"Solver finished with status {status!r} ({condition}).")

        return self

    @property
    def objective_value(self):

        return float(self.model.objective.value)

    def size(self):
        '''Number of variables and constraints in the built model.'''

        return {"variables": int(self.model.nvars), "constraints": int(self.model.ncons)}

    # ------------------------------------------------------------------ outputs

    def _solutions(self):

        results = {}

        for group in (self.assets.values(), self.lines.values(),
                      [d["object"] for _, d in self.graph.nodes(data=True)], self.policies.values()):

            for cls, objs in self._classes(group).items():

                results.update(cls.solution(self, objs))

        return results

    def solution_graph(self):
        '''
        A graph shaped like the input: each node holds its region results and
        an ``assets`` dictionary, each edge a ``lines`` dictionary. Values are
        lists over time steps (capacities are one-element lists).
        '''

        t0 = time.time()
        results = self._solutions()
        solution = nx.DiGraph()

        for handle, data in self.graph.nodes(data=True):

            node = dict(results.get(handle, {}))
            node["assets"] = {h: results[h] for h in data["object"].assets}
            solution.add_node(handle, **node)

        for source, target, data in self.graph.edges(data=True):

            solution.add_edge(source, target, lines={h: results[h] for h in data["object"].lines})

        solution.graph["policies"] = {h: results[h] for h in self.policies}
        solution.graph["objective"] = self.objective_value
        solution.graph["steps"] = list(self.steps)
        solution.graph["time_step"] = self.time_step

        cprint(f"Solution graph built: {time.time() - t0:.2f} s", self.verbose)

        return solution

    def solution_dataframe(self, solution=None):
        '''
        Time series results in one DataFrame indexed by step. Columns are
        ``region::key``, ``region:asset::key`` and ``source:target:line::key``;
        single values (capacities) appear in the first row only.
        '''

        if solution is None:

            solution = self.solution_graph()

        columns = {}

        def collect(prefix, values):

            for key, value in values.items():

                if isinstance(value, list):

                    columns[f"{prefix}::{key}"] = value

        for handle, node in solution.nodes(data=True):

            collect(handle, node)

            for asset, values in node["assets"].items():

                collect(f"{handle}:{asset}", values)

        for source, target, edge in solution.edges(data=True):

            for line, values in edge["lines"].items():

                collect(f"{source}:{target}:{line}", values)

        n = len(self.time)

        frame = {
            key: (value + [np.nan] * (n - 1)) if len(value) == 1 else value
            for key, value in columns.items()
        }

        return pd.DataFrame(frame, index=self.time)
