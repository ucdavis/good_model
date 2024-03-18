import pyomo.environ as pyomo

class Wind:
    def __init__(self, region_id, *wind_data):
        self.region_id = region_id
        self.installed_capacity = 0
        self.gen_profile = {}
        self.max_capacity = {}
        self.cost = {}
        self.transmission_cost = {}

        for data in wind_data:

            data_type = data.get('data_tye', 0)
            parameters = data.get('parameters', [])

            if data_type == 'wind_cost': 

                for params in parameters: 
                    
                    resource_id = str(params.get('resource_class', 0))
                    values = data.get('values', {})
                    for cost_class, info in values.items():
                        self.cost[resource_id][cost_class] = info.get('cost', None)

            elif data_type == 'wind_max_capacity': 
                
                for params in parameters: 
                    resource_id = str(data.params('resource_class', 0))
                    values = params.get('values', {})
                    for cost_class, info in values.items():
                        self.max_capacity[resource_id][cost_class] = info.get('max_capacity', None)

            elif data_type == 'wind_installed_capacity': 
                
                for params in parameters: 
                    resource_id = str(params.get('resource_class', 0))
                    self.installed_capacity[resource_id] = data.get('capacity', 0)

            elif data_type == 'wind_gen':
                 
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
        ## nested dictionary, ex: model.c_windprofile[w][t]
        ## tuple dictionary, ex: model.c_windprofile[w,t]

        if all(self.check_valid_params_list):
        
            windCap = pyomo.Param(initialize=self.installed_capacity, within=pyomo.Any)
            setattr(model, self.region_id + '_windCap', windCap)

            windgenprofile = pyomo.Param(model.wrc, model.t, self.gen_profile, within=pyomo.Any)
            setattr(model, self.region_id + '_windgenprofile', windgenprofile)

            windmax = pyomo.Param(model.wrc, model.cc, self.max_capacity, within=pyomo.Any)
            setattr(model, self.region_id + '_windMax', windmax)

            windCost = pyomo.Param(model.wrc, model.cc, initialize=self.cost, within=pyomo.Any)
            setattr(model, self.region_id + '_windCost', windCost)

            windTransCost = pyomo.Param(model.wrc, model.cc, initialize=self.trans_cost, within=pyomo.Any)
            setattr(model, self.region_id + '_windTransCost', windTransCost)

            return model

    def variables(self, model):
        # decision variables all indexed as, ex: model.x_windNew[w,c]

        if hasattr(model, self.region_id + '_windCost'):

            windNew = pyomo.Var(model.wrc, model.cc, within=pyomo.NonNegativeReals)
            setattr(model, self.region_id + '_windNew', windNew)

        return model

    def objective(self, model):
        # Simplified objective function to correctly sum wind generation and transmission costs
        
        wind_cost_term = 0 

        if hasattr(model, self.region_id + '_windNew'):

            wind_cost_term = pyomo.quicksum(
                (getattr(model, self.region_id + '_windCost')[w][c] + getattr(model, self.region_id + '_windTransCost')[w][c]) * getattr(model, self.region_id + '_windNew')[w,c]
                for w in model.wrc
                for c in model.cc
                ) 
        
        return wind_cost_term

    def constraints(self, model):
        # Corrected and simplified constraints definition
    
        wind_constraints = {}  # Dictionary to store constraint lists for each region

        for s in model.wrc:
            wind_constraints_region = {}  # Dictionary to store constraint lists for each region

            for c in model.cc:
                wind_install_limits_rule = pyomo.ConstraintList()
                wind_constraints_region[c] = wind_install_limits_rule

                if hasattr(model, self.region_id + '_windNew'):
                    constraint_expr = getattr(model, self.region_id + '_windMax')[w][c] - getattr(model, self.region_id + '_windNew')[w, c] >= 0
                    wind_constraints_region[c] = (constraint_expr)
                else:
                    constraint_expr = pyomo.Constraint.Skip()
                    wind_constraints_region[c] = (constraint_expr)

            wind_constraints[s] = wind_constraints_region
        
        setattr(model, self.region_id + '_wind_install_limits', wind_constraints)

        return model
