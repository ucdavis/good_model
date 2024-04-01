import pyomo.environ as pyomo
from .constants import storage_efficiency
from .constants import storage_flow_limit

class Storage:
    def __init__(self, region_id, kwargs):
        self.region_id = region_id
        self.storage_data = kwargs

        for data in self.storage_data: 

            self.storage_capacity = data.get('capacity', 0)
            self.efficiency = storage_efficiency
            self.cost = data.get('cost', 0)
            self.storage_flow_limit = storage_flow_limit


    def parameters(self, model):

        model.add_component(
            self.region_id + '_storCap',
            pyomo.Param(initialize=self.storage_capacity)
        )

        model.add_component(
            self.region_id + '_storEff',
            pyomo.Param(initialize=self.efficiency)
        )
     
        model.add_component(
            self.region_id + '_storCost',
            pyomo.Param(self.region_id, initialize=self.cost)
        )
 
        model.add_component(
            self.region_id + '_storFlowCap',
            pyomo.Param(initialize=self.storage_flow_limit)
        )


    def variables(self, model):

        model.add_component(
            self.region_id + '_storSOC',
            pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        )

        model.add_component(
            self.region_id + '_storCharge',
            pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        )
        
        model.add_component(
            self.region_id + '_storDischarge', 
            pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        )


    def objective(self, model): 

        return 0 
   

    def constraints(self, model):

        def maxStorage_rule(model, t): 
            return getattr(model, self.region_id + '_storCap') - getattr(model, self.region_id + '_storSOC')[t] >= 0

        model.add_component(
            self.region_id + '_storage_capacity_rule', 
            pyomo.Constraint(model.t, rule=maxStorage_rule)
        )
        
        def storSOC_rule(model, t): 
            if t == min(model.t):
               return getattr(model, self.region_id + '_storSOC')[t] == 0
        
            else:
                t_1 = t - 1
                return (getattr(model, self.region_id + '_storSOC')[t] - getattr(model, self.region_id + '_storSOC')[t_1] - getattr(model, self.region_id + '_storCharge')[t_1] * getattr(model, self.region_id + '_storEff')
                    + getattr(model, self.region_id + '_storDischarge')[t_1]
                    == 0
                )   

        model.add_component(
            self.region_id + '_storage_SOC_rule',
            pyomo.Constraint(model.t, rule=storSOC_rule)
        )
        

        def storCharge_rule(model, t): 
            return (getattr(model, self.region_id + '_storCap') * getattr(model, self.region_id + '_storFlowCap')
                - getattr(model, self.region_id + '_storCharge')[t]
                >= 0
            )

        model.add_component(
            self.region_id + '_stor_charge_rule', 
            pyomo.Constraint(model.t, rule=storCharge_rule)
        )

        def storDischarge_rule(model, t): 
            return (getattr(model, self.region_id + '_storCap') * getattr(model, self.region_id + '_storFlowCap')
                - getattr(model, self.region_id + '_storDischarge')[t]
                >= 0
            )

        model.add_component(
            self.region_id + '_stor_discharge_rule',
            pyomo.Constraint(model.t, rule=storDischarge_rule)
        )
        

