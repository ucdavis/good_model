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

        self.profile = kwargs.get('profile', None)

        if self.profile is not None:

            self.profile = np.array(self.profile)

    def parameters(self, model):

        if self.profile is None:
            self.profile = [0] * len(model.steps)

        # Get start and stop indices, defaulting to 0 and length of steps
        start_idx = getattr(model, 'start', 0)
        stop_idx = getattr(model, 'stop', len(model.steps))
        
        # Convert to int if they're not already
        if hasattr(start_idx, 'value'):
            start_idx = int(start_idx)
        if hasattr(stop_idx, 'value'):
            stop_idx = int(stop_idx)
        
        # Ensure profile is long enough
        if len(self.profile) < stop_idx:
            self.profile = np.pad(self.profile, (0, stop_idx - len(self.profile)), 'constant')

        handle = f"{self.handle}::profile"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Param(model.steps,
                initialize = {i: self.profile[i] for i in range(start_idx, stop_idx)}
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
                    model.steps, initialize = {i: 0 for i in model.steps}
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

            shift_sum = pyomo.quicksum(shift[t] for t in model.steps)

            setattr(
                model, f"{self.handle}::shift_sum_constraint",
                pyomo.Constraint(expr = (0, shift_sum, 0)),
                )

        return model

    def energy(self, model, step = None):
        """Energy contribution of the load"""
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

        return -1 * energy  # Negative for consumption

    def capacity(self, model, step = None):

        capex = getattr(model, f"{self.handle}::capex")

        capacity = self.installed_capacity + capex

        return capacity

    def objective(self, model):

        profile = getattr(model, f"{self.handle}::profile")
        shift = getattr(model, f"{self.handle}::shift")
        capex = getattr(model, f"{self.handle}::capex")

        capacity = self.installed_capacity + capex
        
        cost = pyomo.quicksum(
            (profile[t] + shift[t]) * model.time_step * capacity * self.operating_cost \
            for t in model.steps
            )

        return cost

    def results(self, model, results):
        """Collect load results including any shifting"""
        handle = self.handle
        
        # Get the profile parameter
        profile = getattr(model, f"{handle}::profile")
        results[f'{handle}::profile'] = [profile[t] for t in model.steps]
        
        # Get the shift variable if it exists
        shift = getattr(model, f"{handle}::shift")
        
        # Calculate total shifted profile
        shifted = []
        for t in model.steps:
            base = profile[t] * self.installed_capacity
            shift_amount = shift[t].value if self.shiftable else 0
            shifted.append(base + shift_amount)
        
        results[f'{handle}::shifted'] = shifted
        
        # Convert to numpy arrays
        results[f'{handle}::profile'] = np.array(results[f'{handle}::profile'])
        results[f'{handle}::shifted'] = np.array(results[f'{handle}::shifted'])
        
        return results