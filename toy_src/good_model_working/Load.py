import pyomo.environ as pyomo


class Load:
    def __init__(self, region_id, **kwargs):
        self.region_id = region_id
        self.load = kwargs.get('load', {})

    def sets(self, model): 
        pass 

    def parameters(self, model):
        model.c_demandLoad = pyomo.Param(model.t, initialize=self.load)

    def variables(self, model): 
        pass 

    def objective(self,model): 
        pass 

    def constraints(self, model): 
        pass 

