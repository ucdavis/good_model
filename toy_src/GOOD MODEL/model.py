import pyomo.environ as pyomo
from RegionNode import RegionNode
from Transmission import Transmission
class Model:
    def __init__(self, graph, periods):
        self.graph = graph
        self.time_periods = periods.get('hours', [])
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
            region_data['object'] = RegionNode(region_id, **region_data)

        for source, target, link in self.graph.edges(data=True):  # Corrected iteration over edges
            link['object'] = Transmission(source, target, **link)

    def build_model(self):
        self.build_sets()
        self.build_variables()
        self.build_objective()
        self.build_constraints()

    def build_sets(self):
        self.model.t = pyomo.Set(initialize=self.time_periods)
        self.model.r = pyomo.Set(initialize=self.region_list)

    def build_variables(self):
        pass

    def build_objective(self):
        pass

    def build_constraints(self):
        pass

    def solve_model(self, solver_name="glpk"):
        solver = pyomo.SolverFactory(solver_name)
        solution = solver.solve(self.model, tee=True)
        return solution
