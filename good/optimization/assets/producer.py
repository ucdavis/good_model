from ..base.asset import Asset

import numpy as np
import pyomo.environ as pyomo
import logging

class Producer(Asset):

    def __init__(self, handle, **kwargs):

        super().__init__(handle, **kwargs)

        self.dispatchable = kwargs.get('dispatchable', True)

        # Operational parameters
        self.installed_capacity = kwargs.get('installed_capacity', 0)
        self.operating_cost = kwargs.get('operating_cost', 0)
        self.ramp_rate = kwargs.get('ramp_rate', 1)

        # Can capacity be expanded
        self.capex_capacity = kwargs.get('capex_capacity', 0)
        self.capex_cost = kwargs.get('capex_cost', 0)

        # print(self.handle, self.capex_capacity)
        self.extensible = self.capex_capacity > 0

        # Profile of instantaneous capcity factors (as per-unit values 0-1)
        self.profile = kwargs.get('profile', None)
        self.capacity_factor = kwargs.get('capacity_factor', 1)

        if self.profile is not None:

            self.profile = np.array(self.profile)

    def parameters(self, model):

        # Capacity Expansion
        if not self.extensible:

            handle = f"{self.handle}::capex"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Param(initialize = 0),
            )

        # Capacity Factor Profile
        if self.profile is None:

            handle = f"{self.handle}::profile"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Param(model.steps, initialize = self.capacity_factor),
            )

        else:

            print(self.profile)

            handle = f"{self.handle}::profile"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Param(
                    model.steps,
                    initialize = self.profile[int(model.start):int(model.stop)]),
            )

        return model

    def variables(self, model):

        handle = f"{self.handle}::production"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Var(
                model.steps,
                initialize = [0] * len(model.steps),
                within = pyomo.NonNegativeReals
                ),
            )

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

        return model

    def constraints(self, model):
        """Add capacity and renewable profile constraints"""

        production = getattr(model, f"{self.handle}::production")
        profile = getattr(model, f"{self.handle}::profile")
        capex = getattr(model, f"{self.handle}::capex")

        # Maximum capacity constraint
        setattr(
            model, f"{self.handle}::production_constraint",
            pyomo.Constraint(
                model.steps,
                rule = (
                    lambda m, t: production[t] <= (
                        self.installed_capacity * profile[t] + capex * profile[t]
                        )
                    )
                )
            )

        # Ramp rate
        def ramp_rate_rule_upper(m, t):

            if t == 0:

                rule = (0, production[t], np.inf)

            else:

                rule = (
                    production[t] - production[t - 1] <=
                    self.ramp_rate * (self.installed_capacity + capex)
                    )

            return rule

        setattr(
            model, f"{self.handle}::ramp_rate_upper_constraint",
            pyomo.Constraint(
                model.steps,
                rule = lambda m, t: ramp_rate_rule_upper(m, t),
                )
            )

        def ramp_rate_rule_lower(m, t):

            if t == 0:

                rule = (0, production[t], np.inf)

            else:

                rule = (
                    production[t] - production[t - 1] >=
                    -self.ramp_rate * (self.installed_capacity + capex)
                    )

            return rule

        setattr(
            model, f"{self.handle}::ramp_rate_lower_constraint",
            pyomo.Constraint(
                model.steps,
                rule = lambda m, t: ramp_rate_rule_lower(m, t),
                )
            )

        return model

    def energy(self, model, step = None):

        production = getattr(model, f"{self.handle}::production")

        if step is None:

            energy = pyomo.quicksum(
                production[i] * model.time_step for i in model.steps
            )

        else:

            energy = production[step] * model.time_step

        return energy

    def power(self, model, step = None):

        production = getattr(model, f"{self.handle}::production")

        if step is None:

            power = pyomo.quicksum(
                production[i] for i in model.steps
            )

        else:

            power = production[step]

        return power

    def capacity(self, model, step = None):

        capex = getattr(model, f"{self.handle}::capex")

        capacity = self.installed_capacity + capex

        return capacity

    def objective(self, model):
        """Calculate cost of production"""

        production = getattr(model, f"{self.handle}::production")
        
        production_cost = pyomo.quicksum(
            production[t] * model.time_step * self.operating_cost  for t in model.steps
        )

        capex = getattr(model, f"{self.handle}::capex")

        expansion_cost = capex * self.capex_cost

        cost = production_cost + expansion_cost
        
        return cost

    def solution(self, model):

        solution = {}

        for handle in self.handles:

            value = list(getattr(model, handle).extract_values().values())
            solution[handle.split('::')[1]] = value

        # Net Contribution
        production = list(
            getattr(model, f"{self.handle}::production").extract_values().values()
            )

        solution["net"] = production

        return solution