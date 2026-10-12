import math

import numpy as np
import xarray as xr

from ...schema import LoadParams
from ..base import Asset
from ..base.component import labels, param, profile_matrix, subset


class Load(Asset):
    '''
    Electricity demand: ``installed_capacity * profile`` MW in each step.

    A load with ``flex_capacity > 0`` can shift part of its demand in time,
    following GenX's flexible-demand formulation. In each step it may defer
    up to ``min(flex_capacity, demand)`` MW and serve up to ``flex_capacity``
    MW of earlier-deferred (or later-due) demand. An inventory tracks demand
    deferred but not yet served:

        backlog[t] = backlog[t-1] + deferred[t] - flex_efficiency * served[t]

    The backlog wraps from the last step to the first, so shifted demand is
    always paid back inside the horizon. Deferred demand must be served
    within ``flex_max_delay`` hours, and demand served early must fall due
    within ``flex_max_advance`` hours (both optional).
    '''

    Params = LoadParams

    @classmethod
    def base_demand(cls, net, objs):

        return profile_matrix(net, cls, objs) * param(cls, objs, lambda o: o.p.installed_capacity)

    @classmethod
    def build(cls, net, objs):

        m = net.model
        dim = cls.dim()
        dt = net.time_step

        demand = cls.base_demand(net, objs)
        region = labels(cls, objs, lambda o: o.node)

        net.add_fixed_injection(-demand, region)

        flexible = subset(objs, lambda o: o.p.flexible)

        if not flexible:

            return

        fidx = cls.index(flexible)
        flex_cap = param(cls, flexible, lambda o: o.p.flex_capacity)
        eta = param(cls, flexible, lambda o: o.p.flex_efficiency)

        deferred = m.add_variables(
            lower=0, upper=np.minimum(flex_cap, demand.sel({dim: fidx})), name=f"{dim}-deferred"
        )
        served = m.add_variables(
            lower=0, upper=(flex_cap / eta).broadcast_like(deferred.lower), name=f"{dim}-served"
        )
        backlog = m.add_variables(coords=[fidx, net.time], name=f"{dim}-backlog")

        change = (deferred - served * eta) * dt

        later = xr.DataArray(net.time > net.time[0], coords=[net.time])
        m.add_constraints(backlog - backlog.shift(time=1) - change == 0, name=f"{dim}-backlog_balance", mask=later)
        m.add_constraints((backlog - backlog.roll(time=1) - change).isel(time=[0]) == 0, name=f"{dim}-backlog_cyclic")

        cls._window_limits(net, flexible, served, backlog, "flex_max_delay", 1.0, "max_delay")
        cls._window_limits(net, flexible, deferred, backlog, "flex_max_advance", -1.0, "max_advance")

        net.add_injection(deferred - served, labels(cls, flexible, lambda o: o.node))

        cost = param(cls, flexible, lambda o: o.p.flex_cost)

        net.add_cost((deferred * cost).sum() * dt)

    @classmethod
    def _window_limits(cls, net, objs, flow, backlog, attribute, sign, name):
        '''
        Delay: served energy in the next k steps covers today's backlog.
        Advance: deferred energy in the next k steps covers today's advance.
        '''

        dim = cls.dim()
        limited = subset(objs, lambda o: getattr(o.p, attribute) is not None)
        steps = {o.handle: max(1, math.ceil(getattr(o.p, attribute) / net.time_step)) for o in limited}

        for k in sorted(set(steps.values())):

            group = [o for o in limited if steps[o.handle] == k]
            idx = cls.index(group)
            f = flow.sel({dim: idx})

            ahead = sum(f.roll(time=-j) for j in range(1, k + 1)) * net.time_step

            net.model.add_constraints(ahead - sign * backlog.sel({dim: idx}) >= 0, name=f"{dim}-{name}_{k}")

    @classmethod
    def demand(cls, net, handles):

        objs = [net.objects[h] for h in handles]

        return cls.base_demand(net, objs).sum(cls.dim())

    @classmethod
    def solution(cls, net, objs):

        dim = cls.dim()
        v = net.model.variables
        demand = cls.base_demand(net, objs)

        flex = f"{dim}-deferred" in v

        out = {}

        for o in objs:

            d = demand.sel({dim: o.handle}).values
            result = {"demand": d.tolist()}
            consumption = d

            if flex and o.p.flexible:

                deferred = v[f"{dim}-deferred"].solution.sel({dim: o.handle}).values
                served = v[f"{dim}-served"].solution.sel({dim: o.handle}).values
                consumption = d - deferred + served

                result["deferred"] = deferred.tolist()
                result["served"] = served.tolist()
                result["backlog"] = v[f"{dim}-backlog"].solution.sel({dim: o.handle}).values.tolist()

            result["consumption"] = consumption.tolist()
            result["net"] = (-consumption).tolist()

            out[o.handle] = result

        return out
