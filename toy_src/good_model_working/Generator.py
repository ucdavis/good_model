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

            total_capacity = 0
            total_cost = 0
            hold_capacity = []
            hold_cost = []
            wt_capacity = []

            for params in gen_type_data: 

                gen_id = params.get('gen_type', 0)
                gen_data = params.get('values', {})

                hold_capacity.append(gen_data.get('capacity', 0))
                total_capacity += gen_data.get('capacity',0)
                hold_cost.append(gen_data.get('cost', 0))

                if gen_id not in self.gen_capacity.keys():
                    self.gen_capacity[gen_id]= (gen_data.get('capacity', 0))
                else: 
                    self.gen_capacity[gen_id] += (gen_data.get('capacity', 0))
                    
                for gen_id, value in self.gen_capacity.items(): 
                    wt_capacity.append(value/ total_capacity)

                for i in range(len(hold_capacity)):
                    wt_cost = wt_capacity[i] * hold_cost[i]
                    total_cost += wt_cost
                    if not gen_id in self.gen_cost.keys():
                        self.gen_cost[gen_id] = total_cost
                    else: 
                        continue

    def parameters(self, model):

        model.add_component(
            self.region_id + '_gencost', 
            pyomo.Param(model.gen, initialize=self.gen_cost, within=pyomo.Reals)
        )

        model.add_component(
            self.region_id + '_genMax', 
            pyomo.Param(model.gen, initialize=self.gen_capacity, within=pyomo.Reals)
        )

    def variables(self, model):

        model.add_component(
            self.region_id + '_generation',
            pyomo.Var(model.gen, model.t, domain=pyomo.NonNegativeReals)
        )

    def objective(self, model):

        gen_cost_term = 0

        gen_indices = [g for g in model.gen if g in getattr(model, self.region_id + '_gencost')]

        gen_cost_term = pyomo.quicksum(
            getattr(model, self.region_id + '_generation')[g,t] * getattr(model, self.region_id + '_gencost')[g]
            for g in gen_indices
            for t in model.t)
            
        return gen_cost_term

    def constraints(self, model):
            
        def generator_constraints(model, g, t): 
            if g in getattr(model, self.region_id + '_genMax'): 
                return getattr(model, self.region_id + '_genMax')[g] - getattr(model, self.region_id + '_generation')[g, t] >= 0 
            else: 
                return pyomo.Constraint.Skip
        
        model.add_component(
            self.region_id + '_gen_limits_rule', 
            pyomo.Constraint(model.gen, model.t, rule=generator_constraints)
        )
    

