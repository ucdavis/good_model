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

                    if values: 
                        for cost_class, info in values.items():
                            index = (resource_id, cost_class)
                            self.cost[index] = info
                    else: 
                        self.cost = {}

            elif data_type == 'solar_max_capacity': 
                
                for params in parameters: 
                    
                    resource_id = str(params.get('resource_class', 0))
                    values = params.get('max_capacity', {})

                    if values: 
                        for cost_class, info in values.items():
                            index_key = (resource_id, cost_class)
                            self.max_capacity[index_key] = info
                    else: 
                        self.max_capacity = {}
                    
            elif data_type == 'solar_installed_capacity': 
                
                for params in parameters: 
                    self.installed_capacity = params.get('capacity', 0)

            elif data_type == 'solar_gen':
                 
                 for params in parameters:
                    resource_id = str(params.get('resource_class', 0))
                    values = params.get('generation_profile', {})

                    if values: 
                        for hour, load in values.items():
                            index_key = (resource_id, int(hour))
                            self.gen_profile[index_key] = load
                    else:
                        self.gen_profile = {}

            elif data_type == 'solar_transmission_cost': 
                 
                 for params in parameters: 
                    resource_id = params.get('resource_class', 0)
                    values = params.get('transmission_cost', {})

                    if values: 
                        for cost_class, info in values.items():
                            index_key = (str(resource_id), cost_class)
                            self.transmission_cost[index_key] = info
                    else: 
                        self.transmission_cost = {}

    
    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_solarprofile[s][t]
        ## tuple dictionary, ex: model.c_solarprofile[s,t]

        if self.installed_capacity:
            model.add_component(
                self.region_id + '_solarCap', 
                pyomo.Param(initialize=self.installed_capacity, within=pyomo.Reals)
            )

       
        if self.max_capacity: 
            model.add_component(
                self.region_id + '_solarMax', 
                pyomo.Param(model.src, model.cc, initialize=self.max_capacity, within=pyomo.Reals)
            )

        if self.cost:
            model.add_component( 
                self.region_id + '_solarCost', 
                pyomo.Param(model.src, model.cc,  initialize=self.cost, within=pyomo.Reals)
            )

        if self.gen_profile: 
            model.add_component( 
                self.region_id + '_solarprofile', 
                pyomo.Param(model.src, model.t,initialize=self.gen_profile, within=pyomo.Reals)
            )

        if self.transmission_cost:
            model.add_component( 
                self.region_id + '_solarTransCost', 
                pyomo.Param(model.src, model.cc, initialize=self.transmission_cost, within=pyomo.Reals)
            )        
        

    def variables(self, model):
        # decision variables all indexed as, ex: model.x_solarNew[s,c]

        model.add_component(
            self.region_id + '_solarNew', pyomo.Var(model.src, model.cc, domain=pyomo.NonNegativeReals)
        )


    def objective(self, model):
        # Simplify the construction of the objective function

        solar_cost_term = 0

        if hasattr(model, self.region_id + '_solarTransCost'):

            solar_indices = [(s,c) for s in model.src for c in model.cc if (s,c) in getattr(model, self.region_id + '_solarCost')]
            solar_cost_term = pyomo.quicksum(
                (getattr(model, self.region_id + '_solarCost')[s,c] + getattr(model, self.region_id + '_solarTransCost')[s,c]) 
                * getattr(model, self.region_id + '_solarNew')[s, c] 
                for (s,c) in solar_indices
            ) 
        
        elif hasattr(model, self.region_id + '_solarCost'): 
            
            solar_indices = [(s,c) for s in model.src for c in model.cc if (s,c) in getattr(model, self.region_id + '_solarCost')]
            solar_cost_term = pyomo.quicksum(
                (getattr(model, self.region_id + '_solarCost')[s,c]) * getattr(model, self.region_id + '_solarNew')[s, c] 
                for (s,c) in solar_indices
            ) 
        
        else: 

            solar_cost_term 

        return solar_cost_term


    def constraints(self, model):
    
        def solar_constraints(model, s, c): 
            
            if hasattr(model, self.region_id + '_solarMax'):

                if (s, c) in getattr(model, self.region_id + '_solarMax'): 
                    return getattr(model, self.region_id + '_solarMax')[s, c] - getattr(model, self.region_id + '_solarNew')[s, c] >= 0
                else: 
                    return pyomo.Constraint.Skip
            
            else: 
                return pyomo.Constraint.Skip
        
        model.add_component(
            self.region_id + '_solar_install_limits', 
            pyomo.Constraint(model.src, model.cc, rule = solar_constraints)
        )