import pyomo.environ as pyomo

class Solar:
    def __init__(self, region_id, *solar_data):
        
        self.region_id = region_id
        self.installed_capacity = 0
        self.gen_profile = {}
        self.max_capacity = {}
        self.cost = {}
        self.transmission_cost = {}

        for data in solar_data:

            data_type = data.get('data_type', 0)
            parameters = data.get('parameters', [])

            if data_type == 'solar_cost': 

                for params in parameters: 
                    
                    resource_id = str(params.get('resource_class', 0))
                    values = data.get('values', {})
                    for cost_class, info in values.items():
                        self.cost[resource_id][cost_class] = info.get('cost', None)

            elif data_type == 'solar_max_capacity': 
                
                for params in parameters: 
                    resource_id = str(data.params('resource_class', 0))
                    values = params.get('values', {})
                    for cost_class, info in values.items():
                        self.max_capacity[resource_id][cost_class] = info.get('max_capacity', None)

            elif data_type == 'solar_installed_capacity': 
                
                for params in parameters: 
                    self.installed_capacity = data.get('capacity', 0)

            elif data_type == 'solar_gen':
                 
                 for params in parameters: 
                    resource_id = str(data.get('resource_class', 0))
                    self.gen_profile[resource_id] = data.get('generation_profile', {})

            elif data_type == 'transmission_cost': 
                 
                 for params in parameters: 
                    resource_id = str(params.get('resource_class', 0))
                    self.transmission_cost[resource_id] = params.get('transmission_cost', 0)

            
        self.check_valid_params_list = [self.gen_profile, self.cost]

    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_solarprofile[s][t]
        ## tuple dictionary, ex: model.c_solarprofile[s,t]
        
        if all(self.check_valid_params_list):
            
            self.solarCap = pyomo.Param(model.src, initialize=self.installed_capacity, within=pyomo.Reals)
            setattr(model, self.region_id + '_solarCap', self.solarCap)

            self.solarprofile = pyomo.Param(model.src, model.t, initialize=self.gen_profile, within=pyomo.Reals)
            setattr(model, self.region_id + '_solarprofile', self.solarprofile)

            self.solarMax = pyomo.Param(model.src, model.cc, initialize=self.max_capacity, within=pyomo.Reals)
            setattr(model, self.region_id + '_solarMax', self.solarMax)

            self.solarCost = pyomo.Param(model.src, model.cc, initialize=self.cost, within=pyomo.Reals)
            setattr(model, self.region_id + '_solarCost', self.solarCost)

            self.transCost = pyomo.Param(model.src, initialize=self.transmission_cost)
            setattr(model, self.region_id + '_solarTransCost', self.transCost)

        return model 

    def variables(self, model):
        # decision variables all indexed as, ex: model.x_solarNew[s,c]

        if hasattr(model, self.region_id + '_solarCost'):

            self.solarNew = pyomo.Var(model.src, model.cc, within=pyomo.NonNegativeReals)
            setattr(model, self.region_id + '_solarNew', self.solarNew)

        return model

    def objective(self, model):
        # Simplify the construction of the objective function

        solar_cost_term = 0
    
        if hasattr(model, self.region_id + '_solarNew') and hasattr(model, self.region_id + '_solarCost'):

            solar_cost_term = pyomo.quicksum(
                getattr(model, self.region_id + '_solarCost')[s][c] * getattr(model, self.region_id + '_solarNew')[s, c] 
                for s in model.src
                for c in model.cc) 
            
        return solar_cost_term

    def constraints(self, model):

        solar_constraints = {}  # Dictionary to store constraint lists for each region

        for s in model.src:
            solar_constraints_region = {}  # Dictionary to store constraint lists for each region

            for c in model.cc:
                solar_install_limits_rule = pyomo.ConstraintList()
                solar_constraints_region[c] = solar_install_limits_rule

                if hasattr(model, self.region_id + '_solarNew'):
                    constraint_expr = getattr(model, self.region_id + '_solarMax')[s][c] - getattr(model, self.region_id + '_solarNew')[s, c] >= 0
                    solar_constraints_region[c] = (constraint_expr)
                else:
                    constraint_expr = pyomo.Constraint.Skip()
                    solar_constraints_region[c] = (constraint_expr)

            solar_constraints[s] = solar_constraints_region
        
        setattr(model, self.region_id + '_solar_install_limits', solar_constraints)

        return model