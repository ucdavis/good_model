import pyomo.environ as pyomo

class Generator:
    def __init__(self, region_id, *generators):
        self.region_id = region_id
        self.gen_fuel_type = []
        self.gen_cost = {}
        self.gen_capacity = {}

        for gen in generators:
            fuel_type = gen.get('type', 'default')
            values = gen.get('values', {})
            cost = values.get('cost', 0)
            capacity = values.get('capacity', 0)

            self.gen_fuel_type.append(fuel_type)
            self.gen_cost[fuel_type] = cost
            self.gen_capacity[fuel_type] = capacity

    def sets(self, model):
        model.gf = pyomo.Set(initialize=self.gen_fuel_type)

    def parameters(self, model):
        model.c_gencost = pyomo.Param(model.gf, initialize=self.gen_cost)
        model.c_genMax = pyomo.Param(model.gf, initialize=self.gen_capacity)


    def variables(self, model):
        model.x_generation = pyomo.Var(model.gf, model.t, within=pyomo.NonNegativeReals)

    def objective(self, model):
        gen_cost_indices = [gf for gf in model.gf if gf in model.c_gencost]
        self.gen_cost_term = pyomo.quicksum(model.x_generation[gf, t] * model.c_gencost[gf] for gf in gen_cost_indices for t in model.t)
        return self.gen_cost_term

    def constraints(self, model):
        model.gen_limits_rule = pyomo.ConstraintList()
        constraint_expr = pyomo.quicksum(model.c_genMax[gf] - model.x_generation[gf, t] for gf in model.gf for t in model.t) >= 0
        model.gen_limits_rule.add(constraint_expr)
