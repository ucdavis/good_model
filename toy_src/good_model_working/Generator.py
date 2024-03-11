import pyomo.environ as pyomo

class Generator:
    def __init__(self, region_id, *generators):
        self.region_id = region_id
        self.gen_fuel_type = []
        self.generator_type = []
        self.gen_cost = {}
        self.gen_capacity = {}

        for data in generators:
            gen_id = data.get('plant_type', 0)
            self.generator_type.append(gen_id)

            values = data.get('parameters',{})
            self.gen_fuel_type += list(values.keys())

            for fuel_type, data in values.items(): 

                self.gen_cost[gen_id][fuel_type] = data.get('cost', 0) 
                self.gen_capacity[gen_id][fuel_type] = data.get('capacity')

    def parameters(self, model):
        model.c_gencost = pyomo.Param(model.g, model.gf, initialize=self.gen_cost)
        model.c_genMax = pyomo.Param(model.g, model.gf, initialize=self.gen_capacity)


    def variables(self, model):
        model.x_generation = pyomo.Var(model.gf, model.t, within=pyomo.NonNegativeReals)

    def objective(self, model):
        gen_cost_indices = [gf for gf in model.gf if gf in model.c_gencost]
        gen_cost_term = pyomo.quicksum(model.x_generation[gf, t] * model.c_gencost[gf] for gf in gen_cost_indices for t in model.t)
        return gen_cost_term

    def constraints(self, model):
        model.gen_limits_rule = pyomo.ConstraintList()
        constraint_expr = pyomo.quicksum(model.c_genMax[gf] - model.x_generation[gf, t] for gf in model.gf for t in model.t) >= 0
        model.gen_limits_rule.add(constraint_expr)
