import pyomo.environ as pyomo


class Load:
    def __init__(self, region_id, **kwargs):
        self.region_id = region_id
        self.load = kwargs.get('load', {})


    def parameters(self, model):

        self.demandLoad = pyomo.Param(self.region_id, model.t, initialize=self.load)
        setattr(model, self.region_id + '_load', self.demandLoad)

    def variables(self, model): 
        pass 

    def objective(self,model): 
        pass 

    def constraints(self, model): 
        pass 

