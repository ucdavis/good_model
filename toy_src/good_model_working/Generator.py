import pyomo.environ as pyomo

class Generator:
    def __init__(self, region_id, generators):
        self.region_id = region_id
        self.gen_cost = {}
        self.gen_capacity = {}
        self.gen_type = []
        self.fuel_type = []

        for data in generators:

            gen_type_data = data.get('parameters',[])

            for params in gen_type_data: 

                gen_id = params.get('plant_type', 0)
                gen_data = params.get('generation', [])

                total_capacity = 0
                total_cost = 0
                hold_capacity = []
                hold_cost = []
                wt_capacity = []

                for gen_params in gen_data: 

                    fuel_type = gen_params.get('fuel_type', 0)
                    self.fuel_type.append(fuel_type)
                    values = gen_params.get('values', {})

                    gen_key = (gen_id, fuel_type)
                    if gen_key not in self.gen_capacity.keys():
                        self.gen_capacity[gen_key]= (values.get('capacity', 0))
                    else: 
                        self.gen_capacity[gen_key] += (values.get('capacity', 0))
                    
                    hold_capacity.append(values.get('capacity', 0))
                    total_capacity += values.get('capacity',0)
                    hold_cost.append(values.get('cost', 0))

                for (gen, fuel), value in self.gen_capacity.items(): 
                    wt_capacity.append(value/ total_capacity)

                for i in range(len(hold_capacity)):
                    wt_cost = wt_capacity[i] * hold_cost[i]
                    total_cost += wt_cost
                    fuel_key = (gen_id, self.fuel_type[i])
                    if not fuel_key in self.gen_cost.keys():
                        self.gen_cost[fuel_key] = total_cost
                    else: 
                        continue

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

