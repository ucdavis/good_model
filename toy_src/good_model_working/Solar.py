import pyomo.environ as pyomo

class Solar:
    def __init__(self, region_id, *solar_data):
        
        self.region_id = region_id
        self.resource_id = []
        self.cost_class = []
        self.installed_capacity = {}
        self.gen_profile = {}
        self.max_capacity = {}
        self.cost = {}

        for data in solar_data:
            
            resource_id = str(data.get('Resource Class ', 0))
            self.resource_id.append(resource_id)
           
            # Assuming 'values' contains cost-related information
            values = data.get('values', {})
            self.cost_class += [str(key) for key in values.keys()]

            # Installed capacity and capacity factor for each resource
            self.installed_capacity[resource_id] = data.get('capacity', 0)
            self.gen_profile[resource_id] = data.get('generation_profile', {})

            # Max capacity and cost for each cost class
            for cost_class, info in values.items():
                self.max_capacity[resource_id][cost_class] = info.get('max_capacity', None)
                self.cost[resource_id][cost_class] = info.get('cost', None)

        self.param_list = [self.gen_profile, self.max_capacity, self.cost]

    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_solarprofile[s][t]
        ## tuple dictionary, ex: model.c_solarprofile[s,t]
        
        if all(self.param_list):
            
            self.solarCap = pyomo.Param(model.src, initialize=self.installed_capacity, within=pyomo.Reals)
            setattr(model, self.region_id + '_solarCap', self.solarCap)

            self.solarprofile = pyomo.Param(model.src, model.t, initialize=self.gen_profile, within=pyomo.Reals)
            setattr(model, self.region_id + '_solarprofile', self.solarprofile)

            self.solarMax = pyomo.Param(model.src, model.cc, initialize=self.max_capacity, within=pyomo.Reals)
            setattr(model, self.region_id + '_solarMax', self.solarMax)

            self.solarCost = pyomo.Param(model.src, model.cc, initialize=self.cost, within=pyomo.Reals)
            setattr(model, self.region_id + '_solarCost', self.solarCost)

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