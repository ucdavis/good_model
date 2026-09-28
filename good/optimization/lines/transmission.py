import numpy as np
import pandas as pd
import xarray as xr

from ...exceptions import GOOD_ValidationError
from ...schema import TransmissionParams
from ..base import Line
from ..base.component import annual_cost, labels, param, subset


class Transmission(Line):
    '''
    A directed transfer path from the edge's source region to its target.

    ``flow`` (MW) leaves the source and ``efficiency * flow`` arrives at the
    target. Opposite directions are separate lines so their limits can
    differ. Lines that name the same ``corridor`` share one expansion
    decision: new capacity raises both directions and is paid for once.
    Wheeling costs (``operating_cost``) are charged once per MWh sent.
    '''

    Params = TransmissionParams

    @classmethod
    def corridor_of(cls, obj):

        return obj.p.corridor if obj.p.corridor is not None else obj.handle

    @classmethod
    def build(cls, net, objs):

        m = net.model
        dim = cls.dim()

        cap = param(cls, objs, lambda o: o.p.installed_capacity)
        extensible = param(cls, objs, lambda o: o.p.extensible, dtype=bool)
        upper = xr.where(extensible, np.inf, cap).broadcast_like(
            xr.DataArray(np.zeros(len(net.time)), coords=[net.time])
        ).transpose(dim, "time")

        flow = m.add_variables(lower=0, upper=upper, name=f"{dim}-flow")

        ext = subset(objs, lambda o: o.p.extensible)

        if ext:

            corridors = {}

            for o in ext:

                corridors.setdefault(cls.corridor_of(o), []).append(o)

            cls._check_corridors(corridors)

            cdim = f"{dim}_corridor"
            cidx = pd.Index(list(corridors), name=cdim)
            first = [members[0] for members in corridors.values()]

            new = m.add_variables(
                lower=0,
                upper=xr.DataArray([o.p.capex_capacity for o in first], coords=[cidx]),
                name=f"{dim}-new_capacity",
            )

            eidx = cls.index(ext)
            corridor_of_line = xr.DataArray([cls.corridor_of(o) for o in ext], coords=[eidx])
            new_by_line = new.sel({cdim: corridor_of_line})

            m.add_constraints(flow.sel({dim: eidx}) - new_by_line <= cap.sel({dim: eidx}), name=f"{dim}-max_flow")

            unit_cost = xr.DataArray(annual_cost(net, cls, first).values, coords=[cidx])

            net.add_cost((new * unit_cost).sum() * net.year_fraction)

        efficiency = param(cls, objs, lambda o: o.p.efficiency)

        net.add_injection(-flow, labels(cls, objs, lambda o: o.source))
        net.add_injection(flow * efficiency, labels(cls, objs, lambda o: o.target))

        cost = param(cls, objs, lambda o: o.p.operating_cost)

        net.add_cost((flow * cost).sum() * net.time_step)

    @staticmethod
    def _check_corridors(corridors):

        problems = []

        for name, members in corridors.items():

            keys = ("capex_capacity", "capex_cost", "fom_cost", "lifetime", "capital_charge_rate", "discount_rate")
            reference = [getattr(members[0].p, k) for k in keys]

            for o in members[1:]:

                if [getattr(o.p, k) for k in keys] != reference:

                    problems.append(
                        f"Transmission {o.handle!r}: expansion inputs differ from {members[0].handle!r} "
                        f"in corridor {name!r}; lines in one corridor must share them"
                    )

        if problems:

            raise GOOD_ValidationError(problems)

    @classmethod
    def solution(cls, net, objs):

        dim = cls.dim()
        flow = net.model.variables[f"{dim}-flow"].solution

        new = {}

        if f"{dim}-new_capacity" in net.model.variables:

            sol = net.model.variables[f"{dim}-new_capacity"].solution
            new = dict(zip(sol.coords[f"{dim}_corridor"].values, sol.values.tolist()))

        out = {}

        for o in objs:

            f = flow.sel({dim: o.handle}).values

            out[o.handle] = {
                "flow": f.tolist(),
                "received": (f * o.p.efficiency).tolist(),
                "new_capacity": [new.get(cls.corridor_of(o), 0.0) if o.p.extensible else 0.0],
            }

        return out
