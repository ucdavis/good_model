import pyomo.environ as pyomo

class Wind:
    def __init__(self, region_id, wind_data):
        self.region_id = region_id
        self.installed_capacity = 0
        self.gen_profile = {}
        self.max_capacity = {}
        self.cost = {}
        self.transmission_cost = {}

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
                    values = params.get('generation_profile', {})
                    
                    if values: 
                        for hour, load in values.items():
                            index_key = (resource_id, int(hour))
                            self.gen_profile[index_key] = load
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

    
    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_windprofile[w][t]
        ## tuple dictionary, ex: model.c_windprofile[w,t]

        if self.installed_capacity:
            model.add_component(
                self.region_id + '_windCap',
                pyomo.Param(initialize=self.installed_capacity)
            )
 
        if self.max_capacity: 
            model.add_component(
                self.region_id + '_windMax',
                pyomo.Param(model.wrc, model.cc, initialize=self.max_capacity)
            )
        
        if self.cost: 
            model.add_component(
                self.region_id + '_windCost',
                pyomo.Param(model.wrc, model.cc, initialize=self.cost)
            )
  
        if self.transmission_cost: 
            model.add_component(
                self.region_id + '_windTransCost',
                pyomo.Param(model.wrc, model.cc, initialize=self.transmission_cost)
            )

        if self.gen_profile: 
            model.add_component(
                self.region_id + '_windGenProfile',
                pyomo.Param(model.wrc, model.t, initialize= self.gen_profile)
            )

            
    def variables(self, model):
        # decision variables all indexed as, ex: model.x_windNew[w,c]

        model.add_component(
            self.region_id + '_windNew', 
            pyomo.Var(model.wrc, model.cc, within=pyomo.NonNegativeReals, bounds= (None, None))
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

