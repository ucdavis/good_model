import pyomo.environ as pyomo
from .constants import time_periods

class Solar:
    def __init__(self, region_id, solar_data):
        
        self.region_id = region_id
        self.installed_capacity = 0
        self.gen_profile = {}
        self.max_capacity = {}
        self.cost = {}
        self.transmission_cost = {}
        self.resource_id_profile = []
        self.cost_class_ids = []
        self.time_periods = time_periods

        for data in solar_data:

            data_type = data.get('data_type', 0)
            parameters = data.get('parameters', [])

            if data_type == 'solar_cost': 

                for params in parameters: 
                    resource_id = str(int(params.get('resource_class', 0)))
                    values = params.get('cost', {})

                    if values: 
                        for cost_class, info in values.items():
                            index = (resource_id, cost_class)
                            self.cost[index] = info
                    else: 
                        self.cost = {}

            elif data_type == 'solar_max_capacity': 
                
                for params in parameters: 
                    
                    resource_id = str(int(params.get('resource_class', 0)))
                    values = params.get('max_capacity', {})

                    if values: 
                        for cost_class, info in values.items():
                            self.cost_class_ids.append(cost_class)
                            index_key = (resource_id, cost_class)
                            self.max_capacity[index_key] = info
                    else: 
                        self.max_capacity = {}
                    
            elif data_type == 'solar_installed_capacity': 
                
                for params in parameters: 
                    installed_capacity = params.get('capacity', 0)

            elif data_type == 'solar_gen':
                 
                 for params in parameters:
                    resource_id = str(int(params.get('resource_class', 0)))
                    self.resource_id_profile.append(resource_id)
                    values = params.get('generation_profile', {})

                    
                    if values:
                        max_load = max(values.values())
                        if max(self.time_periods) != 4380: 
                            self.gen_profile.update({(resource_id, int(hour)): load / max_load
                                for hour, load in values.items()
                                if int(hour) in self.time_periods})
                        else:
                            self.gen_profile.update({(resource_id, int(hour)): load / max_load
                                for hour, load in values.items()})
                    else:
                        self.gen_profile = {}

            elif data_type == 'solar_transmission_cost': 
                 
                 for params in parameters: 
                    resource_id = str(int(params.get('resource_class', 0)))
                    values = params.get('transmission_cost', {})

                    if values: 
                        for cost_class, info in values.items():
                            index_key = (resource_id, cost_class)
                            self.transmission_cost[index_key] = info
                    else: 
                        self.transmission_cost = {}

        if self.installed_capacity is not None: 
            if self.resource_id_profile:
                capacity = {(i,j): 0 for i in self.resource_id_profile for j in self.cost_class_ids}
                first_key = next(iter(capacity))
                capacity[first_key] = self.installed_capacity
                self.installed_capacity = capacity

        
    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_solarprofile[s][t]
        ## tuple dictionary, ex: model.c_solarprofile[s,t]

        model.add_component(
            self.region_id + '_solarCap', 
            pyomo.Param(model.src, model.cc, initialize=self.installed_capacity, default=0)
        )

        model.add_component(
            self.region_id + '_solarMax', 
            pyomo.Param(model.src, model.cc, initialize=self.max_capacity, default=0)
        )

        model.add_component( 
            self.region_id + '_solarCost', 
            pyomo.Param(model.src, model.cc,  initialize=self.cost, default=0)
        )

        model.add_component( 
            self.region_id + '_solarGenProfile', 
            pyomo.Param(model.src, model.t,initialize=self.gen_profile, default=0)
        )

        model.add_component( 
            self.region_id + '_solarTransCost', 
            pyomo.Param(model.src, model.cc, initialize=self.transmission_cost, default=0)
        )        
        

    def variables(self, model):
        # decision variables all indexed as, ex: model.x_solarNew[s,c]

        model.add_component(
            self.region_id + '_solarNew', 
            pyomo.Var(model.src, model.cc, within=pyomo.NonNegativeReals, bounds = (1e-08, None))
        )


    def objective(self, model):
        # Simplify the construction of the objective function

        solar_cost_term = 0

        if hasattr(model, self.region_id + '_solarTransCost') and hasattr(model, self.region_id + '_solarCost'):

            solar_indices = [(s,c) for s in model.src for c in model.cc if (s,c) in getattr(model, self.region_id + '_solarCost')]
            solar_cost_term = pyomo.quicksum(
                (getattr(model, self.region_id + '_solarCost')[s,c] + getattr(model, self.region_id + '_solarTransCost')[s,c]) 
                * getattr(model, self.region_id + '_solarNew')[s,c] 
                for (s,c) in solar_indices
            ) 
        
        elif hasattr(model, self.region_id + '_solarCost'): 
            
            solar_indices = [(s,c) for s in model.src for c in model.cc if (s,c) in getattr(model, self.region_id + '_solarCost')]
            solar_cost_term = pyomo.quicksum(
                (getattr(model, self.region_id + '_solarCost')[s,c]) * getattr(model, self.region_id + '_solarNew')[s,c] 
                for (s,c) in solar_indices
            ) 
        
        else: 

            solar_cost_term = 0

        return solar_cost_term


    def constraints(self, model):
    
        def solar_constraints(model, s, c): 
            
            if hasattr(model, self.region_id + '_solarMax'):
                if (s,c) in getattr(model, self.region_id + '_solarMax'):
                    return getattr(model, self.region_id + '_solarMax')[s,c] - getattr(model, self.region_id + '_solarNew')[s,c] >= 0
                else: 
                    return pyomo.Constraint.Skip
            else: 
                return pyomo.Constraint.Skip
        
        model.add_component(
            self.region_id + '_solar_install_limits', 
            pyomo.Constraint(model.src, model.cc, rule = solar_constraints)
        )

    def results(self, model, results): 

        results = {}
        
        capacity_dict = {}
        cost_dict ={}

        trans_var = getattr(model, self.region_id + '_solarTransCost',0)

        if hasattr(model, self.region_id + '_solarNew'): 
            capacity_var = getattr(model, self.region_id + '_solarNew').extract_values()
            
            for key, value in capacity_var.items(): 
                
                if key not in capacity_dict: 
                    capacity_dict[key] = {}

                else: 
                    capacity_dict[key] +=  value
    

        if hasattr(model, self.region_id + '_solarcost'): 
            cost_var = getattr(model, self.region_id + '_solarcost').extract_values()
            trans_cost = trans_var.extract_values()

            for key, value in cost_var.items(): 

                if key not in capacity_dict: 
                    capacity_cost[key] = {}

                else: 
                    capacity_cost[key] +=  capacity_dict[key] * (value + trans_cost[key])

        results = {
            'capacity': capacity_dict,
            'cost': cost_dict
            }

        return results