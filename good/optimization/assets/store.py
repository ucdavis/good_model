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
        self.production_rate = kwargs.get('production_rate', 1)
        self.consumption_rate = kwargs.get('consumption_rate', 1)
        self.initial = kwargs.get('initial', 0)

        # Can capacity be expanded
        self.capex_capacity = kwargs.get('capex_capacity', 0)
        self.capex_cost = kwargs.get('capex_cost', 0)
        self.extensible = self.capex_capacity > 0

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

                rule = (self.initial, level[t], self.initial)

            else:

                rule = level[t] == (
                    level[t - 1] +
                    consumption[t] * model.time_step -
                    production[t] * model.time_step
                    )
                    
            return rule

        setattr(
            model, f"{self.handle}::level_constraint",
            pyomo.Constraint(
                model.steps,
                rule = lambda m, t: level_rule(m, t),
                )
            )

        setattr(
            model, f"{self.handle}::level_initial_constraint",
            pyomo.Constraint(
                rule = level[model.steps.at(1)] == self.initial
                )
            )

        setattr(
            model, f"{self.handle}::level_final_constraint",
            pyomo.Constraint(
                rule = level[model.steps.at(-1)] == self.initial
                )
            )

        setattr(
            model, f"{self.handle}::production_intial_constraint",
            pyomo.Constraint(
                rule = production[model.steps.at(1)] == 0
                )
            )

        setattr(
            model, f"{self.handle}::consumption_intial_constraint",
            pyomo.Constraint(
                rule = consumption[model.steps.at(1)] == 0
                )
            )

        setattr(
            model, f"{self.handle}::production_constraint",
            pyomo.Constraint(
                model.steps,
                rule = (
                    lambda m, t: (
                        (self.installed_capacity + capex) * self.production_rate
                         - production[t] >= 0
                         )
                    )
                )
            )

        setattr(
            model, f"{self.handle}::consumption_constraint",
            pyomo.Constraint(
                model.steps,
                rule = (
                    lambda m, t: (
                        (self.installed_capacity + capex) * self.consumption_rate
                         - consumption[t] >= 0
                         )
                    )
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

        return model

    def objective(self, model):

        production = getattr(model, f"{self.handle}::production")
        
        production_cost = pyomo.quicksum(
            production[t] * model.time_step * self.operating_cost  for t in model.steps
        )

        capex = getattr(model, f"{self.handle}::capex")

        expansion_cost = capex * self.capex_cost * model.amortization

        cost = production_cost + expansion_cost
        
        return cost

    def energy(self, model, step = None):

        production = getattr(model, f"{self.handle}::production")
        consumption = getattr(model, f"{self.handle}::consumption")
        efficiency = self.efficiency

        if step is None:

            energy = pyomo.quicksum(
                production[i] * efficiency * model.time_step -
                consumption[i] / efficiency * model.time_step
                for i in model.steps
            )

        else:

            energy = (
                production[step] * efficiency * model.time_step -
                consumption[step] / efficiency * model.time_step
                )

        return energy

    def power(self, model, step = None):

        production = getattr(model, f"{self.handle}::production")
        consumption = getattr(model, f"{self.handle}::consumption")
        efficiency = self.efficiency

        if step is None:

            power = pyomo.quicksum(
                production[i] * efficiency -
                consumption[i] / efficiency
                for i in model.steps
            )

        else:

            power = (
                production[step] * efficiency -
                consumption[step] / efficiency
                )

        return power

    def capacity(self, model, step = None):

        capex = getattr(model, f"{self.handle}::capex")

        capacity = self.installed_capacity + capex

        return capacity

    def solution(self, model):

        solution = {}

        for handle in self.handles:

            value = list(getattr(model, handle).extract_values().values())
            solution[handle.split('::')[1]] = value

        # Net Contribution
        production = list(
            getattr(model, f"{self.handle}::production").extract_values().values()
            )

        consumption = list(
            getattr(model, f"{self.handle}::consumption").extract_values().values()
            )

        efficiency = self.efficiency

        solution["net"] = (
            [production[i] * efficiency - consumption[i] / efficiency \
            for i in model.steps]
            )

        return solution