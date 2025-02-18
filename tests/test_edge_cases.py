import pytest
from good.optimization import Network
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
        
        network = Network().from_graph(graph_from_dict(two_node_graph))
        with pytest.raises(Exception):
            network.optimize()

    def test_transmission_limits(self, two_node_graph):
        """Test that transmission limits are respected"""
        # Set transmission capacity to 50
        two_node_graph["edges"][0]["installed_capacity"] = 50
        
        # Set load to 100
        load_asset = next(asset for node in two_node_graph["nodes"] 
                         for asset in node["assets"] 
                         if asset["type"] == "Load")
        load_asset["profile"] = [100.0] * 24
        
        network = Network().from_graph(graph_from_dict(two_node_graph))
        network.build()
        with pytest.raises(Exception):  # Should be infeasible
            network.solve()

        # Now make it feasible with local generation
        region2 = next(node for node in two_node_graph["nodes"] if node["id"] == "region2")
        region2["assets"].append({
            "type": "Producer",
            "_class": "Producer",
            "handle": "local_gen",
            "installed_capacity": 50,
            "operating_cost": 60,  # More expensive than remote generation
            "profile": [1.0] * 24
        })
        
        network = Network().set_graph(graph_from_dict(two_node_graph))
        result = network.optimize()
        
        # Verify transmission limit is respected
        assert result.lines["line1"].flow <= 50 