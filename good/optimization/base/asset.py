import numpy as np
import pyomo.environ as pyomo

class Asset:
    '''
    Super-class for all grid assets. An asset is subordinate to a region and the output
    of all assets must sum to zero for any region at all time steps.
    '''

    __base__ = 'Asset'
    
    def __init__(self, handle, **kwargs):

        self.handle = handle
        self.handles = []

    def parameters(self, model):

        return model

    def variables(self, model):

        return model

    def constraints(self, model):

        return model

    def energy(self, model, step = None):

        return 0.  # Default to no energy contribution

    def power(self, model, step = None):

        return 0.  # Default to no power contribution

    def capacity(self, model, step = None):

        return 0.

    def objective(self, model):
        """Base objective function returns zero cost"""

        return 0.  # Default to no cost for assets

    def solution(self, model):

        solution = {}

        for handle in self.handles:

            value = list(getattr(model, handle).extract_values().values())
            solution[handle] = value

        return solution 