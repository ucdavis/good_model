import pytest
from good.optimization import Network
import networkx as nx
from good.graph import graph_from_json
import numpy as np

def graph_from_dict(graph_dict):
    """Creates a NetworkX graph from a dictionary representation"""
    graph = nx.DiGraph()
    
    # Add nodes
    for node in graph_dict["nodes"]:
        node_id = node["id"]
        graph.add_node(node_id, **node)
    
    # Add edges
    for edge in graph_dict["edges"]:
        source = edge.get("source") or edge.get("from")
        target = edge.get("target") or edge.get("to")
        if source and target:
            graph.add_edge(source, target, **edge)
    
    return graph

@pytest.mark.optimization
class TestFeasibility:
    
    def test_empty_network(self, empty_graph):
        """Test that empty network has zero generation and cost"""
        # Add a minimal node to make the problem well-formed
        empty_graph["nodes"] = [{
            "type": "Region",
            "_class": "Region",
            "id": "region1",
            "assets": []
        }]
        
        network = Network(
            steps=24,
            shortfall_capacity=np.inf,  # Allow shortfall for empty network
            shortfall_cost=1e6,
            wastage_capacity=np.inf,  # Allow wastage for empty network
            wastage_cost=1e6
        ).from_graph(graph_from_dict(empty_graph))
        network.build()
        network.solve(solver={'_name': 'appsi_highs'})
        
        # Check no generation
        assert sum(v.sum() for k, v in network.results.items() 
                  if 'production' in k) == 0

    def test_no_load_minimal_generation(self, single_node_graph):
        """Test that network with no load has minimal generation even with free renewables"""
        # Modify generator to be renewable with zero cost
        region = next(node for node in single_node_graph["nodes"] if node["id"] == "region1")
        gen_asset = next(asset for asset in region["assets"]
                        if asset["type"] == "Producer")
        gen_asset["type"] = "renewable"
        gen_asset["operating_cost"] = 0
        
        # Remove load
        region["assets"] = [asset for asset in region["assets"]
                           if asset["type"] != "Load"]
        
        network = Network().from_graph(graph_from_dict(single_node_graph))
        network.build()
        network.solve()
        
        # Check generation is minimal
        assert sum(sum(v) for k, v in network.results.items()
                  if 'production' in k) == 0

    def test_infeasible_high_load(self, single_node_graph):
        """Test that network fails with impossibly high load"""
        region = next(node for node in single_node_graph["nodes"] if node["id"] == "region1")
        
        # Set region parameters to force infeasibility
        region["shortfall_capacity"] = 0
        region["shortfall_cost"] = 1e6
        region["wastage_capacity"] = 0
        region["wastage_cost"] = 1e6
        
        # Update load and generator
        load_asset = next(asset for asset in region["assets"] 
                         if asset["type"] == "Load")
        load_asset["profile"] = [1e12] * 24  # Very high load
        load_asset["installed_capacity"] = 1.0  # Ensure load capacity is set
        
        # Make generator capacity much smaller than load
        region["assets"] = [
            load_asset,
            {
                "type": "Producer",
                "_class": "Producer",
                "handle": "gen1",
                "installed_capacity": 1e6,  # Limited capacity
                "operating_cost": 10,
                "profile": [1.0] * 24,
                "minimum_output": 0.0
            }
        ]
        
        network = Network(
            steps=24,
            shortfall_capacity=0,  # No shortfall allowed
            shortfall_cost=1e6,
            wastage_capacity=0,  # No wastage allowed
            wastage_cost=1e6
        ).from_graph(graph_from_dict(single_node_graph))
        
        network.build()
        
        # Test should expect the infeasibility
        with pytest.raises(Exception):
            network.solve(solver={'_name': 'appsi_highs'})