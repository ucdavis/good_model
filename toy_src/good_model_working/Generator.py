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

                for val in values: 

                    capacity = val.get('capacity',0)
                    cost = val.get('cost', 0)
                    cf = val.get('cf', 1)
                
                if gen_id not in self.gen_capacity:
                    self.gen_capacity[gen_id] = capacity
                else: 
                    self.gen_capacity[gen_id] += capacity
                
                cost_weight[gen_id] = cost_weight.get(gen_id, 0) + cost * capacity

            for gen_id, wt_cost in cost_weight.items():
                if self.gen_capacity[gen_id] > 0:
                    self.gen_cost[gen_id] = wt_cost / self.gen_capacity[gen_id]

        gen_to_remove = ['Fossil Waste', 
        'Municipal Solid Waste', 
        'Non-Fossil Waste', 
        'Pumped Storage',
        'Fuel Cell',
        'Landfill Gas', 
        "Energy Storage", 
        "Solar PV", 
        "Onshore Wind", 
        'New Battery Storage', 
        'IMPORT', 
        'Tires',
        'Offshore Wind', 
        'Solar Thermal']

        self.gen_cost = {key: value for key, value in self.gen_cost.items() if not any(substring in key for substring in gen_to_remove)}
        self.gen_capacity = {key: value for key, value in self.gen_capacity.items() if not any(substring in key for substring in gen_to_remove)}
        # for key, capacity in self.gen_capacity.items(): 
        #     # if 'Hydro' in key: 
        #     #     self.gen_capacity[key] = capacity/2
        for key, cost in self.gen_capacity.items(): 
            if 'Hydro' in key: 
                self.gen_cost[key] = 40
            if 'Geothermal' in key: 
                self.gen_cost[key] = 50
            if 'Nuclear' in key and cost == 0 : 
                self.gen_cost[key] = 45

    def parameters(self, model):

        model.add_component(
            self.region_id + '_gencost', 
            pyomo.Param(model.gen, initialize=self.gen_cost, default= 0)
        )

        model.add_component(
            self.region_id + '_genMax', 
            pyomo.Param(model.gen, initialize=self.gen_capacity, default=0)
        )

    def variables(self, model):

        model.add_component(
            self.region_id + '_generation',
            pyomo.Var(model.gen, model.t, within=pyomo.NonNegativeReals)
        )

    def objective(self, model):

        gen_indices = [g for g in model.gen if g in getattr(model, self.region_id + '_gencost')]

        gen_cost_term = 0

        gen_cost_term = pyomo.quicksum(
            getattr(model, self.region_id + '_generation')[g,t] 
            * getattr(model, self.region_id + '_gencost')[g]
            for g in gen_indices
            for t in model.t)

        return gen_cost_term

    def constraints(self, model):
            
        def generator_constraints(model, g, t): 
            if g in getattr(model, self.region_id + '_genMax'): 
                return (getattr(model, self.region_id + '_genMax')[g] 
                - (getattr(model, self.region_id + '_generation')[g,t]) 
                >= 0 
                )
            else: 
                return pyomo.Constraint.Skip
        
        model.add_component(
            self.region_id + '_gen_limits_rule', 
            pyomo.Constraint(model.gen, model.t, rule=generator_constraints)
        )
    
    def results(self, model, results):
        
        results = {}

        region_cost= {}
        region_capacity = {}
    
        if hasattr(model, self.region_id + '_generation'): 
            dispatch_capacity = getattr(model, self.region_id + '_generation').extract_values()
            
            for key, value in dispatch_capacity.items(): 
                gen_type = key[0]
                hour = key[1]
                if gen_type not in region_capacity: 
                    region_capacity[gen_type] = {} 
                
                region_capacity[gen_type][hour] = value

        if hasattr(model,self.region_id + '_gencost'): 
            dispatch_cost = getattr(model, self.region_id + '_generation').extract_values()

            for gen_type, profile in region_capacity.items(): 
                region_cost[gen_type] = {}

                if gen_type in dispatch_cost: 
                    cost = dispatch_cost[gen_type]
                else: 
                    cost = 0

                for hour, capacity in profile.items(): 
                    region_cost[gen_type] = cost * capacity
    

        results = {
            'cost': region_cost, 
            'capacity': region_capacity
            }

        return results


        


