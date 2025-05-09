import numpy as np
import pyomo.environ as pyomo

class Policy:
    '''
    Super-class for all nodal policies. A nodal policy enforces a constraint which guarantees
    that a specified portion of energy produced by node assets must come from assets with a
    specified tag over a specified time period
    '''

    __base__ = 'Policy'
    
    def __init__(self, handle, **kwargs):

        self.handle = handle
        self.handles = []

    def parameters(self, model, assets = []):

        return model

    def variables(self, model, assets = []):

        return model

    def constraints(self, model, assets = []):

        return model

    def objective(self, model, assets = []):
        """Base objective function returns zero cost"""

        return 0.0  # Default to no cost for assets

    def solution(self, model):

        solution = {}

        for handle in self.handles:

            value = list(getattr(model, handle).extract_values().values())
            solution[handle] = value

        return solution 