import pyomo.environ as pyomo
from .constants import transmission_efficiency


class Transmission:
    def __init__(self, source, target, **kwargs):
        self.source = source
        self.target = target
        self.trans_link = f'{self.source}_{self.target}'
        self.capacity = kwargs.get('capacity', 0)
        self.cost = kwargs.get('cost', 0)
        self.efficiency = transmission_efficiency
    
    def parameters(self, model):

        model.add_component( 
            self.trans_link + '_transCost', 
            pyomo.Param(initialize=self.cost, within=pyomo.NonNegativeReals)
        )

        model.add_component(
            self.trans_link + '_transCap', 
            pyomo.Param(initialize=self.capacity, within=pyomo.NonNegativeReals)
        ) 
       
        model.add_component(
            self.trans_link + '_efficiency', 
            pyomo.Param(initialize=self.efficiency, within=pyomo.NonNegativeReals)
        )

    def variables(self, model):

        model.add_component(
             self.trans_link + '_trans',
             pyomo.Var(model.t, domain=pyomo.NonNegativeReals)
        )

    def objective(self, model):
        # Simplify the objective function to accumulate transmission costs correctly

        tranmission_cost_term = 0

        transmission_cost_term = pyomo.quicksum(
            getattr(model, self.trans_link + '_trans')[t] * getattr(model, self.trans_link + '_transCost')
            for t in model.t)

        return transmission_cost_term

    def constraints(self, model):
        
        def transmission_constraints(model, t): 
            return getattr(model, self.trans_link + '_transCap') - getattr(model, self.trans_link + '_trans')[t] >= 0
        
        model.add_component(
            self.trans_link + '_trans_limit_rule',
            pyomo.Constraint(model.t, rule=transmission_constraints)
        )
