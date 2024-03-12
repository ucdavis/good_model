import pyomo.environ as pyomo

class Wind:
    def __init__(self, region_id, *kwargs):
        self.region_id = region_id
        #wind_install_capacity

        ## TO DO: 
        ## need to fix data handling from RegionNode to modules
        self.data = kwargs
        
        for i in self.data: 
            
            max_capacity_dict = i.get('max_capacity', {})
            

            if max_capacity_dict:
                self.max_capacity = next(iter(max_capacity_dict.values()))
            else:
                self.max_capacity = 0

                print(self.max_capacity)

        self.installed_capacity = kwargs.get('installed_capacity', 0)
        self.gen_profile = kwargs.get('generation_profile', {})
        
        self.cost = kwargs.get('cost', {})
        self.trans_cost = kwargs.get('transmission_cost', {})

        print(self.cost)

    def parameters(self, model):
        # parameters are indexed based on the data structure passed via initialize
        # if the data is: 
        ## nested dictionary, ex: model.c_windprofile[w][t]
        ## tuple dictionary, ex: model.c_windprofile[w,t]
        
        windCap = pyomo.Param(initialize=self.installed_capacity)
        setattr(model, self.region_id + '_windCap', windCap)

        windgenprofile = pyomo.Param(region_id, model.wrc, model.t, initialize=self.gen_profile)
        setattr(model, self.region_id + '_windgenprofile', windgenprofile)

        windmax = pyomo.Param(region_id, model.wrc, model.cc, initialize=self.max_capacity)
        setattr(model, self.region_id + '_windMax', windmax)

        windCost = pyomo.Param(region_id, model.wrc, model.cc, initialize=self.cost)
        setattr(model, self.region_id + '_windCost', windCost)

        windTransCost = pyomo.Param(region_id, model.wrc, model.cc, initialize=self.trans_cost)
        setattr(model, self.region_id + '_windTransCost', windTransCost)

        return model

    def variables(self, model):
        # decision variables all indexed as, ex: model.x_windNew[w,c]

        windNew = pyomo.Var(region_id, model.wrc, model.cc, within=pyomo.NonNegativeReals)
        setattr(model, self.region_id + '_windNew', windNew)

        return model

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
                constraint_expr = (getattr(model, self.region_id + '_windMax')[r][w][c] - getattr(model, self.region_id + '_windNew')[r,w,c]) >= 0
                model.wind_install_limits_rule.add(constraint_expr)

        return model
