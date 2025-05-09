from ..base.policy import Policy

import numpy as np
import pyomo.environ as pyomo
import logging

class Capacity_Target(Policy):

    def __init__(self, handle, **kwargs):

        super().__init__(handle, **kwargs)

        # Terms of the policy
        self.target = kwargs.get('target', 0)

        self.non_compliance_capacity = kwargs.get('non_compliance_capacity', 0)
        self.non_compliance_cost = kwargs.get('non_compliance_cost', 1)

        # Criteria for assigning assets to sets
        inclusion_criteria = kwargs.get('inclusion_criteria', {})

        # Truning srings into functions if needed
        self.inclusion_criteria = self.interpret(inclusion_criteria)

        # Building the incuded and excluded sets
        self.assets = kwargs.get('assets', [])
        self.included = self.build_set(self.assets, self.inclusion_criteria)


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

        handle = f"{self.handle}::target"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Param(initialize = self.target, mutable = True),
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

        target = getattr(model, f"{self.handle}::target")

        included_sum = sum(
                asset['object'].capacity(model) for asset in self.included.values()
            )

        non_compliance = getattr(model, f"{self.handle}::non_compliance")

        setattr(
            model, f"{self.handle}::compliance",
            pyomo.Constraint(
                expr = (
                    included_sum + non_compliance >= target
                    )
                )
            )
    
        return model

    def objective(self, model):

        non_compliance = getattr(model, f"{self.handle}::non_compliance")

        cost = non_compliance * self.non_compliance_cost
        
        return cost