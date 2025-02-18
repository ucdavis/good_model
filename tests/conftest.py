import pytest
import json
import os
from pathlib import Path
from good.graph import graph_from_json
from good.optimization import Network
import numpy as np
import networkx as nx

def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line(
        "markers", "optimization: mark test as an optimization test"
    )

@pytest.fixture
def empty_graph():
    return {
        "nodes": [],
        "edges": []
    }

@pytest.fixture
def single_node_graph():
    return {
        "nodes": [{
            "id": "region1",
            "type": "Region",
            "_class": "Region",
            "assets": [
                {
                    "type": "Producer",
                    "_class": "Producer",
                    "handle": "gen1",
                    "installed_capacity": 100,
                    "operating_cost": 10
                },
                {
                    "type": "Load",
                    "_class": "Load",
                    "handle": "load1",
                    "profile": [50.0] * 24
                }
            ]
        }],
        "edges": []
    }

@pytest.fixture
def two_node_graph():
    return {
        "nodes": [
            {
                "id": "region1",
                "type": "Region",
                "_class": "Region",
                "assets": [{
                    "type": "Producer",
                    "_class": "Producer",
                    "handle": "gen1",
                    "installed_capacity": 200,
                    "operating_cost": 50
                }]
            },
            {
                "id": "region2",
                "type": "Region",
                "_class": "Region",
                "assets": [{
                    "type": "Load",
                    "_class": "Load",
                    "handle": "load1",
                    "profile": [100.0] * 24
                }]
            }
        ],
        "edges": [{
            "source": "region1",
            "target": "region2",
            "type": "Line",
            "_class": "Line",
            "handle": "line1",
            "installed_capacity": 150,
            "efficiency": 0.95
        }]
    }

@pytest.fixture
def simple_network_data():
    """Create a simple two-node network with generation, load, and transmission"""
    return {
        "nodes": [
            {
                "id": "region1",
                "type": "Region",
                "_class": "Region",
                "assets": [
                    {
                        "type": "Producer",
                        "_class": "Producer",
                        "handle": "gen1",
                        "installed_capacity": 100,
                        "operating_cost": 50,
                        "profile": [1.0] * 24
                    },
                    {
                        "type": "Store",
                        "_class": "Store",
                        "handle": "storage1",
                        "installed_capacity": 50,
                        "efficiency": 0.9
                    }
                ]
            },
            {
                "id": "region2",
                "type": "Region",
                "_class": "Region",
                "assets": [
                    {
                        "type": "Load",
                        "_class": "Load",
                        "handle": "load1",
                        "profile": [80.0] * 24,
                        "shift_portion": 0.1
                    }
                ]
            }
        ],
        "edges": [
            {
                "source": "region1",
                "target": "region2",
                "type": "Line",
                "_class": "Line",
                "handle": "line1",
                "installed_capacity": 90,
                "efficiency": 0.95
            }
        ]
    }

@pytest.fixture
def simple_graph(simple_network_data):
    """Convert network data to NetworkX graph"""
    G = nx.DiGraph()
    
    # Add nodes
    for node in simple_network_data["nodes"]:
        G.add_node(node["id"], **node)
    
    # Add edges
    for edge in simple_network_data["edges"]:
        G.add_edge(edge["source"], edge["target"], **edge)
    
    return G 

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