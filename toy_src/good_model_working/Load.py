import pyomo.environ as pyomo


class Load:
    def __init__(self, region_id, load_data):
        self.region_id = region_id

        for data in load_data: 

            params = data.get('parameters',[])

            for param in params: 

                self.load = param.get('value', {})

        self.load = {int(key): value for key, value in self.load.items()}

    def parameters(self, model):

        model.add_component(
            self.region_id + '_load', 
            pyomo.Param(model.t, initialize=self.load)
        )

        return model

    def variables(self, model): 
        
        return model

    def objective(self, model): 
        
        return 0

    def constraints(self, model): 
        
        return model

