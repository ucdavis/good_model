import pyomo.environ as pyomo

class Wind:
    def __init__(self, region_id, **kwargs):
        self.region_id = region_id
        
        # Assuming `kwargs` contains keys for installed_capacity, cf, max_capacity, cost, trans_cost
        # Corrected the initialization from kwargs
        self.installed_capacity = kwargs.get('installed_capacity', 0)
        self.gen_profile = kwargs.get('generation_profile', 0)
        self.max_capacity = kwargs.get('max_capacity', {})
        self.cost = kwargs.get('cost', {})
        self.trans_cost = kwargs.get('trans_cost', {})

    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_windprofile[w][t]
        ## tuple dictionary, ex: model.c_windprofile[w,t]
        model.c_windCap = pyomo.Param(initialize=self.installed_capacity)
        model.c_windprofile = pyomo.Param(model.wrc, model.t, initialize=self.gen_profile)
        model.c_windMax = pyomo.Param(model.wrc, model.cc, initialize=self.max_capacity)
        model.c_windCost = pyomo.Param(model.wrc, model.cc, initialize=self.cost)
        model.c_windTransCost = pyomo.Param(model.wrc, model.cc, initialize=self.trans_cost)

    def variables(self, model):
        # decision variables all indexed as, ex: model.x_windNew[w,c]
        model.x_windNew = pyomo.Var(model.wrc, model.cc, within=pyomo.NonNegativeReals)

    def objective(self, model):
        # Simplified objective function to correctly sum wind generation and transmission costs
        wind_cost_term = pyomo.summation(model.c_windCost, model.x_windnew) + pyomo.summation(model.c_windTransCost, model.x_windnew)
        return wind_cost_term

    def constraints(self, model):
        # Corrected and simplified constraints definition
        model.wind_install_limits_rule = pyomo.ConstraintList()

        for w in model.wrc:
            for c in model.cc:
                if (w, c) in model.c_windMax:
                    constraint_expr = model.c_windMax[w][c] - model.x_windnew[w, c] >= 0
                    model.wind_install_limits_rule.add(constraint_expr)
