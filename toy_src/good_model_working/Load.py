import pyomo.environ as pyomo
from .constants import time_periods


class Load:
    def __init__(self, region_id, load_data):
        self.region_id = region_id
        self.time_periods = time_periods

        for data in load_data: 

            params = data.get('parameters',[])

            for param in params: 

                self.load = param.get('value', {})

        self.load = {int(key): value for key, value in self.load.items()
            if int(key) in self.time_periods}

    def parameters(self, model):

        model.add_component(
            self.region_id + '_load', 
            pyomo.Param(model.t, initialize=self.load, default=0)
        )

    def variables(self, model): 
        
        return model

    def objective(self, model): 
        
        return 0

    def constraints(self, model): 
        
        return model

    def results(self, model, results): 
        
        return 0

