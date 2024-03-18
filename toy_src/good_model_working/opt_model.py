import pyomo.environ as pyomo
from .constants import time_periods
from .RegionNode import RegionNode
from .Transmission import Transmission
from pyomo.common.timing import TicTocTimer


class Opt_Model:
    def __init__(self, graph, sets):
        self.graph = graph
        self.sets = sets
        self.time_periods = time_periods
        self.region_list = self.sets.get('region', [])
        self.solar_ids = self.sets.get('solar_rc', [])
        self.wind_ids = self.sets.get('wind_rc', [])
        self.cost_class_ids = self.sets.get('cost_class', [])
        self.generator_type = self.sets.get('plant_type', [])
        self.gen_fuel_type = self.sets.get('fuel_type', [])

        # Check for non-empty graph and periods, then build
        if self.graph and self.time_periods and self.sets:

            self.model = pyomo.ConcreteModel()
            
            self.build()

    def build(self):
        self.timer = TicTocTimer()

        self.build_grid()
        self.timer.toc('Grid built')
        
        self.build_model()
        self.timer.toc('Model built')

        self.timer.toc('Model solving...')
        self.solve_model()
        self.timer.toc('Model solved')

    def build_grid(self):

        for region_id, region_data in self.graph._node.items():  

            region_data['object'] = RegionNode(region_id, **region_data)
    
        for source, adjacency in self.graph._adj.items():

            for target, link in adjacency.items():

                link['object'] = Transmission(source, target, **link)

            
    def build_model(self):

        self.build_sets()
        self.timer.toc('Sets built')

        self.build_parameters()
        self.timer.toc('Parameters built')

        self.build_variables()
        self.timer.toc('Variables built')

        self.build_objective()
        self.timer.toc('Objective Function built')

        self.build_constraints()
        self.timer.toc('Constraints built')

    def build_sets(self):

        self.global_sets()

    def global_sets(self): 

        self.model.t = pyomo.Set(initialize=self.time_periods)
        self.model.r = pyomo.Set(initialize=self.region_list)
        self.model.o = pyomo.Set(initialize=self.model.r)
        self.model.p = pyomo.Set(initialize=self.model.r)
        self.model.g = pyomo.Set(initialize=self.generator_type)
        self.model.gf = pyomo.Set(initialize=self.gen_fuel_type)
        self.model.src = pyomo.Set(initialize=self.solar_ids)
        self.model.wrc = pyomo.Set(initialize=self.wind_ids)
        self.model.cc = pyomo.Set(initialize=self.cost_class_ids)

    def build_parameters(self): 

        for region_id, region_data in self.graph._node.items():

            region_data['object'].parameters(self.model)

        for source, adjacency in self.graph._adj.items():
           
           for target, link in adjacency.items():

	            link['object'].parameters(self.model)
        
    def build_variables(self):

        for node in self.graph._node.values():

            node['object'].variables(self.model)

        for source, adjacency in self.graph._adj.items():

            for target, link in adjacency.items():

               link['object'].variables(self.model)

    def build_objective(self):
        
        objective_function = 0
    
        for node in self.graph._node.values(): 

            objective_function += node['object'].objective(self.model)

        for source, adjacency in self.graph._adj.items():

            for target, link in adjacency.items(): 

                objective_function += link['object'].objective(self.model)

        self.model.obj_func = pyomo.Objective(expr=objective_function, sense=pyomo.minimize)

    def build_constraints(self):

        self.local_constraints()
        self.timer.toc("Local Constraints built")

        self.transmission_constraints() 
        self.timer.toc("Transmission constraints built")

        self.timer.toc("Starting balanacing constraint...")
        self.region_balancing_constraint()
        self.timer.toc("Balancing constraint built")

    def local_constraints(self): 

        for node in self.graph._node.values(): 
            
            node['object'].constraints(self.model)

    def transmission_constraints(self): 

        for source, adjacency in self.graph._adj.items():

            for target, link in adjacency.items():  

                link['object'].constraints(self.model)

    def region_balancing_constraint(self): 

        # constraint 1: generation-demand balancing
        self.model.gen_to_demand_rule = pyomo.ConstraintList()

        generation_terms = pyomo.Expression(initialize=0)
        solar_terms = pyomo.Expression(initialize=0)
        wind_terms = pyomo.Expression(initialize=0)
        storage_terms = pyomo.Expression(initialize=0)
        demand_terms = pyomo.Expression(initialize=0)
        export_terms = pyomo.Expression(initialize=0)
        import_terms = pyomo.Expression(initialize=0)
        
       
        for r in self.model.r: 
            for t in self.model.t: 

                if hasattr(self.model, r + '_generation'): 
                    for gf in self.model.gf:
                        generation_terms += (getattr(self.model, r + '_generation')[g, gf, t])

                if hasattr(self.model, r + '_solarNew'): 
                    for s in self.model.src:
                        for c in self.model.cc:
                            solar_terms += (getattr(self.model, r + '_solarCap')[s][c] + getattr(self.model, r + '_solarNew')[s,c]) * getattr(self.model, r + '_solarprofile')[s][t]

                if hasattr(self.model, r + '_windNew'):
                    for w in self.model.wrc: 
                        for c in self.model.cc: 
                         wind_terms += (getattr(self.model, r + '_windCap') + getattr(self.model, r + '_windNew')[w, c]) * getattr(self.model, r + '_windprofile')[w][t]


                if hasattr(self.model, r + '_storCharge'):
                    storage_terms += (getattr(self.model, r + '_storDischarge')[t] - getattr(self.model, r + '_storCharge')[t])

                demand_terms = []
                if hasattr(self.model, r + '_load'): 
                    demand_terms += getattr(self.model, r + '_load')[t]


        for o in self.model.o: 
            for r in self.model.r: 
                export_link = f'{o}_{r}'
                if hasattr(self.model, export_link + '_trans'): 
                    for t in self.model.t:
                        export_terms += getattr(self.model, export_link + '_trans')[t] *  getattr(self.model, export_link + '_efficiency')
        
        for r in self.model.r: 
            for p in self.model.p: 
                import_link = f'{r}_{p}'
                if hasattr(self.model, import_link + '_trans'): 
                    for t in self.model.t:
                        import_terms += getattr(self.model, import_link + '_trans')[t]

 
        constraint_expr = (
            generation_terms
            + solar_terms 
            + wind_terms
            + storage_terms
            + import_terms
            - export_terms
            - demand_terms
        ) == 0
				
        self.model.gen_to_demand_rule.add(constraint_expr)

       
    def solve_model(self, solver_name="cbc"):
        
        solver = pyomo.SolverFactory(solver_name)
        solution = solver.solve(self.model)
        
        return solution
