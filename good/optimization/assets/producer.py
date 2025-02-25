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

    def parameters(self, model):
        """Set up parameters for the producer"""
        
        # Handle profile if it's None or not long enough
        if self.profile is None:
            self.profile = [1.0] * len(model.steps)
        elif len(self.profile) < len(model.steps):
            # Pad profile with ones if it's too short
            self.profile = np.pad(self.profile, (0, len(model.steps) - len(self.profile)), 
                                 'constant', constant_values=1.0)
        
        # Get start and stop indices, defaulting to 0 and length of steps
        start_idx = getattr(model, 'start', 0)
        stop_idx = getattr(model, 'stop', len(model.steps))
        
        # Convert to int if they're not already
        if hasattr(start_idx, 'value'):
            start_idx = int(start_idx)
        if hasattr(stop_idx, 'value'):
            stop_idx = int(stop_idx)
        
        # Create profile parameter
        handle = f"{self.handle}::profile"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Param(model.steps,
                initialize = {i: self.profile[i] for i in range(len(model.steps))}
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
        

        # Capacity Factor Profile
        if self.profile is None:

            handle = f"{self.handle}::profile"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Param(model.steps, initialize = self.capacity_factor),
            )

        else:

            handle = f"{self.handle}::profile"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Param(model.steps, initialize = self.profile[:len(model.steps)]),
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
        def ramp_rate_rule(m, t):

            if t == 0:

                rule = (0, production[t], np.inf)

            else:

                rule = (
                    -self.ramp_rate * (self.installed_capacity + capex),
                    production[t] - production[t - 1],
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

        if step is None:

            energy = pyomo.quicksum(
                production[i] * model.time_step for i in model.steps
            )

        else:

            energy = production[step] * model.time_step

        return energy

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