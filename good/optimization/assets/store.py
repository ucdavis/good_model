import numpy as np
import xarray as xr

from ...schema import StoreParams
from ..base import Asset
from ..base.component import annual_cost, labels, param, subset, total_energy


class Store(Asset):
    '''
    Energy storage such as batteries and pumped hydro.

    Power capacity (MW) limits charging and discharging; energy capacity (MWh)
    limits the state of charge. Energy capacity is ``installed_energy`` when
    given, otherwise ``installed_capacity * duration``. New builds add power
    and energy together at the store's ``duration`` and pay
    ``capex_cost + duration * energy_capex_cost`` per MW.

    State of charge follows

        soc[t] = soc[t-1] + (charge_efficiency * charge[t] - discharge[t] / discharge_efficiency) * dt

    and wraps from the last step to the first when ``cyclic`` (the default),
    so a short window neither starts empty nor gets free energy.
    '''

    Params = StoreParams

    @classmethod
    def build(cls, net, objs):

        m = net.model
        dim = cls.dim()
        dt = net.time_step

        power = param(cls, objs, lambda o: o.p.installed_capacity)
        energy = param(cls, objs, lambda o: o.p.energy_capacity)
        extensible = param(cls, objs, lambda o: o.p.extensible, dtype=bool)

        coords = [cls.index(objs), net.time]
        shape = (len(objs), len(net.time))

        def upper(values):

            return xr.DataArray(
                np.broadcast_to(xr.where(extensible, np.inf, values).values[:, None], shape).copy(),
                coords=coords,
            )

        charge = m.add_variables(lower=0, upper=upper(power), name=f"{dim}-charge")
        discharge = m.add_variables(lower=0, upper=upper(power), name=f"{dim}-discharge")
        soc = m.add_variables(lower=0, upper=upper(energy), name=f"{dim}-soc")

        ext = subset(objs, lambda o: o.p.extensible)
        new = None

        if ext:

            eidx = cls.index(ext)
            new = m.add_variables(
                lower=0, upper=param(cls, ext, lambda o: o.p.capex_capacity), name=f"{dim}-new_capacity"
            )
            duration = param(cls, ext, lambda o: o.p.duration)

            m.add_constraints(charge.sel({dim: eidx}) - new <= power.sel({dim: eidx}), name=f"{dim}-max_charge")
            m.add_constraints(discharge.sel({dim: eidx}) - new <= power.sel({dim: eidx}), name=f"{dim}-max_discharge")
            m.add_constraints(soc.sel({dim: eidx}) - duration * new <= energy.sel({dim: eidx}), name=f"{dim}-max_soc")

            unit_cost = annual_cost(net, cls, ext, capex=lambda o: o.p.capex_cost + o.p.duration * o.p.energy_capex_cost)

            net.add_cost((new * unit_cost).sum() * net.year_fraction)

        eta_c = param(cls, objs, lambda o: o.p.charge_efficiency)
        eta_d = param(cls, objs, lambda o: o.p.discharge_efficiency)

        flow = (charge * eta_c - discharge / eta_d) * dt

        later = xr.DataArray(net.time > net.time[0], coords=[net.time])
        m.add_constraints(soc - soc.shift(time=1) - flow == 0, name=f"{dim}-soc_balance", mask=later)

        cyclic = subset(objs, lambda o: o.p.cyclic)

        if cyclic:

            cidx = cls.index(cyclic)
            s = soc.sel({dim: cidx})
            first = (s - s.roll(time=1) - flow.sel({dim: cidx})).isel(time=[0])
            m.add_constraints(first == 0, name=f"{dim}-soc_cyclic")

        acyclic = subset(objs, lambda o: not o.p.cyclic)

        if acyclic:

            aidx = cls.index(acyclic)
            start = param(cls, acyclic, lambda o: o.p.initial_soc)
            lhs = (soc.sel({dim: aidx}) - flow.sel({dim: aidx})).isel(time=[0])
            rhs = start * energy.sel({dim: aidx})

            grown = subset(acyclic, lambda o: o.p.extensible)

            if grown:

                gidx = cls.index(grown)
                lhs_g = lhs.sel({dim: gidx}) - (start.sel({dim: gidx}) * param(cls, grown, lambda o: o.p.duration)) * new.sel({dim: gidx})
                m.add_constraints(lhs_g == rhs.sel({dim: gidx}), name=f"{dim}-soc_initial_ext")

                fixed = subset(acyclic, lambda o: not o.p.extensible)

                if fixed:

                    fidx = cls.index(fixed)
                    m.add_constraints(lhs.sel({dim: fidx}) == rhs.sel({dim: fidx}), name=f"{dim}-soc_initial")

            else:

                m.add_constraints(lhs == rhs, name=f"{dim}-soc_initial")

        net.add_injection(discharge - charge, labels(cls, objs, lambda o: o.node))

        cost = param(cls, objs, lambda o: o.p.operating_cost)

        net.add_cost((discharge * cost).sum() * dt)

    @classmethod
    def generation(cls, net, handles):

        dim = cls.dim()
        net_output = net.model.variables[f"{dim}-discharge"] - net.model.variables[f"{dim}-charge"]
        total = total_energy(net, cls, "total_net_output", net_output)

        return total.sel({dim: handles}).sum()

    @classmethod
    def capacity(cls, net, handles, weight=lambda o: 1.0):

        objs = [net.objects[h] for h in handles]
        total = sum(o.p.installed_capacity * weight(o) for o in objs)

        ext = subset(objs, lambda o: o.p.extensible)

        if ext:

            new = net.model.variables[f"{cls.dim()}-new_capacity"].sel({cls.dim(): cls.index(ext)})
            total = (new * param(cls, ext, weight)).sum() + total

        return total

    @classmethod
    def solution(cls, net, objs):

        dim = cls.dim()
        v = net.model.variables
        charge = v[f"{dim}-charge"].solution
        discharge = v[f"{dim}-discharge"].solution
        soc = v[f"{dim}-soc"].solution

        new = {}

        if f"{dim}-new_capacity" in v:

            sol = v[f"{dim}-new_capacity"].solution
            new = dict(zip(sol.coords[dim].values, sol.values.tolist()))

        out = {}

        for o in objs:

            c = charge.sel({dim: o.handle}).values
            d = discharge.sel({dim: o.handle}).values

            out[o.handle] = {
                "charge": c.tolist(),
                "discharge": d.tolist(),
                "soc": soc.sel({dim: o.handle}).values.tolist(),
                "new_capacity": [new.get(o.handle, 0.0)],
                "new_energy": [new.get(o.handle, 0.0) * (o.p.duration or 0.0)],
                "net": (d - c).tolist(),
            }

        return out
