"""Base class, registry and array helpers shared by all components.

A component class validates its inputs when an instance is created and adds
its variables and constraints to the model for *all* of its instances at once
(``build`` is a class method). Building by class keeps the model vectorized:
one linopy variable per class and quantity instead of one per asset and hour.
"""

import numpy as np
import pandas as pd
import xarray as xr

from ...economics import annualized_cost

REGISTRY = {}
"""Maps class name to class for every component class defined so far."""


class Component:
    """Something that can be added to a Network.

    Subclasses set ``Params`` to a pydantic model from :mod:`good.schema`.
    Validated inputs are available as ``self.p``; every keyword argument,
    including free-form ones such as ``fuel``, is kept in ``self.attrs``.
    """

    Params = None

    def __init_subclass__(cls, **kwargs):

        super().__init_subclass__(**kwargs)

        REGISTRY[cls.__name__] = cls

    def __init__(self, handle, **kwargs):

        self.handle = handle
        self.attrs = dict(kwargs)
        self.p = self.Params.model_validate(kwargs) if self.Params is not None else None

    def __repr__(self):

        return f"{type(self).__name__}({self.handle!r})"

    @classmethod
    def dim(cls):
        """Name of the model dimension that indexes instances of this class."""

        return cls.__name__

    @classmethod
    def index(cls, objs):

        return pd.Index([o.handle for o in objs], name=cls.dim())

    @classmethod
    def build(cls, net, objs):
        """Add variables, constraints and costs for all ``objs`` to ``net.model``."""

    @classmethod
    def solution(cls, net, objs):
        """Map each handle to a dictionary of result lists."""

        return {o.handle: {} for o in objs}


def param(cls, objs, getter, dtype=float):
    """DataArray over the class dimension built from one value per object."""

    values = [getter(o) for o in objs]

    return xr.DataArray(np.asarray(values, dtype=dtype), coords=[cls.index(objs)])


def labels(cls, objs, getter):
    """String labels over the class dimension (for grouping)."""

    return xr.DataArray(np.asarray([getter(o) for o in objs], dtype=object), coords=[cls.index(objs)])


def profile_matrix(net, cls, objs, getter=lambda o: o.p.profile, default=1.0):
    """(instance, time) DataArray of per-step profiles, one row per object."""

    rows = []

    for o in objs:

        profile = getter(o)

        if profile is None:

            rows.append(np.full(len(net.time), default))

        else:

            rows.append(net.profile_window(o, profile))

    data = np.vstack(rows) if rows else np.zeros((0, len(net.time)))

    return xr.DataArray(data, coords=[cls.index(objs), net.time])


def annual_cost(net, cls, objs, capex=lambda o: o.p.capex_cost):
    """Annualized cost of new capacity per unit ($/unit-yr), one value per object."""

    def one(o):

        p = o.p

        return annualized_cost(
            capex(o),
            fom_cost=p.fom_cost,
            lifetime=p.lifetime,
            discount_rate=p.discount_rate if p.discount_rate is not None else net.discount_rate,
            capital_charge_rate=p.capital_charge_rate,
        )

    return param(cls, objs, one)


def total_energy(net, cls, name, per_step):
    '''
    Per-instance total energy over the horizon (MWh), as one variable per
    instance tied to its hourly values by one constraint each.

    Policies sum these totals instead of every hourly value. A policy row
    over all hours of hundreds of assets has hundreds of thousands of
    nonzeros and slows simplex and interior-point solvers by an order of
    magnitude; these auxiliary variables keep every row sparse. Created once
    per class and reused by every policy.
    '''

    key = f"{cls.dim()}-{name}"

    if key not in net.model.variables:

        total = net.model.add_variables(coords=[per_step.indexes[cls.dim()]], name=key)
        net.model.add_constraints(total - (per_step * net.time_step).sum("time") == 0, name=key)

    return net.model.variables[key]


def subset(objs, predicate):

    return [o for o in objs if predicate(o)]


def empty_like_sum():
    """A zero that adds cleanly to scalar linopy expressions."""

    return 0.0
