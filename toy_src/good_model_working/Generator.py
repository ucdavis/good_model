import pyomo.environ as pyomo

class Generator:
    def __init__(self, region_id, generators):
        self.region_id = region_id
        self.gen_cost = {}
        self.gen_capacity = {}
        self.fuel_type = []

        print("Generating", generators)

        for data in generators:
            for params in data.get('parameters',[]): 

                gen_id = params.get('plant_type', '')

                total_capacity = 0
                weighted_costs = {}

                for gen_params in params.get('generation', []): 
                    fuel = gen_params.get('fuel_type', '')
                    self.fuel_type.append(fuel)
                    values = gen_params.get('values', {})
                    capacity = values.get('capacity',0)
                    cost = values.get('cost',0)

                    gen_key = (gen_id, fuel)
                    if gen_key not in self.gen_capacity:
                        self.gen_capacity[gen_key] = 0
                        weighted_costs[gen_key] = 0

                    self.gen_capacity[gen_key] += capacity
                    total_capacity += capacity
                    weighted_costs[gen_key] += cost * capacity

                for gen_key, total_weighted_cost in weighted_costs.items():
                    if self.gen_capacity[gen_key] > 0:
                        self.gen_cost[gen_key] = total_weighted_cost / self.gen_capacity[gen_key]


    def parameters(self, model):

        # cost_keys = [key for key in self.gen_cost.keys()]
        # cap_keys = [key for key in self.gen_capacity.keys()]

        # if cost_keys not in model.g: 

        gencost = pyomo.Param(model.g_gf, initialize=self.gen_cost, within=pyomo.Reals)
        setattr(model, self.region_id + '_gencost', gencost)

        # if cap_keys not in model.g:

        genMax = pyomo.Param(model.g_gf, initialize=self.gen_capacity, within=pyomo.Reals)
        setattr(model, self.region_id + '_genMax', genMax)

        return model


    def variables(self, model):

        if hasattr(model, self.region_id + '_gencost'):
        
            self.generation = pyomo.Var(model.g_gf, model.t, within=pyomo.NonNegativeReals)
            setattr(model, self.region_id + '_generation', self.generation)

            print('gen_vars')
            print(self.region_id)

        return model

    def objective(self, model):

        gen_cost_term = 0

        if hasattr(model, self.region_id + '_generation'):

            gen_cost_term = pyomo.quicksum(
                getattr(model, self.region_id + '_generation')[g_gf,t] * getattr(model, self.region_id + '_gencost')[g_gf]
                for g_gf in model.g_gf
                for t in model.t)
            
        return gen_cost_term

    def constraints(self, model):

        if hasattr(model, self.region_id + '_generation'): 
            
            generator_constraints = {}

            for g_gf in model.g_gf:
                for t in model.t:  
                    gen_limits_rule = pyomo.ConstraintList()
                    constraint_expr = (
                        getattr(model, self.region_id + '_genMax')[g_gf] - getattr(model, self.region_id + '_generation')[g_gf, t]
                        >= 0 
                    )  

                    gen_limits_rule.add(constraint_expr)                   
                    generator_constraints.setdefault(g, {}).setdefault(gf, {})[t] = gen_limits_rule
                        
            setattr(model, self.region_id + '_gen_limits_rule', generator_constraints)

        return model

