import pyomo.environ as pyomo

class Load:
    def __init__(self, region_id, **kwargs):
        self.region_id = region_id
        # Assuming 'load' is passed as a dictionary {time: load_value}
        # Correctly extract 'load' from kwargs
        self.load = kwargs.get('load', {})

    def parameters(self, model):
        # Correct initialization of Pyomo parameter for demand load
        # Removed incorrect self.model and properly reference 'self.load'
        model.c_demandLoad = pyomo.Param(model.t, initialize=self.load)

