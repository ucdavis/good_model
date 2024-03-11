import pyomo.environ as pyomo
import constants
import opt_model

class Storage:
    def __init__(self, region_id, **kwargs):
        self.region_id = region_id
        self.storage_capacity = kwargs.get('capacity', 0)
        self.efficiency = constants.storage_efficiency
        self.cost = kwargs.get('cost', 0)
        self.storage_flow_limit = utils.storage_flow_limit

    def parameters(self, model):
        model.c_storCap = pyomo.Param(initialize=self.storage_capacity)
        model.c_storEff = pyomo.Param(initialize=self.efficiency)
        model.c_storCost = pyomo.Param(initialize=self.cost)
        model.c_storFlowCap = pyomo.Param(initialize=self.storage_flow_limit)

    def variables(self, model):
        # Correctly define variables without unnecessary setattr
        model.x_storSOC = pyomo.Var(region_id, opt_model.model.t, within=pyomo.NonNegativeReals)
        model.x_storCharge = pyomo.Var(region_id, opt_model.model.t, within=pyomo.NonNegativeReals)
        model.x_storDischarge = pyomo.Var(region_id, opt_model.model.t, within=pyomo.NonNegativeReals)

    def objective(self, model): 
        pass 
   
    def constraints(self, model):
        # Max storage constraint
        model.maxStorage_rule = pyomo.ConstraintList()
        
        for r in region_id: 
            for t in opt_model.model.t:
                model.maxStorage_rule.add(model.c_storCap[r] - model.x_storSOC[r][t] >= 0 )

        # Storage state-of-charge constraint
        model.storageSOC_rule = pyomo.ConstraintList()
        
        for r in region_id:
            for t in opt_model.model.t:
                if t == min(model.t):  # Assuming model.t is an ordered set
                    model.storageSOC_rule.add(model.x_storSOC[r][t] == 0)
                else:
                    t_1 = t-1
                    constraint_expr = (
                        model.x_storSOC[r][t] - model.x_storSOC[r][t_1] - model.x_storIn[r][t_1] * model.c_storEff + model.x_storOut[r][t_1]  
                    ) == 0

                    model.storageSOC_rule.add(constraint_expr)

        # Storage flow-in (charge)  constraints
        model.stor_flowIN_rule = pyomo.ConstraintList()
        
        constraint_expr = (pyomo.quicksum(
            model.c_storCap[r] * model.c_storFlowCap - model.x_storIn[r][t] 
            for r in region_id
            for t in self.model.t) 
        ) >= 0 
        model.stor_flowIN_rule.add(constraint_expr)

        # Storage  flow-out (discharge) constraints
        model.stor_flowOUT_rule = pyomo.ConstraintList()
        
        constraint_expr = pyomo.quicksum(
            model.c_storCap * model.c_storFlowCap - model.x_storOut[r][t]
            for r in region_id
            for t in self.model.t
        ) >= 0
                
        model.stor_flowOUT_rule.add(constraint_expr)
