# Grid Optimized Operation Dispatch (GOOD) model

A Python-based power grid optimization framework for modeling energy systems with renewable integration and policy constraints.

## Table of Contents
- [Status & Roadmap](#status--roadmap)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Model](#running-the-model)
  - [Using Jupyter Notebook](#using-jupyter-notebook)
  - [Configuration Options](#configuration-options)
- [Project Structure](#project-structure)
- [Optimization Framework](#optimization-framework)
  - [Node Types](#node-types)
  - [Asset Types](#asset-types)
  - [Flow of Execution](#flow-of-execution)
- [Testing](#testing)
  - [Running Tests](#running-tests)
  - [Test Structure](#test-structure)
  - [Test Fixtures](#test-fixtures)
  - [Writing New Tests](#writing-new-tests)

## Status & Roadmap
- **Current State**: Development
- **Key Features**:
  - Power grid network modeling
  - Renewable integration optimization
  - Policy constraint handling
  - Multi-region transmission modeling

### High Priority TODOs
- [ ] Policy implementation from graph data (see network.py TODO)
- [ ] Improved data validation for input files
- [ ] Documentation for data file formats
- [ ] Unit test coverage
- [ ] Performance optimization for large networks

## Prerequisites

- Python 3.8+
- pip
- Jupyter Notebook

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Model

### Using Jupyter Notebook

The primary way to run the model is through the Example.ipynb notebook. The basic workflow is:

1. Import required libraries:
```python
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import good
from good.reload import deep_reload
```

2. Load and configure the network graph:
```python
deep_reload(good)
wecc = good.graph.graph_from_json('Examples/WECC.json')

# Configure load shift portions if needed
for source, node in wecc._node.items():
    for asset in node.get('assets', []):
        if asset['type'] == 'load':
            asset['shift_portion'] = .1
```

3. Build and configure the network:
```python
kw = {
    'verbose': True,
    'steps': 25,
    'shortfall_capacity': np.inf,
    'shortfall_cost': 1e3,
    'wastage_capacity': np.inf,
    'wastage_cost': 1e3,
}

network = good.optimization.network.Network(**kw).from_graph(wecc)
network.build()
```

4. Solve the optimization:
```python
kw = {
    'solver': {
        '_name': 'appsi_highs',
    },
}

network.solve(**kw)
```

5. Access results through network.results, which contains various metrics including:
- Capital expenditure (capex)
- Load profiles and shifting
- Generation profiles and production
- Storage levels
- Transmission flows between regions
- System shortfalls and wastage

Results can be accessed and scaled as needed:
```python
# View capex results
{k: v[0] / 1e6 for k, v in network.results.items() if 'capex' in k and v[0] > 0}

# View production results
{k: np.array(v) / 1e6 for k, v in network.results.items() if 'production' in k and np.array(v).sum() > 0}

# View storage levels
{k: np.array(v) / 1e6 for k, v in network.results.items() if 'level' in k and np.array(v).sum() > 0}

# View transmission flows
{k: np.array(v) / 1e6 for k, v in network.results.items() if 'transmission' in k and np.array(v).sum() > 0}
```

### Configuration Options

Key network parameters include:
- **steps**: Number of time steps to optimize (default: 25)
- **time_step**: Time step duration in seconds (default: 3600)
- **shortfall_capacity/cost**: Parameters for handling supply shortfalls
- **wastage_capacity/cost**: Parameters for handling excess generation
- **verbose**: Enable detailed output (default: False)
- **solver**: Optimization solver configuration (default: appsi_highs)

## Project Structure

- `good/`: Core source code
  - `optimization/`: Optimization model components
    - `network.py`: Core Network class managing optimization
    - `policies/`: Policy implementations (e.g., RPS)
    - `assets/`: Asset type implementations
  - `graph/`: Network graph handling and JSON I/O
  - `utilities.py`: Helper functions
- `Examples/`: Example input files and notebooks
  - `WECC.json`: Western Electricity Coordinating Council network data
  - `Example.ipynb`: Main example notebook
- `Outputs/`: Results and visualization tools
  - `output.py`: Model output processing
  - `diagnostics.py`: Analysis and visualization utilities

## Optimization Framework

### Node Types
- **Region**: Represents geographical areas containing assets.
- **Policy**: Handles renewable requirements for different jurisdictions.

Each node can contain multiple assets:
- Producers (e.g., power plants)
- Loads (e.g., power demand centers)
- Storage facilities (e.g., batteries)

### Asset Types
- **Producer**: Represents power plants with attributes like capacity, costs, and emissions.
- **Store**: Represents energy storage facilities.
- **Load**: Represents centers of power demand.
- **Line**: Represents transmission lines connecting regions.

### Optimization Model
The framework uses Pyomo for optimization. Each asset type defines:
- Variables (e.g., production levels, storage levels).
- Constraints (e.g., capacity limits, renewable requirements).
- Objective function components (e.g., costs).

### Flow of Execution
The system is modular:
- Each component (region, plant, line) defines its own optimization variables and constraints.
- The `Network` class orchestrates interactions between components.
- Policies act as cross-cutting concerns, adding constraints across multiple assets.

## Testing

The project uses pytest for testing. Tests are organized into:
- Feasibility tests (`test_feasibility.py`): Basic network operation
- Edge case tests (`test_edge_cases.py`): Boundary conditions and error cases

### Running Tests

Run all tests:
```bash
pytest
```

Run specific test categories:
```bash
pytest -v -m optimization  # Run optimization-related tests
pytest tests/test_feasibility.py  # Run feasibility tests only
```

### Test Structure

Tests use fixture data defined in `conftest.py` to create test networks:
```python
# Example test using fixtures
def test_empty_network(self, empty_graph):
    """Test that empty network has zero generation and cost"""
    network = Network().set_graph(graph_from_dict(empty_graph))
    result = network.optimize()
    assert result.objective_value == 0
```

### Test Fixtures

Common test scenarios are provided as fixtures:
- `empty_graph`: Empty network with no nodes or edges
- `single_node_graph`: Single region with generator and load
- `two_node_graph`: Two connected regions with transmission

### Writing New Tests

1. Use the provided fixtures or create new ones in `conftest.py`
2. Create network using the `Network().set_graph()` pattern:
```python
network = Network().set_graph(graph_from_dict(test_graph))
```

3. Add appropriate assertions:
```python
# Test generation matches load
assert sum(gen.production for gen in result.generators.values()) == total_load

# Test transmission limits
assert result.lines["line1"].flow <= line_capacity
```

4. Add markers for test categorization:
```python
@pytest.mark.optimization
def test_my_feature():
    ...
```

## Output Files

- `optimization_results.json`: Optimization results.
- `optimization_output.log`: Detailed logging output.
