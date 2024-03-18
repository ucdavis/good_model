import pyomo.environ as pyomo
from .constants import storage_efficiency
from .constants import storage_flow_limit

class Storage:
    def __init__(self, region_id, *kwargs):
        self.region_id = region_id
        self.storage_data = kwargs

        for data in self.storage_data: 

            self.storage_capacity = data.get('capacity', 0)
            self.efficiency = storage_efficiency
            self.cost = data.get('cost', 0)
            self.storage_flow_limit = storage_flow_limit

    def parameters(self, model):

        self.storCap = pyomo.Param(initialize=self.storage_capacity)
        setattr(model, self.region_id + '_storCap', self.storCap)

        self.storEff = pyomo.Param(initialize=self.efficiency)
        setattr(model, self.region_id + '_storEff', self.storEff)

        self.storCost = pyomo.Param(self.region_id, initialize=self.cost)
        setattr(model, self.region_id + '_storCost', self.storCost)

        self.storFlowCap = pyomo.Param(initialize=self.storage_flow_limit)
        setattr(model, self.region_id + '_storFlowCap', self.storFlowCap)


    def variables(self, model):

        self.storSOC = pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        setattr(model, self.region_id + '_storSOC', self.storSOC)

        self.storCharge = pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        setattr(model, self.region_id + '_storCharge', self.storCharge)

        self.storDischarge = pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        setattr(model, self.region_id + '_storDischarge', self.storDischarge)

        return model

    def objective(self, model): 

        return 0 
   
    def constraints(self, model):

        maxStorage_rule = {}

        for t in model.t:
            expr = getattr(model, self.region_id + '_storCap') - getattr(model, self.region_id + '_storSOC')[t] >= 0

            maxStorage_rule[t] = pyomo.Constraint(expr=expr)

        setattr(model, self.region_id + '_wind_install_limits', wind_constraints)

        # Storage state-of-charge constraint
        model.storageSOC_rule = pyomo.ConstraintList()
        
        for t in model.t:
            if t == min(model.t):  
                model.storageSOC_rule.add(getattr(model, self.region_id + '_storSOC')[t] == 0)
            else:
                t_1 = t-1
                constraint_expr = (
                    getattr(model, self.region_id + '_storSOC')[t] - getattr(model, self.region_id + '_storSOC')[t_1] 
                    - getattr(model, self.region_id + '_storCharge')[t_1] * getattr(model, self.region_id + '_storEff') + getattr(model, self.region_id + '_storDischarge')[t_1]  
                ) == 0

                model.storageSOC_rule.add(constraint_expr)

        # Storage flow-in (charge)  constraints
        model.stor_flowIN_rule = pyomo.ConstraintList()
        
        constraint_expr = (pyomo.quicksum(
            getattr(model, self.region_id + '_storCap') * getattr(model, self.region_id + '_storFlowCap') 
            - getattr(model, self.region_id + '_storCharge')[t] 
            for t in model.t) 
        ) >= 0 
        model.stor_flowIN_rule.add(constraint_expr)

        # Storage  flow-out (discharge) constraints
        model.stor_flowOUT_rule = pyomo.ConstraintList()
        
        constraint_expr = pyomo.quicksum(
            getattr(model, self.region_id + '_storCap') * getattr(model, self.region_id + '_storFlowCap') 
            - getattr(model, self.region_id + '_storDischarge')[t]
            for t in model.t
        ) >= 0
                
        model.stor_flowOUT_rule.add(constraint_expr)

        return model
