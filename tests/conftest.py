import networkx as nx
import pytest


@pytest.fixture
def two_regions():
    """Cheap generation in B, expensive generation and demand in A, two directed lines."""

    graph = nx.DiGraph()
    graph.add_node("A", _class="Region", assets={
        "peaker": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 80},
        "demand": {"_class": "Load", "installed_capacity": 60},
    })
    graph.add_node("B", _class="Region", assets={
        "base": {"_class": "Producer", "installed_capacity": 100, "operating_cost": 20},
    })

    line = {"_class": "Transmission", "installed_capacity": 40, "efficiency": 0.95}
    graph.add_edge("B", "A", _class="Link", lines={"ba": dict(line)})
    graph.add_edge("A", "B", _class="Link", lines={"ab": dict(line)})

    return graph
