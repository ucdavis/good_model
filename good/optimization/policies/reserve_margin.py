from ..base.policy import Policy

import numpy as np
import pyomo.environ as pyomo
import logging

class Reserve_Margin(Policy):

    def __init__(self, handle, **kwargs):

        super().__init__(handle, **kwargs)

        # Terms of the policy
        self.margin = 1 + kwargs.get('margin', 0)
        self.sign = kwargs.get('sign', 1)

        self.non_compliance_capacity = kwargs.get('non_compliance_capacity', 0)
        self.non_compliance_cost = kwargs.get('non_compliance_cost', 1)

        # Criteria for assigning assets to sets
        demand_criteria = kwargs.get('demand_criteria', {})
        supply_criteria = kwargs.get('supply_criteria', {})

        # Truning srings into functions if needed
        self.demand_criteria = self.interpret(demand_criteria)
        self.supply_criteria = self.interpret(supply_criteria)

        # Building the incuded and excluded sets
        self.assets = kwargs.get('assets', [])
        self.demand = self.build_set(self.assets, self.demand_criteria)
        self.supply = self.build_set(self.assets, self.supply_criteria)

    def build_set(self, assets, criteria):

        included = {}

        for key, asset in assets.items():

            include = True

            for fun in criteria.values():

                include *= fun(asset)

            if include:

                included[key] = asset

        return included

    def interpret(self, criteria):

        interpreted_criteria = {}

        for key, fun in criteria.items():
            if isinstance(fun, str):

                fun = eval(fun)
            
            interpreted_criteria[key] = fun

        return interpreted_criteria

    def parameters(self, model):

        handle = f"{self.handle}::margin"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Param(initialize = self.margin, mutable = True),
        )

        handle = f"{self.handle}::sign"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Param(initialize = self.sign, mutable = True),
        )

        return model

    def variables(self, model):

        # Shortfall - avoids infeasibility due to insufficient supply from included set
        handle = f"{self.handle}::non_compliance"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Var(
                initialize = 0,
                bounds = (0, self.non_compliance_capacity),
                ),
            )

        return model

    def constraints(self, model):

        margin = getattr(model, f"{self.handle}::margin")
        sign = getattr(model, f"{self.handle}::sign")

        supply_sum = sum(
                asset['object'].capacity(model) for asset in self.supply.values()
            )

        demand_sums = [
            sum(asset['object'].power(model, step) for asset in self.demand.values()) \
            for step in model.steps
        ]

        non_compliance = getattr(model, f"{self.handle}::non_compliance")

        setattr(
            model, f"{self.handle}::compliance",
            pyomo.Constraint(
                model.steps,
                rule = lambda m, t: (
                    supply_sum + non_compliance >=
                    demand_sums[t] * margin * sign
                    )
                )
            )
    
        return model

    def objective(self, model):

        non_compliance = getattr(model, f"{self.handle}::non_compliance")

        cost = non_compliance * self.non_compliance_cost
        
        return cost