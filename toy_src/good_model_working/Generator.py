import pyomo.environ as pyomo

class Generator:
    def __init__(self, region_id, generators):
        self.region_id = region_id
        self.gen_cost = {}
        self.gen_capacity = {}
        

        for data in generators:     
            cost_weight = {}

            for params in data.get('parameters',[]): 

                gen_id = params.get('gen_type', '')
                values = params.get('values', {})
                capacity = values.get('capacity',0)
                cost = values.get('cost', 0)
                
                if gen_id not in self.gen_capacity:
                    self.gen_capacity[gen_id] = capacity
                else: 
                    self.gen_capacity[gen_id] += capacity
                
                cost_weight[gen_id] = cost_weight.get(gen_id, 0) + cost * capacity

            for gen_id, wt_cost in cost_weight.items():
                if self.gen_capacity[gen_id] > 0:
                    self.gen_cost[gen_id] = wt_cost / self.gen_capacity[gen_id]
                    
               
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
    

