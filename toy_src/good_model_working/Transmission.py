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

        self.transCost = pyomo.Param(initialize=self.cost)
        setattr(model, self.trans_link + '_cost', self.transCost)

        self.transCap = pyomo.Param(initialize=self.capacity)
        setattr(model, self.trans_link + '_cap', self.transCap)
       
        self.transEff = pyomo.Param(initialize=self.efficiency)
        setattr(model, self.trans_link + '_efficiency', self.transEff)

        return model

    def variables(self, model):
        # Assuming model.trans_links is a set of (source, target) tuples
        # Correct variable definition without using setattr incorrectly 

        self.trans_var = pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        
        setattr(model, self.trans_link + '_trans', self.trans_var)

        return model

    def objective(self, model):
        # Simplify the objective function to accumulate transmission costs correctly

        tranmission_cost_term = 0

        transmission_cost_term = pyomo.quicksum(
            getattr(model, self.trans_link + '_trans')[t] * getattr(model, self.trans_link + '_cost')
            for t in model.t)

        return transmission_cost_term

    def constraints(self, model):
        
        model.trans_limits_rule = pyomo.ConstraintList()

        for t in model.t:
            constraint_expr = getattr(model, self.trans_link + '_transCap') - getattr(model, self.trans_link + '_trans')[t] >= 0 

            model.trans_limits_rule.add(constraint_expr)

        return model
