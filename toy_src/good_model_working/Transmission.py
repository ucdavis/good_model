import pyomo.environ as pyomo
from .constants import transmission_efficiency


class Transmission:
    def __init__(self, model, source, target, **kwargs):
        self.source = source
        self.target = target
        self.model = model
        self.trans_link = f'{self.source}_{self.target}'
        self.capacity = kwargs.get('capacity', 0)
        self.cost = kwargs.get('cost', 0)
        self.efficiency = transmission_efficiency
    
    def parameters(self):

        self.transCost = pyomo.Param(initialize=self.cost)
        setattr(self.model, self.trans_link + '_cost', self.transCost)

        self.transCap = pyomo.Param(initialize=self.capacity)
        setattr(self.model, self.trans_link + '_cap', self.transCap)
       
        self.transEff = pyomo.Param(initialize=self.efficiency)
        setattr(self.model, self.trans_link + '_efficiency', self.transEff)

    def variables(self):
        # Assuming model.trans_links is a set of (source, target) tuples
        # Correct variable definition without using setattr incorrectly 

        self.trans_var = pyomo.Var(self.model.t, within=pyomo.NonNegativeReals)
        
        setattr(self.model, self.trans_link + '_trans', self.trans_var)

        return self.model

    def objective(self):
        print("Here in transmission objective")
        # Correct summation using sum() and appropriate attribute access
        transmission_cost_term = sum(
            getattr(self.model, self.trans_link + '_trans')[t] * getattr(self.model, self.trans_link + '_cost')
            for t in self.model.t
        )

        return transmission_cost_term


    def constraints(self):
        self.model.trans_limits_rule = pyomo.ConstraintList()

        for t in self.model.t:
            constraint_expr = getattr(self.model, self.trans_link + '_transCap') - getattr(self.model, self.trans_link + '_trans')[t] >= 0 

            self.model.trans_limits_rule.add(constraint_expr)

        return self.model
