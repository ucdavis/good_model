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

            data_type = data.get('data_tye', 0)
            parameters = data.get('parameters', [])

            if data_type == 'wind_cost': 

                for params in parameters: 
                    resource_id = str(params.get('resource_class', 0))
                    values = params.get('cost', {})

                    for cost_class, info in values.items():
                        index = (resource_id, cost_class)
                        self.cost[index] = info

            elif data_type == 'wind_max_capacity': 
                
                for params in parameters: 
                    
                    resource_id = str(params.get('resource_class', 0))
                    values = params.get('max_capacity', {})

                    for cost_class, info in values.items():
                        index = (resource_id, cost_class)
                        self.max_capacity[index] = info
                    

            elif data_type == 'wind_installed_capacity': 
                
                for params in parameters: 
                    self.installed_capacity = params.get('capacity', 0)
 
            elif data_type == 'wind_gen':
                
                for params in parameters:
                    resource_id = str(params.get('resource_class', 0))
                    self.gen_profile[resource_id] = params.get('generation_profile', {})

            elif data_type == 'wind_transmission_cost': 
                
                for params in parameters: 
                    resource_id = str(params.get('resource_class', 0))
                    values = params.get('transmission_cost', 0)

                    for cost_class, info in values.items():
                        index = (resource_id, cost_class)
                        self.transmission_cost[index] = info
    

    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_windprofile[w][t]
        ## tuple dictionary, ex: model.c_windprofile[w,t]

        model.add_component(
            self.region_id + '_windCap', 
            pyomo.Param(initialize=self.installed_capacity, within=pyomo.Reals)
        )

        model.add_component(
            self.region_id + '_windgenprofile', 
            pyomo.Param(model.wrc, model.t, initialize= self.gen_profile, within=pyomo.Reals)
        )
      
        model.add_component(
            self.region_id + '_windMax', 
            pyomo.Param(model.wrc, model.cc, initialize=self.max_capacity, within=pyomo.Reals)
        )

        model.add_component(
            self.region_id + '_windCost',
            pyomo.Param(model.wrc, model.cc, initialize=self.cost, within=pyomo.Reals)
        )
    
        model.add_component( 
            self.region_id + '_windTransCost',
            pyomo.Param(model.wrc, model.cc, initialize=self.transmission_cost, within=pyomo.Reals)
        )

        return model

    def variables(self, model):
        # decision variables all indexed as, ex: model.x_windNew[w,c]

        if hasattr(model, self.region_id + '_windCost'):

            windNew = pyomo.Var(model.wrc, model.cc, within=pyomo.NonNegativeReals)
            setattr(model, self.region_id + '_windNew', windNew)

            print('wind_vars')

        return model

    def objective(self, model):
        # Simplified objective function to correctly sum wind generation and transmission costs
        
        wind_cost_term = 0 

        if hasattr(model, self.region_id + '_windNew'):

            wind_cost_term = pyomo.quicksum(
                (getattr(model, self.region_id + '_windCost')[w,c] + getattr(model, self.region_id + '_windTransCost')[w][c]) * getattr(model, self.region_id + '_windNew')[w,c]
                for w in model.wrc
                for c in model.cc
                if (w, c) in getattr(model, self.region_id + '_windCost')
                ) 
        
        return wind_cost_term

    def constraints(self, model):
    
        wind_constraints = {}  
        wind_install_limits_rule = pyomo.ConstraintList()
        
        for w in model.wrc:
            for c in model.cc:
                if hasattr(model, self.region_id + '_windMax') and \
                            hasattr(model, self.region_id + '_windNew'):
                    constraint_expr = (
                        getattr(model, self.region_id + '_windMax')[w,c] - 
                        getattr(model, self.region_id + '_windNew')[w, c] >= 0
                    )
                    wind_install_limits_rule.add(constraint_expr)
                    wind_constraints.setdefault(w, {})[c] = wind_install_limits_rule
                else:
                    constraint_expr = pyomo.Constraint.Skip()
                    wind_install_limits_rule.add(constraint_expr)
                    wind_constraints.setdefault(w, {})[c] = wind_install_limits_rule
                
                        
        setattr(model, self.region_id + '_wind_install_limits', wind_constraints)

        return model
