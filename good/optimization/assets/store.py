from ..base.asset import Asset
import pyomo.environ as pyomo

import numpy as np

class Store(Asset):

    def __init__(self, handle, **kwargs):

        super().__init__(handle, **kwargs)

        # Operational parameters
        self.installed_capacity = kwargs.get('installed_capacity', 0)
        self.efficiency = kwargs.get('efficiency', 1)
        self.ramp_rate = kwargs.get('ramp_rate', 1)
        self.initial = kwargs.get('initial', 0)

        # Can capacity be expanded
        self.capex_limit = kwargs.get('capex_limit', 0)
        self.capex_cost = kwargs.get('capex_cost', 0)
        self.extensible = self.capex_limit > 0

    def parameters(self, model):

        # Capacity Expansion
        if not self.extensible:

            handle = f"{self.handle}::capex"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Param(initialize = 0),
            )

        return model

    def variables(self, model):

        # Production - energy to grid (discharging)
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

        # Consumption - energy from gid (charging)
        handle = f"{self.handle}::consumption"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Var(
                model.steps,
                initialize = [0] * len(model.steps),
                within = pyomo.NonNegativeReals
                ),
            )
        # Level
        handle = f"{self.handle}::level"
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

        production = getattr(model, f"{self.handle}::production")
        consumption = getattr(model, f"{self.handle}::consumption")
        level = getattr(model, f"{self.handle}::level")
        capex = getattr(model, f"{self.handle}::capex")

        # Setting the level
        def level_rule(m, t):

            if t == 0:

                # rule = (self.initial, level[t], self.initial)
                rule = level[t] + consumption[t] - production[t] == self.initial

            else:

                rule = level[t] == level[t - 1] + consumption[t] - production[t]
                    
            return rule

        setattr(
            model, f"{self.handle}::level_constraint",
            pyomo.Constraint(
                model.steps,
                rule = lambda m, t: level_rule(m, t),
                )
            )

        # Max and min level
        setattr(
            model, f"{self.handle}::storage_constraint",
            pyomo.Constraint(
                model.steps,
                rule = (
                    lambda m, t: (0, level[t], self.installed_capacity)
                    )
                )
            )

        # Ramp rate
        def ramp_rate_rule(m, t):

            if t == 0:

                rule = (0, level[t], np.inf)

            else:

                rule = (
                    -self.ramp_rate * (self.installed_capacity + capex),
                    level[t] - level[t - 1],
                    self.ramp_rate * (self.installed_capacity + capex)
                    )

            return rule

        setattr(
            model, f"{self.handle}::ramp_rate_constraint",
            pyomo.Constraint(
                model.steps,
                rule = lambda m, t: ramp_rate_rule(m, t),
                )
            )

        return model

    def energy(self, model, step = None):

        production = getattr(model, f"{self.handle}::production")
        consumption = getattr(model, f"{self.handle}::consumption")
        efficiency = self.efficiency

        if step is None:

            energy = pyomo.quicksum(
                production[i] * efficiency - consumption[i] / efficiency
                for i in model.steps
            )

        else:

            energy = production[step] * efficiency - consumption[step] / efficiency

        return energy

    def capacity(self, model, step = None):

        capex = getattr(model, f"{self.handle}::capex")

        capacity = self.installed_capacity + capex

        return capacity