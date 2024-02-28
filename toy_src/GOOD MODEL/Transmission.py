import pyomo.environ as pyomo

class Transmission:
    def __init__(self, source, target, **kwargs):
        self.source = source
        self.target = target
        self.link_id = f'{source}_{target}'
        self.capacity = kwargs.get('capacity', 1)
        self.cost = kwargs.get('cost', 1)
        self.efficiency = kwargs.get('efficiency', 1)

    def parameters(self, model):
        # Fixed parameter initialization to reference self attributes
        if not hasattr(model, 'c_transCost'):
            model.c_transCost = pyomo.Param(model.trans_links, initialize=lambda m, s, t: self.cost if (s, t) == (self.source, self.target) else 0, within=pyomo.Reals)
            model.c_transCap = pyomo.Param(model.trans_links, initialize=lambda m, s, t: self.capacity if (s, t) == (self.source, self.target) else 0, within=pyomo.Reals)
            model.c_transEff = pyomo.Param(model.trans_links, initialize=lambda m, s, t: self.efficiency if (s, t) == (self.source, self.target) else 1, within=pyomo.Reals)

    def variables(self, model):
        # Assuming model.trans_links is a set of (source, target) tuples
        # Correct variable definition without using setattr incorrectly
        if not hasattr(model, 'x_trans'):
            model.x_trans = pyomo.Var(model.trans_links, model.t, within=pyomo.NonNegativeReals)

    def objective(self, model):
        # Simplify the objective function to accumulate transmission costs correctly
        transmission_cost_term = sum(model.x_trans[s, t, time] * model.c_transCost[s, t] for s, t in model.trans_links for time in model.t)
        return transmission_cost_term

    def constraints(self, model):
        # Define transmission constraints properly
        if not hasattr(model, 'trans_limits_rule'):
            model.trans_limits_rule = pyomo.ConstraintList()

            for (s, t), time in model.x_trans.index_set():
                model.trans_limits_rule.add(model.x_trans[s, t, time] <= model.c_transCap[s, t])
