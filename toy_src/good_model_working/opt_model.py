import pyomo.environ as pyomo
from .constants import time_periods
from .RegionNode import RegionNode
from .Transmission import Transmission
from pyomo.common.timing import TicTocTimer
import highspy
import time


class Opt_Model:
    def __init__(self, model_data):
        
        self.sets = model_data.get('sets', {})
        self.graph = model_data.get('graph', {})
        self.region_list = self.sets.get('region', [])
        self.time_periods = time_periods
        self.solar_ids = self.sets.get('solar_rc', [])
        self.wind_ids = self.sets.get('wind_rc', [])
        self.cost_class_ids = self.sets.get('cost_class', [])
        self.gen_type = self.sets.get('gen_type', [])

        self.test_nodes = model_data.get('test_nodes', False)
        if self.test_nodes: 
            self.graph = model_data.get('subgraph', {})
            self.region_list = model_data.get('subgraph_nodes', [])
            
        self.test_cons = model_data.get('test_cons', '')
        if self.test_cons:     
            self.cons_deactivate = model_data.get('contraint_deactivation', [])   

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

        self.get_results()
        
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

        if self.test_cons:
            self.constraint_deactivation()
            print('Constraint deactivation called')

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

            c_solar_cap = getattr(self.model, r + '_solarCap', 0)
            c_solar_profile = getattr(self.model, r + '_solarGenProfile', 0)
            x_solar_var = getattr(self.model, r + '_solarNew', None)
            
            solar_indices = None
            if c_solar_profile != 0:
                solar_indices = set([s for s,_ in c_solar_profile])
            
            c_wind_cap = getattr(self.model, r + '_windCap', 0)
            c_wind_profile = getattr(self.model, r + '_windGenProfile', 0)
            x_wind_var = getattr(self.model, r + '_windNew', None)
            
            wind_indices = None
            if c_wind_profile != 0: 
                wind_indices = set([w for w, _ in c_wind_profile])
        
            x_stor_in = getattr(self.model, r + '_storCharge', None)
            x_stor_out = getattr(self.model, r + '_storDischarge', None)

            c_load = getattr(self.model, r + '_load', None)
            x_generation_var = getattr(self.model, r + '_generation', None)
            
            for t in self.model.t: 

                solar_terms = 0
                if solar_indices is not None: 
                    solar_terms = pyomo.quicksum(
                        ((c_solar_cap[s,c] + x_solar_var[s, c]) * c_solar_profile[s, t])
                        for s in solar_indices
                        for c in self.model.cc
                    )
            
                wind_terms = 0 
                if wind_indices is not None: 
                    wind_terms = pyomo.quicksum(
                        ((c_wind_cap[w,c] + x_wind_var[w, c]) * c_wind_profile[w, t])
                        for w in wind_indices
                        for c in self.model.cc
                    )


                generation_terms = 0 
                if x_generation_var is not None: 
                    generation_terms = pyomo.quicksum(
                        x_generation_var[g, t]
                        for g in self.model.gen
                    )

                
                storage_terms = 0
                if x_stor_out is not None: 
                    storage_terms = (x_stor_out[t] - x_stor_in[t])

                demand_terms = 0
                if c_load is not None:
                    demand_terms = (c_load[t])

                export_terms = 0
                for o in self.model.o:
                    export_link = f'{o}_{r}'
                    if hasattr(self.model, export_link + '_trans'):
                        export_terms = (getattr(self.model, export_link + '_trans')[t] 
                            * getattr(self.model, export_link + '_efficiency')
                        )

                import_terms = 0
                for p in self.model.p:
                    import_link = f'{r}_{p}'
                    if hasattr(self.model, import_link + '_trans'):
                        import_terms = getattr(self.model, import_link + '_trans')[t]
                
                cons_expr =  (
                    solar_terms 
                    + wind_terms 
                    + storage_terms 
                    + generation_terms 
                    + import_terms
                    - export_terms
                    - demand_terms
                    >= 0
                )

                self.model.energy_balancing_rule.add(
                   cons_expr
                )

    def constraint_deactivation(self): 

        for constraint in self.cons_deactivate: 
            if constraint == 'storage':
                for r in self.model.r: 
                    x_stor_in = getattr(self.model, r + '_storCharge', None)
                    if x_stor_in is not None: 
                        getattr(self.model, r + '_storage_SOC_rule').deactivate()
                        getattr(self.model, r + '_stor_charge_rule').deactivate()
                        getattr(self.model, r + '_stor_discharge_rule').deactivate()
                        getattr(self.model, r + '_storage_capacity_rule').deactivate()

            print(f'{constraint} constraints deactivated')

            if constraint == 'solar':
                for r in self.model.r: 
                    solar_max = getattr(self.model, r + '_solarMax', None)
                    if solar_max is not None: 
                        getattr(self.model, r + '_solar_install_limits').deactivate()

            print(f'{constraint} constraints deactivated')
            
            if constraint == 'wind':
                for r in self.model.r: 
                    wind_max = getattr(self.model, r + '_windrMax', None)
                    if wind_max is not None: 
                        getattr(self.model, r + '_wind_install_limits').deactivate()

            print(f'{constraint} constraints deactivated')
            
            if constraint == 'generator':
                for r in self.model.r: 
                    gen_max = getattr(self.model, r + '_genMax', None)
                    if gen_max is not None: 
                        getattr(self.model, r + '_gen_limits_rule').deactivate()
        
            print(f'{constraint} constraints deactivated')
            
    def solve_model(self, solver_name="appsi_highs"):
        
        solver = pyomo.SolverFactory(solver_name)
        self.results = solver.solve(self.model, tee=True)

    def get_results(self): 

        self.results = {
            'links': {}, 
            'nodes': {}
        }

        for region_id, region_data in self.graph._node.items():
            
            self.results['nodes'][region_id] = region_data['object'].results(self.model, self.results)

        for source, adjacency in self.graph._adj.items():

            for target, link in adjacency.items():

               self.results['links'][f'{source}_{target}'] = link['object'].results(self.model, self.results)
               
        return self.results