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

        self.gencost = pyomo.Param(model.g, model.gf, initialize=self.gen_cost)
        setattr(model, self.region_id + '_gencost', self.gencost)

        self.genMax = pyomo.Param(model.g, model.gf, initialize=self.gen_capacity)
        setattr(model, self.region_id + '_genMax', self.genMax)

        return model

    def variables(self, model):
        
        self.generation = pyomo.Var(model.g, model.gf, model.t, within=pyomo.NonNegativeReals)
        setattr(model, self.region_id + '_generation', self.generation)

        return model

    def objective(self, model):
        gen_cost_term = pyomo.quicksum(
            getattr(model, self.region_id + '_generation')[g, gf, t] * getattr(model, self.region_id + '_gencost')[g][gf]
            for g in model.g
            for gf in model.gf 
            for t in model.t)
            
        return gen_cost_term

    def constraints(self, model):
        model.gen_limits_rule = pyomo.ConstraintList()
        constraint_expr = pyomo.quicksum(
            getattr(model, self.region_id + '_genMax')[g,gf] - getattr(model, self.region_id + '_generation')[g, gf, t]
            for g in model.g
            for gf in model.gf
            for t in model.t) >= 0
        model.gen_limits_rule.add(constraint_expr)

        return model
