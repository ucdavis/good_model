import pytest
from src.optimization import Network
import networkx as nx


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
class TestTransmission:
    
    def test_isolated_load_infeasible(self, two_node_graph):
        """Test that load without local generation or transmission is infeasible"""
        # Remove transmission line
        two_node_graph["edges"] = {}
        
        network = Network().set_graph(graph_from_dict(two_node_graph))
        with pytest.raises(Exception):
            network.optimize()

    def test_transmission_limits(self, two_node_graph):
        """Test that transmission limits are respected"""
        # Set transmission capacity to 50
        two_node_graph["edges"]["line1"]["capacity"] = 50
        # Set load to 100
        two_node_graph["nodes"]["region2"]["loads"][0]["demand"] = 100
        
        network = Network().set_graph(graph_from_dict(two_node_graph))
        with pytest.raises(Exception):  # Should be infeasible
            network.optimize()

        # Now make it feasible with local generation
        two_node_graph["nodes"]["region2"]["generators"].append({
            "id": "local_gen",
            "type": "conventional",
            "capacity": 50,
            "operating_cost": 60  # More expensive than remote generation
        })
        
        network = Network().set_graph(graph_from_dict(two_node_graph))
        result = network.optimize()
        
        # Verify transmission limit is respected
        assert result.lines["line1"].flow <= 50 