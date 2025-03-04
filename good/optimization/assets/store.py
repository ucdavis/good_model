from ..base.asset import Asset
import pyomo.environ as pyomo

import numpy as np

class Store(Asset):

    def __init__(self, handle, **kwargs):

        super().__init__(handle, **kwargs)

        # Operational parameters
        self.installed_capacity = kwargs.get('installed_capacity', 0)
        self.operating_cost = kwargs.get('operating_cost', 0)
        self.efficiency = kwargs.get('efficiency', 1)
        self.ramp_rate = kwargs.get('ramp_rate', 1)
        self.initial = kwargs.get('initial', 0)

        # Can capacity be expanded
        self.capex_capacity = kwargs.get('capex_capacity', 0)
        self.capex_cost = kwargs.get('capex_cost', 0)
        self.extensible = self.capex_capacity > 0

        # print(self.handle, self.capex_capacity, self.extensible)

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
                    lambda m, t: self.installed_capacity + capex - level[t] >= 0
                    )
                )
            )

        # Ramp rate
        def ramp_rate_rule_upper(m, t):

            if t == 0:

                rule = (0, level[t], np.inf)

            else:

                rule = (
                    level[t] - level[t - 1] <=
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

                rule = (0, level[t], np.inf)

            else:

                rule = (
                    level[t] - level[t - 1] >=
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

    def objective(self, model):

        production = getattr(model, f"{self.handle}::production")
        
        production_cost = pyomo.quicksum(
            production[t] * model.time_step * self.operating_cost  for t in model.steps
        )

        capex = getattr(model, f"{self.handle}::capex")

        expansion_cost = capex * self.capex_cost

        cost = production_cost + expansion_cost
        
        return cost

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

    def results(self, model, results):

        local_results = {}

        for handle in self.handles:

            value = list(getattr(model, handle).extract_values().values())
            local_results[handle.split('::')[1]] = value

        # Net Contribution
        production = list(
            getattr(model, f"{self.handle}::production").extract_values().values()
            )

        consumption = list(
            getattr(model, f"{self.handle}::consumption").extract_values().values()
            )

        efficiency = self.efficiency

        local_results["net"] = (
            [production[i] * efficiency - consumption[i] / efficiency \
            for i in model.steps]
            )

        results[self.handle] = local_results

        return results