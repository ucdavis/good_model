import pyomo.environ as pyomo
from .constants import time_periods
from .RegionNode import RegionNode
from .Transmission import Transmission
from pyomo.common.timing import TicTocTimer
import logging
import highspy
import cProfile


class Opt_Model:
    def __init__(self, graph, sets, enable_logging=False):
        self.graph = graph
        self.sets = sets
        self.time_periods = time_periods
        self.region_list = self.sets.get('region', [])
        self.solar_ids = self.sets.get('solar_rc', [])
        self.wind_ids = self.sets.get('wind_rc', [])
        self.cost_class_ids = self.sets.get('cost_class', [])
        self.gen_type = self.sets.get('gen_type', [])
        
        # Check for non-empty graph and periods, then build
        if self.graph and self.time_periods and self.sets:
            self.model = pyomo.ConcreteModel()
            self.build()

            if enable_logging:
                pyomo_logger = logging.getLogger('pyomo.core')
                pyomo_logger.setLevel(logging.ERROR)


    def build(self):
        self.timer = TicTocTimer()

        self.build_grid()
        self.timer.toc('Grid built')
        
        self.build_model()
        self.timer.toc('Model built')

        # self.timer.toc('Model solving...')
        # self.solve_model()
        # self.timer.toc('Model solved')

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
        self.timer.toc('All Constraints built')

    def build_sets(self):

        self.model.t = pyomo.Set(initialize=self.time_periods)
        self.model.r = pyomo.Set(initialize=self.region_list)
        self.model.o = pyomo.Set(initialize=self.region_list) 
        self.model.p = pyomo.Set(initialize=self.region_list)
        self.model.gen = pyomo.Set(initialize=self.gen_type)
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

        for region_id, region_data in self.graph._node.items():

            region_data['object'].variables(self.model)

        for source, adjacency in self.graph._adj.items():

            for target, link in adjacency.items():

               link['object'].variables(self.model)


    def build_objective(self):
        
        objective_function = 0
    
        for region_id, region_data in self.graph._node.items(): 

            objective_function += region_data['object'].objective(self.model)

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

        for region_id, region_data in self.graph._node.items(): 
            
            region_data['object'].constraints(self.model)

    def transmission_constraints(self): 

        for source, adjacency in self.graph._adj.items():

            for target, link in adjacency.items():  

                link['object'].constraints(self.model)

    def region_balancing_constraint(self): 

        self.model.energy_balancing_rule = pyomo.ConstraintList()

        for r in self.model.r:
            self.timer.toc(f'{r} energy balancing constraint starting...')
            solar_indices = [s for s, _ in getattr(self.model, r + '_solarGenProfile')]
            wind_indices = [w for w, _ in getattr(self.model, r + '_windGenProfile')]

            for t in self.model.t:
                generation_terms = 0
                if hasattr(self.model, r + '_generation'):
                    for g in self.model.gen:
                        generation_terms += getattr(self.model, r + '_generation')[g, t]


                solar_terms = 0
                if hasattr(self.model, r + '_solarGenProfile') and hasattr(self.model, r + '_solarCap'):
                    solar_cap = getattr(self.model, r + '_solarCap')
                    for s in solar_indices:
                        for c in self.model.cc:
                            solar_terms += ((solar_cap + getattr(self.model, r + '_solarNew')[s, c]) 
                                * getattr(self.model, r + '_solarGenProfile')[s, t]
                            )

                elif hasattr(self.model, r + '_solarGenProfile'):
                    for s in solar_indices:
                        for c in self.model.cc:
                            solar_terms += (getattr(self.model, r + '_solarNew')[s, c] 
                                * getattr(self.model, r + '_solarGenProfile')[s, t]
                            )


                wind_terms = 0
                if hasattr(self.model, r + '_windGenProfile') and hasattr(self.model, r + '_windCap'):
                    wind_cap = getattr(self.model, r + '_windCap')
                    for w in wind_indices:
                        for c in self.model.cc:
                            wind_terms += ((wind_cap + getattr(self.model, r + '_windNew')[w, c]) 
                                * getattr(self.model, r + '_windGenProfile')[w, t]
                            )

                elif hasattr(self.model, r + '_windGenProfile'):
                    for w in wind_indices:
                        for c in self.model.cc:
                            wind_terms += (getattr(self.model, r + '_windNew')[w, c] 
                                * getattr(self.model, r + '_windGenProfile')[w, t]
                            )


                storage_terms = 0
                if hasattr(self.model, r + '_storCap'):
                    storage_terms = getattr(self.model, r + '_storDischarge')[t] - getattr(self.model, r + '_storCharge')[t]

                demand_terms = 0
                if hasattr(self.model, r + '_load'):
                    demand_terms = getattr(self.model, r + '_load')[t]

                export_terms = 0
                for o in self.model.o:
                    export_link = f'{o}_{r}'
                    if hasattr(self.model, export_link + '_trans'):
                        export_terms += (getattr(self.model, export_link + '_trans')[t] 
                            * getattr(self.model, export_link + '_efficiency')
                        )

                import_terms = 0
                for p in self.model.p:
                    import_link = f'{r}_{p}'
                    if hasattr(self.model, import_link + '_trans'):
                        import_terms = getattr(self.model, import_link + '_trans')[t]

                self.model.energy_balancing_rule.add(
                    generation_terms
                    + solar_terms
                    + wind_terms
                    + storage_terms
                    + import_terms
                    - export_terms
                    - demand_terms
                    >= 0
                )

            self.timer.toc(f'{r} balancing constraint built')

    def solve_model(self, solver_name="appsi_highs"):
        
        solver = pyomo.SolverFactory(solver_name)
        solution = solver.solve(self.model, tee=True)
        
        return solution
