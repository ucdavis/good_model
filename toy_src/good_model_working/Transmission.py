import pyomo.environ as pyomo
from .constants import transmission_efficiency


class Transmission:
    def __init__(self, source, target, **kwargs):
        self.source = source
        self.target = target
        self.trans_link = f'{self.source}_{self.target}'
        self.capacity = {self.source: {self.target: kwargs.get('capacity', 0)}}
        self.cost = {self.source: {self.target: kwargs.get('cost', 0)}}
        self.efficiency = transmission_efficiency
    
    # def parameters(self, model):

        self.transCost = pyomo.Param(self.source, self.target, initialize=self.cost)
        setattr(model, self.trans_link + '_cost', self.transCost)

        self.transCap = pyomo.Param(self.source, self.target, initialize=self.capacity)
        setattr(model, self.trans_link + '_cap', self.transCap)
       
        self.transEff = pyomo.Param(initialize=self.efficiency)
        setattr(model, self.trans_link + '_efficiency', self.transEff)

    def variables(self, model):
        # Assuming model.trans_links is a set of (source, target) tuples
        # Correct variable definition without using setattr incorrectly 

        self.trans_var = pyomo.Var(source, target, model.t, within=pyomo.NonNegativeReals)
        
        setattr(model, self.trans_link + '_trans', self.trans_var)

        return model

    def objective(self, model):
        # Simplify the objective function to accumulate transmission costs correctly

        transmission_cost_term = pyomo.quicksum(
            getattr(model, self.trans_link + '_trans')[r][o][t] * getattr(model, self.trans_link + '_cost')[r][o]
            for r in model.r
            for o in model.o
            for t in model.t)

        return transmission_cost_term

    def constraints(self, model):
        model.trans_limits_rule = pyomo.ConstraintList()

        for r in model.r: 
            for o in model.o: 
                for t in model.t:
                    constraint_expr = getattr(model, self.trans_link + '_transCap')[r][o] - getattr(model, self.trans_link + '_trans')[r,o,t] >= 0 

                    model.trans_limits_rule.add(constraint_expr)

        return model
