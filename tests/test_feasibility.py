import pytest
from good.optimization import Network
import networkx as nx
from good.graph import graph_from_json

def graph_from_dict(graph_dict):
    """Creates a NetworkX graph from a dictionary representation"""
    graph = nx.DiGraph()
    
    # Add nodes
    for node_id, node_data in graph_dict["nodes"].items():
        graph.add_node(node_id, **node_data)
    
    # Add edges
    for edge_id, edge_data in graph_dict["edges"].items():
        source = edge_data.pop("from", None)
        target = edge_data.pop("to", None)
        if source and target:
            graph.add_edge(source, target, **edge_data)
    
    return graph

@pytest.mark.optimization
class TestFeasibility:
    
    def test_empty_network(self, empty_graph):
        """Test that empty network has zero generation and cost"""
        network = Network().from_graph(graph_from_dict(empty_graph))
        network.build()
        network.solve()
        result = network.optimize()
        assert result.objective_value == 0
        assert sum(gen.production for gen in result.generators.values()) == 0

    def test_no_load_minimal_generation(self, single_node_graph):
        """Test that network with no load has minimal generation even with free renewables"""
        # Modify generator to be renewable with zero cost
        single_node_graph["nodes"]["region1"]["generators"][0]["type"] = "renewable"
        single_node_graph["nodes"]["region1"]["generators"][0]["operating_cost"] = 0
        # Remove load
        single_node_graph["nodes"]["region1"]["loads"] = []
        
        network = Network().set_graph(graph_from_dict(single_node_graph))
        result = network.optimize()
        assert sum(gen.production for gen in result.generators.values()) == 0

    def test_infeasible_high_load(self, single_node_graph):
        """Test that network fails with impossibly high load"""
        single_node_graph["nodes"]["region1"]["loads"][0]["demand"] = 1e12
        
        network = Network().set_graph(graph_from_dict(single_node_graph))
        with pytest.raises(Exception):
            network.optimize()

    def test_expensive_generator_last_resort(self, single_node_graph):
        """Test that expensive generator is only used when necessary"""
        # Add a cheap and expensive generator
        region = next(node for node in single_node_graph["nodes"] if node["id"] == "region1")
        region["assets"] = [
            {
                "type": "Producer",
                "_class": "Producer",
                "handle": "cheap_gen",
                "installed_capacity": 40,
                "operating_cost": 10
            },
            {
                "type": "Producer",
                "_class": "Producer",
                "handle": "expensive_gen",
                "installed_capacity": 100,
                "operating_cost": 1000
            }
        ]
        
        network = Network().from_graph(graph_from_dict(single_node_graph))
        network.build()
        network.solve()
        
        # Verify cheap generator is used first
        assert network.results["cheap_gen::production"].sum() == 30
        assert network.results["expensive_gen::production"].sum() == 0

        # Now increase load beyond cheap generator capacity
        single_node_graph["nodes"]["region1"]["loads"][0]["demand"] = 50
        network = Network().set_graph(graph_from_dict(single_node_graph))
        result = network.optimize()
        
        # Verify expensive generator is used only for excess
        assert result.generators["cheap_gen"].production == 40
        assert result.generators["expensive_gen"].production == 10 