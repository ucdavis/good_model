import pyomo.environ as pyomo
from constants import transmission_efficiency


class Transmission:
    def __init__(self, source, target, **kwargs):
        self.source = source
        self.target = target
        self.trans_link = f'{self.source}_{self.target}'
        self.capacity = {self.source: {self.target: kwargs.get('capacity', 0)}}
        self.cost = {self.source: {self.target: kwargs.get('cost', 0)}}
        self.efficiency = transmission_efficiency
    
    # def parameters(self, model):

        # model.c_transCost = pyomo.Param(self.source, self.target, initialize=self.cost)
        # model.c_transCap = pyomo.Param(self.source, self.target, initialize=self.capacity)
        # model.c_transEff = pyomo.Param(initialize=self.efficiency)

    def variables(self, model):
        # Assuming model.trans_links is a set of (source, target) tuples
        # Correct variable definition without using setattr incorrectly

        self.var_name = f"x_trans_{self.trans_link}" 

        self.var = pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        
        setattr(model, self.var_name, self.var)

        return model

    def objective(self, model):
        # Simplify the objective function to accumulate transmission costs correctly
        transmission_cost_var = getattr(model, self.var_name)

        transmission_cost_term = (transmission_cost_var[t] for t in model.t)
        
        # pyomo.quicksum(model.x_trans[r,o,t] * model.c_transCost[r][o] 
        #     for r in self.source
        #     for o in self.target
        #     for t in model.t)
        return transmission_cost_term

    def constraints(self, model):
        model.trans_limits_rule = pyomo.ConstraintList()

        for r in self.source: 
            for o in self.target: 
                for t in opt_model.model.t:
                    constraint_expr = model.c_transCap[r,o] - model.x_trans[r,o,t] >= 0 

                    model.trans_limits_rule.add(constraint_expr)
