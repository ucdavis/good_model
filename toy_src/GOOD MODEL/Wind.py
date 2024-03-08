import pyomo.environ as pyomo
import opt_model

class Wind:
    def __init__(self, region_id, **kwargs):
        self.region_id = region_id
        #wind_install_capacity
        self.installed_capacity = kwargs.get('installed_capacity', 0)
        self.gen_profile = kwargs.get('generation_profile', {})
        self.max_capacity = kwargs.get('max_capacity', {})
        self.cost = kwargs.get('cost', {})
        self.trans_cost = kwargs.get('transmission_cost', {})

    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_windprofile[w][t]
        ## tuple dictionary, ex: model.c_windprofile[w,t]
        model.c_windCap = pyomo.Param(initialize=self.installed_capacity)
        model.c_windprofile = pyomo.Param(region_id, model.wrc, model.t, initialize=self.gen_profile)
        model.c_windMax = pyomo.Param(region_id, model.wrc, model.cc, initialize=self.max_capacity)
        model.c_windCost = pyomo.Param(region_id, model.wrc, model.cc, initialize=self.cost)
        model.c_windTransCost = pyomo.Param(region_id, model.wrc, model.cc, initialize=self.trans_cost)

    def variables(self, model):
        # decision variables all indexed as, ex: model.x_windNew[w,c]
        model.x_windNew = pyomo.Var(region_id, model.wrc, model.cc, within=pyomo.NonNegativeReals)

    def objective(self, model):
        # Simplified objective function to correctly sum wind generation and transmission costs
        wind_cost_term = pyomo.quicksum(
            (model.x_windCost[r][w][c] + model.c_windTransCost[r][w][c]) * model.x_windNew[r,w,c]
            for r in region_id
            for w in model.wrc
            for c in model.cc
            ) 

    def constraints(self, model):
        # Corrected and simplified constraints definition
        model.wind_install_limits_rule = pyomo.ConstraintList()

        for w in model.wrc:
            for c in model.cc:
                constraint_expr = (model.c_windMax[r][w][c] - model.x_windnew[r,w,c]) >= 0
                model.wind_install_limits_rule.add(constraint_expr)
