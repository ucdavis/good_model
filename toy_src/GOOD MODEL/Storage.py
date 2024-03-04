import pyomo.environ as pyomo
import utils

class Storage:
    def __init__(self, region_id, **kwargs):
        self.region_id = region_id
        # Correctly extract parameters from kwargs
        self.storage_capacity = kwargs.get('storage_capacity', 0)
        self.efficiency = utils.storage_efficiency
        self.cost = kwargs.get('cost', 0)
        self.storage_flow_limit = kwargs.get('storage_flow_limit', 0)

    def parameters(self, model):
        # Fixed incorrect self.model references and parameter initializations
        model.c_storCap = pyomo.Param(initialize=self.storage_capacity)
        model.c_storEff = pyomo.Param(initialize=self.efficiency)
        model.c_storCost = pyomo.Param(initialize=self.cost)
        model.c_storFlowCap = pyomo.Param(initialize=self.storage_flow_limit)

    def variables(self, model):
        # Correctly define variables without unnecessary setattr
        model.x_storSOC = pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        model.x_storCharge = pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        model.x_storDischarge = pyomo.Var(model.t, within=pyomo.NonNegativeReals)

    def constraints(self, model):
        # Max storage constraint
        model.maxStorage_rule = pyomo.ConstraintList()
        
        for t in model.t:
            model.maxStorage_rule.add(model.x_storSOC[t] <= model.c_storCap)

        # Storage state-of-charge constraint
        model.storageSOC_rule = pyomo.ConstraintList()
        
        for t in model.t:
            if t == min(model.t):  # Assuming model.t is an ordered set
                model.storageSOC_rule.add(model.x_storSOC[t] == 0)
            else:
                t_1 = t-1
                constraint_expr = (
                    model.x_storSOC[t] - model.x_storSOC[t_1] - model.x_storIn[t_1] * model.c_storEff + model.x_storOut[t_1]  
                ) == 0

                model.storageSOC_rule.add(constraint_expr)

        # Storage flow-in (charge)  constraints
        model.stor_flowIN_rule = pyomo.ConstraintList()
        
        constraint_expr = (pyomo.quicksum(model.c_storCap * model.c_storFlowCap - model.x_storIn[t] 
            for t in self.model.t) 
        ) >= 0 
        model.stor_flowIN_rule.add(constraint_expr)

        # Storage  flow-out (discharge) constraints
        model.stor_flowOUT_rule = pyomo.ConstraintList()
        
        constraint_expr = pyomo.quicksum(
            model.c_storCap * model.c_storFlowCap - model.x_storOut[t]
            for t in self.model.t
        ) >= 0
                
        model.stor_flowOUT_rule.add(constraint_expr)
