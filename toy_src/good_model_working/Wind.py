import pyomo.environ as pyomo
from .constants import time_periods

class Wind:
    def __init__(self, region_id, wind_data):
        self.region_id = region_id
        self.installed_capacity = 0
        self.gen_profile = {}
        self.max_capacity = {}
        self.cost = {}
        self.transmission_cost = {}
        self.resource_id_profile = []
        self.time_periods = time_periods
        self.cost_class_ids = []

        for data in wind_data:

            data_type = data.get('data_type', 0)
            parameters = data.get('parameters', [])

            if data_type == 'wind_cost': 

                for params in parameters: 
                    resource_id = str(int(params.get('resource_class', 0)))
                    values = params.get('cost', {})

                    if values:
                        for cost_class, info in values.items():
                            index = (resource_id, cost_class)
                            self.cost[index] = info
                    else: 
                        self.cost = {}

            elif data_type == 'wind_max_capacity': 
                
                for params in parameters: 
                    
                    resource_id = str(int(params.get('resource_class', 0)))
                    values = params.get('max_capacity', {})

                    if values: 
                        for cost_class, info in values.items():
                            self.cost_class_ids.append(cost_class)
                            index = (resource_id, cost_class)
                            self.max_capacity[index] = info
                    else: 
                        self.max_capacity = {}
                    
            elif data_type == 'wind_installed_capacity': 
                
                for params in parameters: 
                    self.installed_capacity = params.get('capacity', 0)
 
            elif data_type == 'wind_gen':
                
                for params in parameters:
                    resource_id = str(int(params.get('resource_class', 0)))
                    self.resource_id_profile.append(resource_id)
                    values = params.get('generation_profile', {})
                    
                    if values: 
                        max_load = max(values.values())
                        for hour, load in values.items():
                            # hour = int(hour)
                            # if hour in self.time_periods:
                            index_key = (resource_id, int(hour))
                            normalized_load = load/ max_load
                            self.gen_profile[index_key] = normalized_load
                    else:
                        self.gen_profile = {}

            elif data_type == 'wind_transmission_cost': 
                
                for params in parameters: 
                    resource_id = str(int(params.get('resource_class', 0)))
                    values = params.get('transmission_cost', {})

                    if values: 
                        for cost_class, info in values.items():
                            index = (resource_id, cost_class)
                            self.transmission_cost[index] = info
                    else: 
                        self.transmission_cost= {}

        if self.installed_capacity is not None: 
            if self.resource_id_profile:
                capacity = {(i,j): 0 for i in self.resource_id_profile for j in self.cost_class_ids}
                first_key = next(iter(capacity))
                capacity[first_key] = self.installed_capacity
                self.installed_capacity = capacity

        # self.gen_profile= {(s, h): value for (s,h), value in self.gen_profile.items() if h <= 8760}

    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_windprofile[w][t]
        ## tuple dictionary, ex: model.c_windprofile[w,t]

        if self.installed_capacity:
            model.add_component(
                self.region_id + '_windCap',
                pyomo.Param(model.wrc, model.cc, initialize=self.installed_capacity, default=0)
            )
 
        if self.max_capacity: 
            model.add_component(
                self.region_id + '_windMax',
                pyomo.Param(model.wrc, model.cc, initialize=self.max_capacity, default=0)
            )
        
        if self.cost: 
            model.add_component(
                self.region_id + '_windCost',
                pyomo.Param(model.wrc, model.cc, initialize=self.cost, default=0)
            )
  
        if self.transmission_cost: 
            model.add_component(
                self.region_id + '_windTransCost',
                pyomo.Param(model.wrc, model.cc, initialize=self.transmission_cost, default=0)
            )

        if self.gen_profile: 
            model.add_component(
                self.region_id + '_windGenProfile',
                pyomo.Param(model.wrc, model.t, initialize= self.gen_profile, default=0)
            )

            
    def variables(self, model):
        # decision variables all indexed as, ex: model.x_windNew[w,c]

        model.add_component(
            self.region_id + '_windNew', 
            pyomo.Var(model.wrc, model.cc, within=pyomo.NonNegativeReals, bounds = (1e-08, None))
        )

    def objective(self, model):
        
        wind_cost_term = 0 

        if hasattr(model, self.region_id + '_windTransCost') and hasattr(model, self.region_id + '_windCost'): 

            wind_indices = [(w,c) for w in model.wrc for c in model.cc if (w,c) in getattr(model, self.region_id + '_windCost')]
            wind_cost_term = pyomo.quicksum(
                (getattr(model, self.region_id + '_windCost')[w,c] + getattr(model, self.region_id + '_windTransCost')[w,c]) 
                * getattr(model, self.region_id + '_windNew')[w,c]
                for (w,c) in wind_indices
                ) 

        elif hasattr(model, self.region_id + '_windCost'):
            
            wind_indices = [(w,c) for w in model.wrc for c in model.cc if (w,c) in getattr(model, self.region_id + '_windCost')]
            wind_cost_term = pyomo.quicksum(
                (getattr(model, self.region_id + '_windCost')[w,c]) * getattr(model, self.region_id + '_windNew')[w,c]
                for (w,c) in wind_indices
                ) 

        else:  

            wind_cost_term = 0

        return wind_cost_term

    def constraints(self, model):

        def wind_constraints(model, w, c): 

            if hasattr(model, self.region_id + '_windMax'):
                if (w,c) in getattr(model, self.region_id + '_windMax'): 
                    return getattr(model, self.region_id + '_windMax')[w,c] - getattr(model, self.region_id + '_windNew')[w,c] >= 0            
                else: 
                    return pyomo.Constraint.Skip
            else: 
                return pyomo.Constraint.Skip

        model.add_component(
            self.region_id + '_wind_install_limits', 
            pyomo.Constraint(model.wrc, model.cc, rule = wind_constraints)
        )

    def results(self, model, results): 

        results = {self.region_id: {}}
        
        capacity_dict = {}
        cost_dict ={}

        trans_var = getattr(model, self.region_id + '_windTransCost',0)

        if hasattr(model, self.region_id + '_windrNew'): 
            capacity_var = getattr(model, self.region_id + '_windNew').extract_values()
            
            for key, value in capacity_var.items(): 
                
                if key not in capacity_dict: 
                    capacity_dict[key] = {}

                else: 
                    capacity_dict[key] =  value
    

        if hasattr(model, self.region_id + '_windcost'): 
            cost_var = getattr(model, self.region_id + '_windcost').extract_values()
            trans_cost = trans_var.extract_values()

            for key, value in cost_var.items(): 

                if key not in capacity_dict: 
                    capacity_cost[key] = {}

                else: 
                    capacity_cost[key] +=  capacity_dict[key] * (value + trans_cost[key])

        results[self.region_id] = {
            'type': 'wind',
            'capacity': capacity_dict,
            'cost': cost_dict,
            }

        return results