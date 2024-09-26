import pyomo.environ as pyomo
from .user_inputs import time_periods
from .RegionNode import RegionNode
from .Transmission import Transmission
from pyomo.common.timing import TicTocTimer
import highspy
import time


class Opt_Model:

    def print_total_demand1(self):
        total_demand_all_regions = 0  # Initialize a variable to hold the total demand across all regions

        print("Total demand for each region:")
        for r in self.model.r:
            c_load = getattr(self.model, r + '_load', None)
            if c_load is not None:
                total_demand = sum(c_load[t] for t in self.model.t)  # Sum the demand across all time periods
                total_demand_all_regions += total_demand  # Add the region's total demand to the overall total
                print(f"Region: {r}, Total Demand: {total_demand}")
            else:
                print(f"Region: {r} has no demand data.")

        # Print the total demand for all regions
        print(f"Total demand for all regions: {total_demand_all_regions}")

    def __init__(self, model_data, solver_name, deactivate_policy=False):
        
        self.timer = None
        self.results = None
        self.solver_name = solver_name
        self.sets = model_data.get('sets', {})
        self.graph = model_data.get('graph', {})
        self.rfs_policy = model_data.get('rfs_policy', {})
        self.region_list = self.sets.get('region', [])
        # self.time_periods = model_data.get('time_periods', {})
        self.time_periods = time_periods
        self.solar_ids = self.sets.get('solar_rc', [])
        self.wind_ids = self.sets.get('wind_rc', [])
        self.cost_class_ids = self.sets.get('cost_class', [])
        self.gen_type = self.sets.get('gen_type', [])
        self.deactivate_policy = deactivate_policy
        self.test_nodes = model_data.get('test_nodes', False)
        self.cons_deactivate = model_data.get('constraint_deactivation', [])
        self.deactivate_policy = deactivate_policy or 'policy' in self.cons_deactivate
        if self.test_nodes: 
            self.graph = model_data.get('subgraph', {})
            self.region_list = model_data.get('subgraph_nodes', [])
            
        self.test_cons = model_data.get('test_cons', '')
        if self.test_cons:     
            self.cons_deactivate = model_data.get('contraint_deactivation', [])   

        # Check for non-empty graph and periods, then build
        if self.graph:
            self.model = pyomo.ConcreteModel()
            self.build()

    def build(self):
        self.timer = TicTocTimer()

        self.build_grid()
        self.timer.toc('Grid built')
        
        self.build_model()
        self.timer.toc('Model built')

        # self.timer.toc('Model solving...')
        # self.solve_model()
        # self.timer.toc('Model solved')

        # self.get_results()
        
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

        # Call the total demand printing method here
        self.print_total_demand1()

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

        self.timer.toc("Starting policy constraint...")
        self.region_policy_constraint()
        self.timer.toc("Policy constraint built")

        self.timer.toc("Starting oil constraint...")
        self.oil_constraint()
        self.timer.toc("Oil constraint built")

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
            
            valid_solar_indices = None
            if c_solar_profile != 0:
                valid_solar_indices = set([s for s,_ in c_solar_profile])
            
            c_wind_cap = getattr(self.model, r + '_windCap', 0)
            c_wind_profile = getattr(self.model, r + '_windGenProfile', 0)
            x_wind_var = getattr(self.model, r + '_windNew', None)
            
            valid_wind_indices = None
            if c_wind_profile != 0: 
                valid_wind_indices = set([w for w, _ in c_wind_profile])
        
            x_stor_in = getattr(self.model, r + '_storCharge', None)
            x_stor_out = getattr(self.model, r + '_storDischarge', None)

            c_load = getattr(self.model, r + '_load', None)
            x_generation_var = getattr(self.model, r + '_generation', None)
            valid_gen_types = None
            if x_generation_var is not None:  
                valid_gen_types = set([g for g, _ in x_generation_var])

            for t in self.model.t: 

                solar_terms = 0
                if valid_solar_indices is not None: 
                    solar_terms = pyomo.quicksum(
                        ((c_solar_cap[s, c] + x_solar_var[s, c]) * c_solar_profile[s, t])
                        for s in valid_solar_indices
                        for c in self.model.cc
                    )

                wind_terms = 0 
                if valid_wind_indices is not None: 
                    wind_terms = pyomo.quicksum(
                        ((c_wind_cap[w, c] + x_wind_var[w, c]) * c_wind_profile[w, t])
                        for w in valid_wind_indices
                        for c in self.model.cc
                    )

                generation_terms = 0 
                if valid_gen_types is not None: 
                    generation_terms = pyomo.quicksum(
                        x_generation_var[g, t]
                        for g in valid_gen_types
                    )

                storage_terms = 0
                if x_stor_out is not None: 
                    storage_terms = (x_stor_out[t] - x_stor_in[t])

                demand_terms = 0
                if c_load is not None:
                    demand_terms = (c_load[t])

                import_terms = 0
                for p in self.model.p:
                    import_link = f'{r}_{p}'
                    if hasattr(self.model, import_link + '_trans'):
                        import_terms += getattr(self.model, import_link + '_trans')[t]

                export_terms = 0
                for o in self.model.o:
                    export_link = f'{o}_{r}'
                    if hasattr(self.model, export_link + '_trans'):
                        export_terms += (getattr(self.model, export_link + '_trans')[t] 
                            * getattr(self.model, export_link + '_efficiency')
                        )
           
                cons_expr = (
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

    def region_policy_constraint(self):
        if self.deactivate_policy:
            print("Policy constraint is deactivated.")
            return  # Skip adding the policy constraint if the flag is set
        self.model.rfs_balancing_rule = pyomo.ConstraintList()

        for r in self.model.r:
            c_solar_cap = getattr(self.model, r + '_solarCap', 0)
            c_solar_profile = getattr(self.model, r + '_solarGenProfile', 0)
            x_solar_var = getattr(self.model, r + '_solarNew', None)

            valid_solar_indices = None
            if c_solar_profile != 0:
                valid_solar_indices = set([s for s, _ in c_solar_profile])

            c_wind_cap = getattr(self.model, r + '_windCap', 0)
            c_wind_profile = getattr(self.model, r + '_windGenProfile', 0)
            x_wind_var = getattr(self.model, r + '_windNew', None)

            valid_wind_indices = None
            if c_wind_profile != 0:
                valid_wind_indices = set([w for w, _ in c_wind_profile])

            x_generation_var = getattr(self.model, r + '_generation', None)
            valid_gen_types = None
            if x_generation_var is not None:
                valid_gen_types = set([g for g, _ in x_generation_var])

            # Initialize terms for policy constraint
            total_wind_solar = 0
            total_generation = 0
            total_hydro_above_threshold = 0  # Hydro capacity above the threshold

            # Loop through all generators in the region
            for gen_type in valid_gen_types:
                gen_max = getattr(self.model, r + '_genMax')[gen_type]  # Access directly like a dictionary
                if "Hydro" in gen_type and gen_max > 40:
                    # If it's a hydro generator with capacity > 40 MW, include it in the hydro terms
                    for t in self.model.t:
                        hydro_terms = pyomo.quicksum(
                            x_generation_var[gen_type, t]
                            for t in self.model.t
                        )
                        total_hydro_above_threshold += hydro_terms

            for t in self.model.t:
                solar_terms = 0
                if valid_solar_indices is not None:
                    solar_terms = pyomo.quicksum(
                        ((c_solar_cap[s, c] + (x_solar_var[s, c] if x_solar_var else 0)) * c_solar_profile[s, t])
                        for s in valid_solar_indices
                        for c in self.model.cc
                    )

                wind_terms = 0
                if valid_wind_indices is not None:
                    wind_terms = pyomo.quicksum(
                        ((c_wind_cap[w, c] + (x_wind_var[w, c] if x_wind_var else 0)) * c_wind_profile[w, t])
                        for w in valid_wind_indices
                        for c in self.model.cc
                    )

                generation_terms = 0
                if valid_gen_types is not None:
                    generation_terms = pyomo.quicksum(
                        x_generation_var[g, t]
                        for g in valid_gen_types
                    )

                # Add solar and wind to policy constraint
                total_wind_solar += solar_terms + wind_terms
                total_generation += generation_terms

            # Add policy constraint to ensure wind + solar is at least X% of generation
            self.model.rfs_balancing_rule.add(
                total_wind_solar >= self.rfs_policy * (total_generation - total_wind_solar - total_hydro_above_threshold)
            )

    def oil_constraint(self):
        self.model.oil_balancing_rule = pyomo.ConstraintList()

        for r in self.model.r:
            x_generation_var = getattr(self.model, r + '_generation', None)
            valid_gen_types = None
            if x_generation_var is not None:
                valid_gen_types = set([g for g, _ in x_generation_var])

            total_generation = 0
            total_oil = 0

            # Loop through all generators in the region
            for gen_type in valid_gen_types:

                if "Oil" in gen_type:
                    for t in self.model.t:
                        oil_terms = x_generation_var[gen_type, t]
                        total_oil += oil_terms

                generation_terms = 0
                if valid_gen_types is not None:
                    generation_terms = pyomo.quicksum(
                        x_generation_var[g, t] for g in valid_gen_types for t in self.model.t
                    )

                total_generation += generation_terms

            # Add policy constraint to ensure oil is at least 1% of total generation
            self.model.oil_balancing_rule.add(
                total_oil <= 0.0001 * total_generation
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

            if constraint == 'policy' and hasattr(self.model, 'rfs_balancing_rule'):
                print("Policy constraint deactivated.")
                getattr(self.model, 'rfs_balancing_rule').deactivate()

            print(f'{constraint} constraints deactivated')
            
    def solve_model(self):
        
        solver = pyomo.SolverFactory(self.solver_name)
        self.results = solver.solve(self.model, tee=True)

    def get_results(self):

        self.results = {
            'links': {},
            'nodes': {}
        }

        for region_id, region_data in self.graph._node.items():
            node_results = region_data['object'].results(self.model, self.results)

            # Adding solar and wind generation to the node results
            solar_current, solar_new = self.get_solar_generation(region_id)
            wind_current, wind_new = self.get_wind_generation(region_id)

            if 'generator' not in node_results:
                node_results['generator'] = {'capacity': {}, 'cost': {}}

            if 'capacity' not in node_results['generator']:
                node_results['generator']['capacity'] = {}

            # Store the current and new solar/wind generation separately
            node_results['generator']['capacity']['Solar_Current'] = solar_current
            node_results['generator']['capacity']['Solar_New'] = solar_new
            node_results['generator']['capacity']['Wind_Current'] = wind_current
            node_results['generator']['capacity']['Wind_New'] = wind_new

            self.results['nodes'][region_id] = node_results

        for source, adjacency in self.graph._adj.items():
            for target, link in adjacency.items():
                self.results['links'][f'{source}_{target}'] = link['object'].results(self.model, self.results)

        return self.results

    def get_solar_generation(self, region_id):
        solar_gen_current = {}
        solar_gen_new = {}
        c_solar_cap = getattr(self.model, region_id + '_solarCap', 0)
        c_solar_profile = getattr(self.model, region_id + '_solarGenProfile', 0)
        x_solar_var = getattr(self.model, region_id + '_solarNew', None)

        valid_solar_indices = None
        if c_solar_profile != 0:
            valid_solar_indices = set([s for s, _ in c_solar_profile])

        for t in self.model.t:
            solar_terms_current = 0
            solar_terms_new = 0
            if valid_solar_indices is not None:
                # Current solar generation
                solar_terms_current = sum(
                    (c_solar_cap[s, c]) * c_solar_profile[s, t]
                    for s in valid_solar_indices
                    for c in self.model.cc
                )
                # New solar generation (from x_solar_var)
                if x_solar_var is not None:
                    solar_terms_new = sum(
                        x_solar_var[s, c].value * c_solar_profile[s, t]
                        for s in valid_solar_indices
                        for c in self.model.cc
                    )

            solar_gen_current[t] = solar_terms_current
            solar_gen_new[t] = solar_terms_new

        return solar_gen_current, solar_gen_new

    def get_wind_generation(self, region_id):
        wind_gen_current = {}
        wind_gen_new = {}
        c_wind_cap = getattr(self.model, region_id + '_windCap', 0)
        c_wind_profile = getattr(self.model, region_id + '_windGenProfile', 0)
        x_wind_var = getattr(self.model, region_id + '_windNew', None)

        valid_wind_indices = None
        if c_wind_profile != 0:
            valid_wind_indices = set([w for w, _ in c_wind_profile])

        for t in self.model.t:
            wind_terms_current = 0
            wind_terms_new = 0
            if valid_wind_indices is not None:
                # Current wind generation
                wind_terms_current = sum(
                    (c_wind_cap[w, c]) * c_wind_profile[w, t]
                    for w in valid_wind_indices
                    for c in self.model.cc
                )
                # New wind generation (from x_wind_var)
                if x_wind_var is not None:
                    wind_terms_new = sum(
                        (x_wind_var[w, c].value) * c_wind_profile[w, t]
                        for w in valid_wind_indices
                        for c in self.model.cc
                    )

            wind_gen_current[t] = wind_terms_current
            wind_gen_new[t] = wind_terms_new

        return wind_gen_current, wind_gen_new

    def get_results_hourly(self):
        self.results = {
            'links': {},
            'nodes': {}
        }

        total_generation = 0
        total_demand = 0

        for region_id, region_data in self.graph._node.items():
            node_results = region_data['object'].results(self.model, self.results)
            self.results['nodes'][region_id] = node_results

            # Add generation and demand results
            for t in self.model.t:
                generation = getattr(self.model, f'{region_id}_generation', None)
                load = getattr(self.model, f'{region_id}_load', None)

                if generation is not None:
                    generation_total = sum(generation[g, t].value for g in self.model.gen if (g, t) in generation)
                    total_generation += generation_total

                if load is not None:
                    # Assuming load[t] is a float, no need for .value
                    demand_total = load[t]
                    total_demand += demand_total

                print(f"Region {region_id}, Time {t}: Generation = {generation_total}, Demand = {demand_total}")

        print(f"Total generation: {total_generation}, Total demand: {total_demand}")

