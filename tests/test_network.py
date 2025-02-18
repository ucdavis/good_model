import pytest
import numpy as np
from good.optimization.network import Network

def test_basic_network_creation():
    """Test that network can be created with basic parameters"""
    network = Network(
        steps=24,
        shortfall_capacity=np.inf,
        shortfall_cost=1e3,
    )
    assert network.steps == 24
    assert network.shortfall_capacity == np.inf
    assert network.shortfall_cost == 1e3

def test_simple_graph_loading(simple_graph):
    """Test loading simple test graph"""
    network = Network().from_graph(simple_graph)
    
    # Verify basic graph properties
    assert len(network.graph.nodes) == 2
    assert len(network.graph.edges) == 1
    
    # Check that assets were properly loaded
    region1 = network.graph.nodes["region1"]
    assert len(region1["object"].assets) == 2  # Generator and Storage
    
    region2 = network.graph.nodes["region2"]
    assert len(region2["object"].assets) == 1  # Load

def test_optimization_results(simple_graph):
    """Test that optimization produces expected results structure"""
    network = Network(
        steps=24,
        shortfall_capacity=np.inf,
        shortfall_cost=1e3,
        wastage_capacity=np.inf,
        wastage_cost=1e3,
    ).from_graph(simple_graph)
    
    network.build()
    network.solve(solver={'_name': 'appsi_highs'})
    
    # Check that key result types exist
    assert any('gen1::production' in k for k in network.results.keys())
    assert any('storage1::level' in k for k in network.results.keys())
    assert any('line1::transmission' in k for k in network.results.keys())
    assert any('load1::profile' in k for k in network.results.keys())

def test_load_shifting(simple_graph):
    """Test that load shifting behaves as expected"""
    network = Network(steps=24).from_graph(simple_graph)
    network.build()
    network.solve(solver={'_name': 'appsi_highs'})
    
    # Get original and shifted load profiles
    base_load = np.array(network.results['load1::profile::base'])
    shifted_load = np.array(network.results['load1::profile::shifted'])
    
    # Total energy should be conserved
    np.testing.assert_almost_equal(base_load.sum(), shifted_load.sum())
    
    # Shifted load should differ from base load
    assert not np.array_equal(base_load, shifted_load)

def test_storage_behavior(simple_graph):
    """Test that storage facilities maintain energy balance"""
    network = Network(steps=24).from_graph(simple_graph)
    network.build()
    network.solve()
    
    # Get storage levels using handle
    levels = np.array(network.results['storage1::level'])
    
    # Check constraints
    assert np.all(levels >= 0)
    assert np.all(levels <= 50)

def test_transmission_constraints(simple_graph):
    """Test that transmission flows respect capacity limits"""
    network = Network(steps=24).from_graph(simple_graph)
    network.build()
    network.solve(solver={'_name': 'appsi_highs'})
    
    flows = np.array(network.results['line1::transmission'])
    capacity = 90  # From fixture data
    
    # Check transmission limits
    assert np.all(flows <= capacity * 1.001)  # Allow for solver tolerance
    assert np.all(flows >= 0)  # Flows should be non-negative

@pytest.mark.parametrize("shortfall_cost", [1e3, 1e6])
def test_shortfall_behavior(simple_graph, shortfall_cost):
    """Test that shortfall is minimized and priced correctly"""
    network = Network(
        steps=24,
        shortfall_capacity=np.inf,
        shortfall_cost=shortfall_cost,
    ).from_graph(simple_graph)
    
    network.build()
    network.solve(solver={'_name': 'appsi_highs'})
    
    shortfall_total = sum(
        v.sum() for k, v in network.results.items() 
        if 'shortfall' in k and isinstance(v, (np.ndarray, list))
    )
    
    # Higher shortfall cost should result in less shortfall
    assert shortfall_total >= 0
    if shortfall_cost > 1e5:
        assert shortfall_total < 1e-6  # Practically zero for high costs 