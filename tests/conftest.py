import pytest
import json
import os
from pathlib import Path
from src.graph.graph import graph_from_json
from src.optimization import Network

def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line(
        "markers", "optimization: mark test as an optimization test"
    )

@pytest.fixture
def empty_graph():
    return {
        "nodes": {},
        "edges": {}
    }

@pytest.fixture
def single_node_graph():
    return {
        "nodes": {
            "region1": {
                "generators": [{
                    "id": "gen1",
                    "type": "conventional",
                    "capacity": 100,
                    "operating_cost": 10
                }],
                "loads": [{
                    "id": "load1",
                    "demand": 50
                }]
            }
        },
        "edges": {}
    }

@pytest.fixture
def two_node_graph():
    return {
        "nodes": {
            "region1": {
                "generators": [{
                    "id": "gen1",
                    "type": "conventional", 
                    "capacity": 200,
                    "operating_cost": 50
                }],
                "loads": []
            },
            "region2": {
                "generators": [],
                "loads": [{
                    "id": "load1",
                    "demand": 100
                }]
            }
        },
        "edges": {
            "line1": {
                "from": "region1",
                "to": "region2",
                "capacity": 150
            }
        }
    } 