import pyomo.environ as pyomo
import utils
import opt_model

class Transmission:
    def __init__(self, source, target, **kwargs):
        self.source = source
        self.target = target
        self.capacity = {source: {target: kwargs.get('capacity', 1)}}
        self.cost = {source: {target: kwargs.get('cost', 1)}}
        self.efficiency = utils.transmission_efficiency

    def sets(self, model):
        pass
    
    def parameters(self, model):

        model.c_transCost = pyomo.Param(source, target, model.t, initialize=self.cost)
        model.c_transCap = pyomo.Param(source, target, model.t, initialize=self.capacity)
        model.c_transEff = pyomo.Param(initialize=self.efficiency)

    def variables(self, model):
        # Assuming model.trans_links is a set of (source, target) tuples
        # Correct variable definition without using setattr incorrectly
        model.x_trans = pyomo.Var(source, target, model.t, within=pyomo.NonNegativeReals)

    def objective(self, model):
        # Simplify the objective function to accumulate transmission costs correctly
        transmission_cost_term = pyomo.quicksum(model.x_trans[r,o,t] * model.c_transCost[r][o][t] 
            for r in source
            for o in target
            for t in model.t)
        return transmission_cost_term

    def constraints(self, model):
        model.trans_limits_rule = pyomo.ConstraintList()

        for r in source: 
            for o in target: 
                for t in opt_model.model.t:
                    constraint_expr = model.c_transCap[r,o,t] - model.x_trans[r,o,t] >= 0 

                    model.trans_limits_rule.add(constraint_expr)
