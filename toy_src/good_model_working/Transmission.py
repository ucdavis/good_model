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
        setattr(model, self.trans_link + '_transCost', self.transCost)

        self.transCap = pyomo.Param(initialize=self.capacity)
        setattr(model, self.trans_link + '_transCap', self.transCap)
       
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

        if hasattr(model, self.trans_link + '_trans'):

            transmission_cost_term = pyomo.quicksum(
                getattr(model, self.trans_link + '_trans')[t] * getattr(model, self.trans_link + '_transCost')
                for t in model.t)

        return transmission_cost_term

    def constraints(self, model):
        
        transmission_constraints = {}
        
        for t in model.t:
            trans_limits_rule = pyomo.ConstraintList()
            constraint_expr = (
                getattr(model, self.trans_link + '_transCap') - getattr(model, self.trans_link + '_trans')[t] 
                >= 0
            ) 
            trans_limits_rule.add(constraint_expr)
            transmission_constraints.setdefault(t, trans_limits_rule)

        setattr(model, self.trans_link + '_trans_limit_rule', transmission_constraints)

        return model
