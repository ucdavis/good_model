import numpy as np
import xarray as xr

from ...schema import ProducerParams
from ..base import Asset
from ..base.component import annual_cost, labels, param, profile_matrix, subset, total_energy


class Producer(Asset):
    '''
    A source of energy: thermal plants, hydro, geothermal, wind and solar.

    Output in each step is limited by availability times capacity, where
    availability is ``capacity_factor * profile``. Wind and solar are
    producers with a profile, so the model can curtail them.

    * ``dispatchable=False`` fixes output at availability (must-take or must-run).
    * ``min_output`` sets a floor as a fraction of capacity.
    * ``ramp_rate`` limits the change in output per hour.
    * ``energy_budget_window`` turns the profile into an energy budget: output
      summed over each window of that many steps may not exceed summed
      availability, while hourly output may reach full capacity (for hydro).

    Output limits are variable bounds when capacity is fixed, and constraints
    only for expandable producers.
    '''

    Params = ProducerParams

    @classmethod
    def build(cls, net, objs):

        m = net.model
        dim = cls.dim()

        cap = param(cls, objs, lambda o: o.p.installed_capacity)
        avail = profile_matrix(net, cls, objs) * param(cls, objs, lambda o: o.p.capacity_factor)

        budget = param(cls, objs, lambda o: o.p.energy_budget_window is not None, dtype=bool)
        hourly = xr.where(budget, 1.0, avail)

        floor = np.minimum(param(cls, objs, lambda o: o.p.min_output), hourly)
        must_take = param(cls, objs, lambda o: not o.p.dispatchable, dtype=bool)
        floor = xr.where(must_take, hourly, floor)

        extensible = param(cls, objs, lambda o: o.p.extensible, dtype=bool)

        upper = xr.where(extensible, np.inf, hourly * cap)
        lower = xr.where(extensible, 0.0, floor * cap)

        production = m.add_variables(lower=lower, upper=upper, name=f"{dim}-production")

        ext = subset(objs, lambda o: o.p.extensible)

        if ext:

            eidx = cls.index(ext)
            new = m.add_variables(
                lower=0, upper=param(cls, ext, lambda o: o.p.capex_capacity), name=f"{dim}-new_capacity"
            )

            p_e = production.sel({dim: eidx})
            h_e = hourly.sel({dim: eidx})
            f_e = floor.sel({dim: eidx})
            c_e = cap.sel({dim: eidx})

            m.add_constraints(p_e - h_e * new <= h_e * c_e, name=f"{dim}-max_output")
            m.add_constraints(p_e - f_e * new >= f_e * c_e, name=f"{dim}-min_output", mask=f_e > 0)

            net.add_cost((new * annual_cost(net, cls, ext)).sum() * net.year_fraction)

        cls._ramp_constraints(net, objs, production, cap)
        cls._budget_constraints(net, objs, production, avail, cap)

        net.add_injection(production, labels(cls, objs, lambda o: o.node))

        cost = param(cls, objs, lambda o: o.p.operating_cost)

        net.add_cost((production * cost).sum() * net.time_step)

    @classmethod
    def _ramp_constraints(cls, net, objs, production, cap):

        dim = cls.dim()

        # A ramp limit of a full capacity per step can never bind, so skip it.
        ramped = subset(objs, lambda o: o.p.ramp_rate is not None and o.p.ramp_rate * net.time_step < 1)

        if not ramped or len(net.time) < 2:

            return

        idx = cls.index(ramped)
        limit = param(cls, ramped, lambda o: o.p.ramp_rate * net.time_step)
        p = production.sel({dim: idx})
        change = p - p.shift(time=1)
        later = xr.DataArray(net.time > net.time[0], coords=[net.time])

        capacity = limit * cap.sel({dim: idx})
        ext = subset(ramped, lambda o: o.p.extensible)

        if ext:

            new = net.model.variables[f"{dim}-new_capacity"]
            fixed = subset(ramped, lambda o: not o.p.extensible)

            if fixed:

                fidx = cls.index(fixed)
                c = change.sel({dim: fidx})
                net.model.add_constraints(c <= capacity.sel({dim: fidx}), name=f"{dim}-ramp_up", mask=later)
                net.model.add_constraints(c >= -capacity.sel({dim: fidx}), name=f"{dim}-ramp_down", mask=later)

            eidx = cls.index(ext)
            c = change.sel({dim: eidx})
            lim = limit.sel({dim: eidx})
            n = new.sel({dim: eidx})
            net.model.add_constraints(c - lim * n <= capacity.sel({dim: eidx}), name=f"{dim}-ramp_up_ext", mask=later)
            net.model.add_constraints(c + lim * n >= -capacity.sel({dim: eidx}), name=f"{dim}-ramp_down_ext", mask=later)

        else:

            net.model.add_constraints(change <= capacity, name=f"{dim}-ramp_up", mask=later)
            net.model.add_constraints(change >= -capacity, name=f"{dim}-ramp_down", mask=later)

    @classmethod
    def _budget_constraints(cls, net, objs, production, avail, cap):

        dim = cls.dim()
        budgeted = subset(objs, lambda o: o.p.energy_budget_window is not None)

        for window in sorted({o.p.energy_budget_window for o in budgeted}):

            group = subset(budgeted, lambda o: o.p.energy_budget_window == window)
            idx = cls.index(group)

            # Windows are aligned to absolute step numbers, so a run starting
            # mid-window gets a pro-rated budget for the partial window.
            window_id = xr.DataArray(np.asarray(net.time) // window, coords=[net.time], name="window")

            used = production.sel({dim: idx}).groupby(window_id).sum()
            allowed = (avail.sel({dim: idx}) * cap.sel({dim: idx})).groupby(window_id).sum()

            net.model.add_constraints(used <= allowed, name=f"{dim}-energy_budget_{window}")

    @classmethod
    def generation(cls, net, handles):

        production = net.model.variables[f"{cls.dim()}-production"]
        total = total_energy(net, cls, "total_generation", production)

        return total.sel({cls.dim(): handles}).sum()

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
        production = net.model.variables[f"{dim}-production"].solution

        new = {}

        if f"{dim}-new_capacity" in net.model.variables:

            sol = net.model.variables[f"{dim}-new_capacity"].solution
            new = dict(zip(sol.coords[dim].values, sol.values.tolist()))

        out = {}

        for o in objs:

            p = production.sel({dim: o.handle}).values.tolist()

            out[o.handle] = {
                "production": p,
                "new_capacity": [new.get(o.handle, 0.0)],
                "net": p,
            }

        return out
