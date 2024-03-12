import pyomo.environ as pyomo


class Load:
    def __init__(self, region_id, load_data):
        self.region_id = region_id
        self.load = load_data.get('values', {})


    def parameters(self, model):

        self.demandLoad = pyomo.Param(model.t, initialize=self.load)
        setattr(model, self.region_id + '_load', self.demandLoad)

    def variables(self, model): 
        pass 

    def objective(self,model): 
        pass 

    def constraints(self, model): 
        pass 

