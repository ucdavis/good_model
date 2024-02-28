import pyomo.environ as pyomo

class Storage:
    def __init__(self, region_id, **kwargs):
        self.region_id = region_id
        # Correctly extract parameters from kwargs
        self.storage_capacity = kwargs.get('storage_capacity', 0)
        self.efficiency = kwargs.get('efficiency', 0)
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
        # Corrected and simplified constraint definitions
        model.maxStorage_rule = pyomo.ConstraintList()
        model.storageSOC_rule = pyomo.ConstraintList()
        model.stor_flowIN_rule = pyomo.ConstraintList()
        model.stor_flowOUT_rule = pyomo.ConstraintList()

        # Max storage constraint
        for t in model.t:
            model.maxStorage_rule.add(model.x_storSOC[t] <= model.c_storCap)

        # Storage state-of-charge constraint
        for t in model.t:
            if t == model.t.first():  # Assuming model.t is an ordered set
                model.storageSOC_rule.add(model.x_storSOC[t] == 0)
            else:
                prev_t = model.t.prev(t)
                model.storageSOC_rule.add(
                    model.x_storSOC[t] == model.x_storSOC[prev_t] + model.x_storCharge[prev_t] * model.c_storEff - model.x_storDischarge[prev_t]
                )

        # Storage flow-in (charge) and flow-out (discharge) constraints
        for t in model.t:
            model.stor_flowIN_rule.add(model.x_storCharge[t] <= model.c_storFlowCap)
            model.stor_flowOUT_rule.add(model.x_storDischarge[t] <= model.c_storFlowCap)
