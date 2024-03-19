import pyomo.environ as pyomo

class Generator:
    def __init__(self, region_id, *generators):
        self.region_id = region_id
        self.gen_cost = {}
        self.gen_capacity = {}
        self.gen_cost[gen_id] = {}
        self.gen_capacity[gen_id] = {}

        for data in generators:

            gen_id = data.get('plant_type', 0)
            gen_type_data = data.get('generation',{})

            hold_cost = []
            hold_capacity = []
        
            for params in gen_type_data: 

                fuel_type = params.get('fuel_type', 0)
                values = params.get('values', {})
                cost = values.get('cost', 0)
                capacity = values.get('capacity', 0)

                    
    def parameters(self, model):

        self.gencost = pyomo.Param(model.g, model.gf, initialize=self.gen_cost, within=Reals)
        setattr(model, self.region_id + '_gencost', self.gencost)

        self.genMax = pyomo.Param(model.g, model.gf, initialize=self.gen_capacity, within=Reals)
        setattr(model, self.region_id + '_genMax', self.genMax)

        return model


    def variables(self, model):

        if hasattr(model, self.region_id + '_gencost'):
        
            self.generation = pyomo.Var(model.g, model.gf, model.t, within=pyomo.NonNegativeReals)
            setattr(model, self.region_id + '_generation', self.generation)

        return model

    def objective(self, model):

        gen_cost_term = 0

        gen_cost_term = pyomo.quicksum(
            getattr(model, self.region_id + '_generation')[g, gf, t] * getattr(model, self.region_id + '_gencost')[g][gf]
            for g in model.g
            for gf in model.gf 
            for t in model.t)
            
        return gen_cost_term

    def constraints(self, model):

        generator_constraints = {}

        for g in model.g: 
            gen_limits = {}

            for gf in model.gf: 
                gen_type_limits = {}

                for t in model.t: 
                    gen_limits_rule = pyomo.ConstraintList()
                    constraint_expr = (getattr(model, self.region_id + '_genMax')[g,gf] - getattr(model, self.region_id + '_generation')[g, gf, t]) >= 0 
                    gen_limits_rule.add(constraint_expr)
                    gen_type_limits[t] = gen_limits_rule

                gen_limits[gf] = gen_type_limits

            generator_constraints[g] = gen_limits

        setattr(model, self.region_id + '_gen_limits_rule', generator_constraints)

        return model
