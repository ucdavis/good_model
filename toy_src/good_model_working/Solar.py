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
            resource_id = data.get('id', 0)
            self.resource_id.append(resource_id)

            # Assuming 'values' contains cost-related information
            values = data.get('values', {})
            self.cost_class += list(values.keys())

            # Installed capacity and capacity factor for each resource
            self.installed_capacity[resource_id] = data.get('capacity', 0)
            self.gen_profile[resource_id] = data.get('generation_profile', {})

            # Max capacity and cost for each cost class
            for cost_class, info in values.items():
                self.max_capacity[resource_id][cost_class] = info.get('max_capacity', 0)
                self.cost[resource_id][cost_class] = info.get('cost', 0)

        # Removing duplicate entries in cost_class list if any
        self.cost_class = list(set(self.cost_class))

    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_solarprofile[s][t]
        ## tuple dictionary, ex: model.c_solarprofile[s,t]
        self.solarCap = pyomo.Param(self.region_id, model.src, initialize=self.installed_capacity)
        setattr(model, self.region_id + '_solarCap', self.solarCap)

        self.solarprofile = pyomo.Param(self.region_id, model.src, model.t, initialize=self.gen_profile)
        setattr(model, self.region_id + '_solarprofile', self.solarprofile)

        self.solarMax = pyomo.Param(self.region_id, model.src, model.cc, initialize=self.max_capacity)
        setattr(model, self.region_id + '_solarMax', self.solarMax)

        self.solarCost = pyomo.Param(self.region_id, model.src, model.cc, initialize=self.cost)
        setattr(model, self.region_id + '_solarCost', self.solarCost)


    def variables(self, model):
        # decision variables all indexed as, ex: model.x_solarNew[s,c]
        self.solarNew = pyomo.Var(self.region_id, model.src, model.cc, within=pyomo.NonNegativeReals)
        setattr(model, self.region_id + '_solarNew', self.solarNew)

        return model

    def objective(self, model):
        # Simplify the construction of the objective function
        solar_cost_term = pyomo.quicksum(
            getattr(model, self.region_id + '_solarCost')[r][s][c] * getattr(model, self.region_id + '_solarNew')[r, s, c] 
            for r in model.r
            for s in model.src 
            for c in model.cc) 
            
        return solar_cost_term

    def constraints(self, model):
        model.solar_install_limits_rule = pyomo.ConstraintList()

        for r in model.r:
            for s in model.src: 
                for c in model.cc: 
                    constraint_expr = getattr(model, self.region_id + '_solarMax')[r][s][c] - getattr(model, self.region_id + '_solarNew')[r, s, c] >= 0
                    model.solar_install_limits_rule.add(constraint_expr)
        
        return model

    
