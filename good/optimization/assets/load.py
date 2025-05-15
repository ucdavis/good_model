import numpy as np

from ..base.asset import Asset
import pyomo.environ as pyomo

class Load(Asset):

    def __init__(self, handle, **kwargs):
        '''
        A Load is a grid asset which adds or subtracts energy based on a profile
        and do not receive a dispacth signal from the grid. This includes end user loads
        and certaint types of renewables.
        '''

        super().__init__(handle, **kwargs)
        
        self.installed_capacity = kwargs.get('installed_capacity', 0)
        self.operating_cost = kwargs.get('operating_cost', 0)

        # print(self.handle, self.installed_capacity / 1e6)

        # Can capacity be expanded
        self.capex_capacity = kwargs.get('capex_capacity', 0)
        self.capex_cost = kwargs.get('capex_cost', 0)
        self.extensible = self.capex_capacity > 0

        self.shift_portion = kwargs.get('shift_portion', 0)
        self.shiftable = self.shift_portion > 0

        self.shift_window = kwargs.get('shift_window', None)

        self.profile = kwargs.get('profile', None)

        if self.profile is not None:

            self.profile = np.array(self.profile)

    def parameters(self, model):

        if self.shift_window is None:

            self.shift_window = len(model.steps)

        if self.profile is None:

            self.profile = [0] * len(model.steps)

        handle = f"{self.handle}::profile"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Param(model.steps,
                initialize = self.profile[int(model.start):int(model.stop)]
                )
            )

        # Capacity Expansion
        if not self.extensible:

            handle = f"{self.handle}::capex"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Param(initialize = 0),
            )

        if not self.shiftable:

            handle = f"{self.handle}::shift"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Param(
                    model.steps, initialize = [0] * len(model.steps)
                    )
                )

        return model

    def variables(self, model):

        # Capacity Expansion
        if self.extensible:

            handle = f"{self.handle}::capex"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Var(
                    initialize = 0,
                    bounds = (0, self.capex_capacity), within = pyomo.NonNegativeReals,
                    ),
                )

        if self.shiftable:

            handle = f"{self.handle}::shift"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Var(
                    model.steps,
                    initialize = [0] * len(model.steps), 
                    within = pyomo.Reals
                    ),
                )

        return model

    def constraints(self, model):

        if self.shiftable:

            profile = getattr(model, f"{self.handle}::profile")
            shift = getattr(model, f"{self.handle}::shift")

            def shift_portion_rule(m, t):

                rule = (
                    -self.shift_portion * profile[t],
                    shift[t],
                    self.shift_portion * profile[t],
                    )

                return rule

            setattr(
                model, f"{self.handle}::shift_portion_constraint",
                pyomo.Constraint(
                    model.steps,
                    rule = lambda m, t: shift_portion_rule(m, t),
                    )
                )

            for start in np.arange(
                model.steps.at(1), model.steps.at(-1), self.shift_window
                ):

                # print(start)
                finish = min([start + self.shift_window, model.steps.at(-1)])

                indices = np.arange(start, finish, 1)

                shift_sum = pyomo.quicksum(shift[t] for t in indices)

                setattr(
                    model, f"{self.handle}::shift_sum_constraint_{start}",
                    pyomo.Constraint(expr = (0, shift_sum, 0)),
                    )

        return model

    def energy(self, model, step = None):

        profile = getattr(model, f"{self.handle}::profile")
        shift = getattr(model, f"{self.handle}::shift")
        capex = getattr(model, f"{self.handle}::capex")

        capacity = self.installed_capacity + capex
        
        if step is None:

            energy = pyomo.quicksum(
                (profile[t] + shift[t]) * model.time_step * capacity for t in model.steps
                )

        else:

            energy = (profile[step] + shift[step]) * model.time_step * capacity

        return energy

    def power(self, model, step = None):

        profile = getattr(model, f"{self.handle}::profile")
        shift = getattr(model, f"{self.handle}::shift")
        capex = getattr(model, f"{self.handle}::capex")

        capacity = self.installed_capacity + capex
        
        if step is None:

            power = pyomo.quicksum(
                (profile[t] + shift[t]) * capacity for t in model.steps
                )

        else:

            power = (profile[step] + shift[step]) * capacity

        return power

    def capacity(self, model, step = None):

        capex = getattr(model, f"{self.handle}::capex")

        capacity = self.installed_capacity + capex

        return capacity

    def objective(self, model):

        profile = getattr(model, f"{self.handle}::profile")
        shift = getattr(model, f"{self.handle}::shift")
        capex = getattr(model, f"{self.handle}::capex")

        capacity = self.installed_capacity + capex
        
        shift_cost = pyomo.quicksum(
            shift[t] * model.time_step * capacity * self.operating_cost \
            for t in model.steps
            )

        expansion_cost = capex * self.capex_cost * model.amortization

        cost = shift_cost + expansion_cost

        return cost

    def solution(self, model):

        solution = {}

        for handle in self.handles:

            value = list(getattr(model, handle).extract_values().values())
            solution[handle.split('::')[1]] = value

        # Net Contribution
        profile = list(
            getattr(model, f"{self.handle}::profile").extract_values().values()
            )
        shift = list(getattr(model, f"{self.handle}::shift").extract_values().values())
        capex = list(getattr(model, f"{self.handle}::capex").extract_values().values())

        capacity = self.installed_capacity + capex[0]

        solution["net"] = (
            [(profile[i] + shift[i]) * capacity for i in model.steps]
            )

        return solution