from ..base.policy import Policy

import numpy as np
import pyomo.environ as pyomo
import logging

class RPS(Policy):
    '''
    An RPS policy applies to assets in a Jurisdiction and is enforced over the duration
    of the optimization time period.

    There are four verieties of RPS:

    1. Generation portion: requires a given portion of energy contributed to come from
    a given set of assets

    2. Generation minimum: requires a given amount of energy contributed to come from
    a given set of assets

    3. Capacity portion: requires a given portion of capacity to belong to a given set
    of assets

    4. Capacity portion: requires a given amount of capacity to belong to a given set
    of assets

    RPS policies can be enforce strictly or permissively. Strict enforcement results in
    an unfeasible condition if the RPS is not met. Permissive enforcement adds a scaled
    penalty for failing to meet the RPS.
    '''

    def __init__(self, handle, **kwargs):

        super().__init__(handle, **kwargs)

        # Parameters
        inclusion_criteria = kwargs.get('inclusion_criteria', [])
        exclusion_criteria = kwargs.get('exclusion_criteria', [])

        self.inclusion_criteria = self.interpret(inclusion_criteria)
        self.exclusion_criteria = self.interpret(exclusion_criteria)

        self.assets = kwargs.get('assets', [])
        self.included = self.build_set(self.assets, self.inclusion_criteria)
        self.excluded = self.build_set(self.assets, self.exclusion_criteria)

        self.active = len(self.included) > 0

        self.generation_portion = kwargs.get('generation_portion', 0)
        self.generation_portion_rule = self.generation_portion > 0

        self.capacity_portion = kwargs.get('capacity_portion', 0)
        self.capacity_portion_rule = self.capacity_portion > 0

        self.generation_minimum = kwargs.get('generation_minimum', 0)
        self.generation_minimum_rule = self.generation_minimum > 0

        self.capacity_minimum = kwargs.get('capacity_minimum', 0)
        self.capacity_minimum_rule = self.capacity_minimum > 0

        self.make_included_generation = (
            self.generation_portion_rule or
            self.generation_minimum_rule
            )

        self.make_excluded_generation = self.generation_portion_rule

        self.make_included_capacity = (
            self.capacity_portion_rule or
            self.capacity_minimum_rule
            )
        
        self.make_excluded_capacity = self.capacity_portion_rule

        self.penalty = kwargs.get('penalty', np.inf)
        self.strict = np.isinf(self.penalty)

    def build_set(self, assets, criteria):

        included = []

        for asset in assets:

            include = True

            for fun in criteria:

                include *= fun(asset)

            if include:

                included.append(asset)

        return included

    def interpret(self, criteria):

        interpreted_criteria = []

        for fun in criteria:
            if isinstance(fun, str):

                fun = eval(fun)
            
            interpreted_criteria.append(fun)

        return interpreted_criteria

    def constraints(self, model):

        if self.strict and self.active:

            if self.make_included_generation:

                included_generation = sum(
                        asset['object'].energy(model) for asset in self.included 
                    )

            if self.make_excluded_generation:

                excluded_generation = sum(
                        asset['object'].energy(model) for asset in self.excluded 
                    )

            if self.make_included_capacity:

                included_capacity = sum(
                        asset['object'].capacity(model) for asset in self.included 
                    )

            if self.make_excluded_capacity:

                excluded_capacity = sum(
                        asset['object'].capacity(model) for asset in self.excluded 
                )

            if self.generation_portion_rule:

                setattr(
                    model, f"{self.handle}::rps_generation_portion",
                    pyomo.Constraint(
                        expr = (
                            included_generation >=
                            included_generation * self.generation_portion +
                            excluded_generation * self.generation_portion
                            )
                        )
                    )

            if self.capacity_portion_rule:

                setattr(
                    model, f"{self.handle}::rps_capacity_portion",
                    pyomo.Constraint(
                        expr = (
                            included_capacity >=
                            included_capacity * self.capacity_portion +
                            excluded_capacity * self.capacity_portion
                            )
                        )
                    )

            if self.generation_minimum_rule:

                setattr(
                    model, f"{self.handle}::rps_generation_minimum",
                    pyomo.Constraint(
                        expr = (
                            included_generation >= self.generation_minimum
                            )
                        )
                    )

            if self.capacity_minimum_rule:

                setattr(
                    model, f"{self.handle}::rps_capacity_minimum",
                    pyomo.Constraint(
                        expr = (
                            included_capacity >= self.capacity_minimum
                            )
                        )
                    )
    
        return model

    def objective(self, model):

        cost = 0.

        if not self.strict and self.active:

            if self.make_included_generation:

                included_generation = sum(
                        asset['object'].energy(model) for asset in self.included 
                    )

            if self.make_excluded_generation:

                excluded_generation = sum(
                        asset['object'].energy(model) for asset in self.excluded 
                    )

            if self.make_included_capacity:

                included_capacity = sum(
                        asset['object'].capacity(model) for asset in self.included 
                    )

            if self.make_excluded_capacity:

                excluded_capacity = sum(
                        asset['object'].capacity(model) for asset in self.excluded 
                )

            if self.generation_portion_rule:

                cost = (
                    included_generation * self.generation_portion +
                    excluded_generation * self.generation_portion -
                    included_generation
                    ) * self.penalty

            if self.capacity_portion_rule:

                cost = (
                    included_capacity * self.generation_portion +
                    excluded_capacity * self.generation_portion -
                    included_capacity
                    ) * self.penalty

            if self.generation_minimum_rule:

                cost = (self.generation_minimum - included_generation) * self.penalty

            if self.capacity_minimum_rule:

                cost = (self.capacity_minimum - included_capacity) * self.penalty
        
        return cost