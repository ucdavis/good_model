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
        storSOC_rule = {}
        storCharge_rule = {}
        storDischarge_rule = {}

        for t in model.t:
            # Storage capacity constraint
            constraint_expr = (getattr(model, self.region_id + '_storCap') - getattr(model, self.region_id + '_storSOC')[t]) >= 0
            maxStorage_rule[t] = pyomo.Constraint(expr=constraint_expr)

            # Storage state-of-charge constraint
            if t == min(model.t):
                constraint_expr = getattr(model, self.region_id + '_storSOC')[t] == 0
                storSOC_rule[t] = pyomo.Constraint(expr=constraint_expr)
            else:
                t_1 = t - 1
                constraint_expr = (getattr(model, self.region_id + '_storSOC')[t] - getattr(model, self.region_id + '_storSOC')[t_1]
                    - getattr(model, self.region_id + '_storCharge')[t_1] * getattr(model, self.region_id + '_storEff')
                    + getattr(model, self.region_id + '_storDischarge')[t_1]
                    ) == 0
                
                storSOC_rule[t] = pyomo.Constraint(expr=constraint_expr)

            # Storage flow-in (charge) constraint
            constraint_expr = (getattr(model, self.region_id + '_storCap') * getattr(model, self.region_id + '_storFlowCap')
                - getattr(model, self.region_id + '_storCharge')[t]
                ) >= 0

            storCharge_rule[t] = pyomo.Constraint(expr=constraint_expr)
                
            # Storage flow-out (discharge) constraints
            constraint_expr = (getattr(model, self.region_id + '_storCap') * getattr(model, self.region_id + '_storFlowCap')
                - getattr(model, self.region_id + '_storDischarge')[t]
                ) >= 0

            storDischarge_rule[t] = pyomo.Constraint(expr=constraint_expr)

        setattr(model, self.region_id + '_storage_capacity_rule', maxStorage_rule)
        setattr(model, self.region_id + '_storage_SOC_rule', storSOC_rule)
        setattr(model, self.region_id + '_stor_discharge_rule', storDischarge_rule)
        setattr(model, self.region_id + '_stor_charge_rule', storCharge_rule)

        return model

