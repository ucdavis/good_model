import pyomo.environ as pyomo
from .constants import transmission_efficiency


class Transmission:
    def __init__(self, source, target, **kwargs):
        self.source = source
        self.target = target
        self.trans_link = f'{self.source}_{self.target}'
        self.capacity = kwargs.get('capacity', 0)
        self.cost = kwargs.get('cost', 0)
        self.efficiency = transmission_efficiency
    
    def parameters(self, model):

        model.add_component( 
            self.trans_link + '_transCost', 
            pyomo.Param(initialize=self.cost)
        )

        model.add_component(
            self.trans_link + '_transCap', 
            pyomo.Param(initialize=self.capacity)
        ) 
       
        model.add_component(
            self.trans_link + '_efficiency', 
            pyomo.Param(initialize=self.efficiency)
        )

    def variables(self, model):

        model.add_component(
             self.trans_link + '_trans',
             pyomo.Var(model.t, within=pyomo.NonNegativeReals)
        )

    def objective(self, model):
        # Simplify the objective function to accumulate transmission costs correctly

        tranmission_cost_term = 0

        transmission_cost_term = pyomo.quicksum(
            getattr(model, self.trans_link + '_trans')[t] * getattr(model, self.trans_link + '_transCost')
            for t in model.t)

        return transmission_cost_term

    def constraints(self, model):
        
        def transmission_constraints(model, t): 
            return getattr(model, self.trans_link + '_transCap') - getattr(model, self.trans_link + '_trans')[t] >= 0
        
        model.add_component(
            self.trans_link + '_trans_limit_rule',
            pyomo.Constraint(model.t, rule=transmission_constraints)
        )

    def results(self, model, results): 

        results = {}
        
        trans_capacity = getattr(model, self.trans_link + '_trans').extract_values()
        trans_cost = list(getattr(model, self.trans_link + '_transCost').extract_values().values())[0]
    
        cost_dict = 0
        capacity_dict = {}

        for key, value in trans_capacity.items(): 
            capacity_dict[key] = value
            # if self.trans_link not in cost_dict:
            #     cost_dict[self.trans_link] = 0  
            cost_dict += trans_cost * value

        results = {
            'type': 'transmission',
            'cost': cost_dict, 
            'capacity': capacity_dict
            }

        return results 