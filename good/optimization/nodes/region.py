import numpy as np
import pandas as pd
import xarray as xr

from ...schema import RegionParams
from ..base import Node


class Region(Node):
    '''
    A balancing region. In every step, energy injected by the region's assets
    and imported over lines must equal energy consumed and exported:

        sum(injections) + shortfall - wastage = demand

    ``shortfall`` is unserved energy priced at ``shortfall_cost`` (value of
    lost load) and ``wastage`` is surplus that cannot be used or curtailed,
    priced at ``wastage_cost``. Both are bounded by their ``*_capacity``.
    Unset values take the Network's defaults.

    The dual of the balance constraint, divided by the step length, is the
    region's clearing price in $/MWh.
    '''

    Params = RegionParams

    def setting(self, net, name):

        value = getattr(self.p, name)

        return getattr(net, name) if value is None else value

    @classmethod
    def build(cls, net, objs):

        m = net.model
        index = net.regions

        def region_param(name):

            by_handle = {o.handle: o.setting(net, name) for o in objs}

            return xr.DataArray([float(by_handle[r]) for r in index], coords=[index])

        shape = (len(index), len(net.time))

        def grid(values):

            return xr.DataArray(np.broadcast_to(values.values[:, None], shape).copy(), coords=[index, net.time])

        shortfall = m.add_variables(lower=0, upper=grid(region_param("shortfall_capacity")), name="Region-shortfall")
        wastage = m.add_variables(lower=0, upper=grid(region_param("wastage_capacity")), name="Region-wastage")

        lhs = shortfall - wastage

        for expression in net.injections():

            lhs = lhs + expression

        m.add_constraints(lhs == net.fixed_demand(), name="Region-balance")

        dt = net.time_step

        net.add_cost((shortfall * region_param("shortfall_cost")).sum() * dt)
        net.add_cost((wastage * region_param("wastage_cost")).sum() * dt)

    @classmethod
    def solution(cls, net, objs):

        v = net.model.variables
        shortfall = v["Region-shortfall"].solution
        wastage = v["Region-wastage"].solution

        dual = net.model.constraints["Region-balance"].dual
        price = dual / net.time_step if dual is not None else None

        out = {}

        for o in objs:

            result = {
                "shortfall": shortfall.sel(region=o.handle).values.tolist(),
                "wastage": wastage.sel(region=o.handle).values.tolist(),
            }

            if price is not None:

                result["clearing_price"] = price.sel(region=o.handle).values.tolist()

            out[o.handle] = result

        return out
