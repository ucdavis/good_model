import pyomo.environ as pyomo

class Solar:
    def __init__(self, region_id, solar_data):
        
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
                    values = params.get('cost', {})

                    for cost_class, info in values.items():
                        index = (resource_id, cost_class)
                        self.cost[index] = info

            elif data_type == 'solar_max_capacity': 
                
                for params in parameters: 
                    
                    resource_id = str(params.get('resource_class', 0))
                    values = params.get('max_capacity', {})

                    for cost_class, info in values.items():
                        index = (resource_id, cost_class)
                        self.max_capacity[index] = info
                    
            elif data_type == 'solar_installed_capacity': 
                
                for params in parameters: 
                    self.installed_capacity = params.get('capacity', 0)

            elif data_type == 'solar_gen':
                 
                 for params in parameters:
                    resource_id = str(params.get('resource_class', 0))
                    profile = params.get('generation_profile', {})

                    for hour, load in profile.items():
                        index = (resource_id, int(hour))
                        self.gen_profile[index] = load

            elif data_type == 'solar_transmission_cost': 
                 
                 for params in parameters: 
                    resource_id = str(params.get('resource_class', 0))
                    values = params.get('transmission_cost', {})

                    if values: 
                        for cost_class, info in values.items():
                            self.transmission_cost[resource_id] = {cost_class: info}

    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_solarprofile[s][t]
        ## tuple dictionary, ex: model.c_solarprofile[s,t]

        
        model.add_component(
            self.region_id + '_solarCap', 
            pyomo.Param(initialize=self.installed_capacity, within=pyomo.Reals)
        )

        model.add_component(
            self.region_id + '_solarMax', 
            pyomo.Param(model.src, model.cc, initialize=self.max_capacity, within=pyomo.Reals)
        )

        model.add_component( 
            self.region_id + '_solarCost', 
            pyomo.Param(model.src, model.cc,  initialize=self.cost, within=pyomo.Reals)
        )

        model.add_component( 
            self.region_id + '_solarprofile', 
            pyomo.Param(model.src, model.t,initialize=self.gen_profile, within=pyomo.Reals)
        )

        model.add_component( 
            self.region_id + '_solarTransCost', 
            pyomo.Param(model.src, initialize=self.transmission_cost, within=pyomo.Any)
        )        
        
        return model 

    def variables(self, model):
        # decision variables all indexed as, ex: model.x_solarNew[s,c]

        if hasattr(model, self.region_id + '_solarCost'):

            solarNew = pyomo.Var(model.src, model.cc, within=pyomo.NonNegativeReals)
            setattr(model, self.region_id + '_solarNew', solarNew)

            print('solar_vars')

        return model

    def objective(self, model):
        # Simplify the construction of the objective function

        solar_cost_term = 0
    
        if hasattr(model, self.region_id + '_solarNew') and hasattr(model, self.region_id + '_solarCost'):
        
            solar_cost_term = pyomo.quicksum(
                getattr(model, self.region_id + '_solarCost')[s,c] * getattr(model, self.region_id + '_solarNew')[s, c] 
                for s in model.src
                for c in model.cc
                if (s, c) in getattr(model, self.region_id + '_solarCost')
            ) 
            
        return solar_cost_term

    def constraints(self, model):
    
        constraint_dict = {}

        for s in model.src:
            for c in model.cc:
                if (s, c) in getattr(model, self.region_id + '_solarMax'): 
                    # Construct the constraint expression
                    constraint_expr = (
                        getattr(model, self.region_id + '_solarMax')[s, c] - getattr(model, self.region_id + '_solarNew')[s, c]) >= 0
                    # Add the constraint expression to the dictionary
                    constraint_dict[(s, c)] = constraint_expr

        # Create the ConstraintList and add the constraint expressions
        solar_install_limits_rule = pyomo.ConstraintList()
        for key, constraint_expr in constraint_dict.items():
            solar_install_limits_rule.add(constraint_expr)

        # Set the ConstraintList attribute on the model
        setattr(model, self.region_id + '_solar_install_limits', solar_install_limits_rule)

        return model