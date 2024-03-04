import pyomo.environ as pyomo
from RegionNode import RegionNode
from Transmission import Transmission
import utils

class Model:
    def __init__(self, graph):
        self.graph = graph
        self.time_periods = utils.time_periods
        self.region_list = list(graph.nodes.keys())  # Corrected from graph.node.keys()
        self.model = pyomo.ConcreteModel()

        # Check for non-empty graph and periods, then build
        if self.graph and self.time_periods:
            self.build()

    def build(self):
        self.build_grid()
        self.build_model()

    def build_grid(self):
        self.network_data = self.graph

        for region_id, region_data in self.graph.nodes(data=True):  # Corrected iteration over nodes
            
            self.region_data['object'] = RegionNode(region_id, **region_data)

        for source, target, links in self.graph.edges(data=True):  # Corrected iteration over edges

            self.links['object'] = Transmission(source, target, **link)

    def build_model(self):

        self.build_sets()

        self.build_paramaters()

        self.build_variables()

        self.build_objective()

        self.build_constraints()

    def build_sets(self):

        self.global_sets()

        self.local_sets()

    def global_sets(self, model): 

        self.model.t = pyomo.Set(initialize=self.time_periods)
        self.model.r = pyomo.Set(initialize=self.region_list)
        self.model.o = pyomo.Set(initialize=self.model.r)
        self.model.p = pyomo.Set(initialize=self.model.r)

    def local_sets(self, model): 

        for obj in region_data: 

            obj.sets()
    
    def build_paramaters(self, model): 

        for obj in region_data: 

            obj.parameters()

        for edge in links: 

            edge.parameters()
    
    def build_variables(self,model):

	    for node in self.graph.node.values():

		    self.model = node['object'].variables(self.model)

	    for source, adjacency in self.graph.adj.items():

		    for target, link in adjacency.items():

			    self.model = link['object'].variables(self.model)


    def build_objective(self):
        
        objective_function = 0 
        
        for node in self.graph.node.values(): 

            objective_function += node['object'].objective(self.model)

        for source, adjacency in self.graph.adj.items():

            for target, link in adjacency.items(): 

                objective_function += link['object'].objective(self.model)

        self.model.obj_func = pyomo.Objective(expr=objective_function)

    def build_constraints(self, model):

        self.local_constraints()

        self.transmissions_constraints() 

        self.region_balancing_constraint()

    def local_constraints(self, model): 

        for node in self.graph.node.values(): 
            
            node['object'].constraints(self.model)

    def transmission_constraints(self, model): 

        for source, adjacency in self.graph.adj.items():

            for target, link in adjacency.items():  

                link['object'].constraints(self.model)

    def region_balancing_constraint(self, model): 

        for source, adjacency in self.graph.adj.items(): 

            source_node = self.graph.node[source]

            for target, link in adjacency.items(): 

                target_node = self.graph.node[target]

                object_data = source_node.get('object')



        for region_id, region_data in self.graph.node.items(): 
            region = region_data.get('object', [])

        # constraint 1: generation-demand balancing
        self.model.gen_to_demand_rule = pyomo.ConstraintList()

        for gf in self.model.gf:
            for t in self.model.t:
                generation_term += self.model.x_generation[gf, t]
        
        solar_term = pyomo.quicksum((Solar.model.c_solarCap + self.region_objects.Solar.model.x_solarNew[s,c]) * self.region_objects.Solar.model.c_solarCF[s,t]
            for s in self.model.src 
            for t in self.model.t
            for c in self.model.cc) 
             
        wind_term = pyomo.quicksum((self.region_objects.Wind.model.c_windCap + self.region_objects.Wind.model.x_windNew[w,c]) * self.region_objects.Wind.model.c_windCF[w,t] 
            for w in self.model.wrc 
            for c in self.model.cc
            for t in self.model.t) 
        
        storage_term = pyomo.quicksum(self.region_objects.Storage.model.x_stordischarge[t] - self.region_objects.Storage.model.x_storcharge[t] 
            for t in self.model.t)

        # how to handle region sets in the region nodes 
        ## include some region_id check in the model.o, model.r, and model.p sets?
        export_indices = [r for r in self.model.r if r == self.region_id]

        export_term = pyomo.quicksum(Transmission.model.x_trans[o,r,t] * Transmission.model.c_transLoss 
            for o in model.o 
            for r in model.r 
            for t in model.t)

        for r in model.r: 
            for p in model.p: 
                for t in model.t:
                    import_term += Transmission.model.x_trans[r,p,t] 
        
        for t in self.model.t: 
            demand_term += self.region_objects.Load.model.c_demandLoad[t]
        
        constraint_expr = (generation_term 
            + solar_term 
            + wind_term 
            + storage_term
            + import_term
            - export_term
            - transmission_term
            - demand_term
            ) == 0
				
        self.model.gen_to_demand_rule.add(constraint_expr)

        return model

    def solve_model(self, solver_name="glpk"):
        solver = pyomo.SolverFactory(solver_name)
        solution = solver.solve(self.model, tee=True)
        return solution
