# Grid Optimized Operation Dispatch (GOOD) model

A Python-based power grid optimization framework for modeling energy systems with renewable integration and policy constraints.

# NOTE THAT THIS IS OUT OF DATE AND NEEDS UPDATING - SEE Example.ipynb

## Table of Contents
- [Status & Roadmap](#status--roadmap)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Network](#running-the-network)
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
- (optional) Jupyter Notebook

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

## Running the Network

1. Configure your settings in `config.py`:
```python
# Edit regions of interest
REGIONS = ['ERC_FRNT', 'ERC_PHDL', 'ERC_REST', 'ERC_WEST']

# Adjust time window
START_HOUR = 0  # Start hour of the year (0-8759)
NUM_HOURS = 24  # Number of hours to optimize

# Modify paths if needed
INPUT_GRAPH_PATH = 'Data/Default/US/graph.json'
```

2. Run the optimization:
```bash
python run_network.py
```

3. Check the outputs:
- Results will be saved to `optimization_results.json` (configurable in config.py)
- Logs will be written to `optimization_output.log`
- Enable DEBUG_MODE in config.py for additional output

### Configuration Options

The `config.py` file allows you to customize:
- **Regions**: Which geographical areas to include
- **Time Window**: Start time and duration of optimization
- **Network Parameters**: Line efficiency and other technical parameters
- **Input/Output**: File paths for data, logs, and results
- **Debug Settings**: Toggle detailed debug output

### Breakdown: `test_network.py`

```python
# Load a pre-built graph
graph = graph_from_json('Data/Default/US/graph.json')

# Create a subgraph for specific regions
regions = ['ERC_FRNT', 'ERC_PHDL', 'ERC_REST', 'ERC_WEST']
sub_g = subgraph(graph, regions)

# Create optimization network
network = Network()
network.add_plants(plants)  # Add plant data

# Define time window
time_steps = range(24)  # 24-hour optimization

# Create and solve optimization
opt_model = OptimizationModel(network, time_steps)
results = opt_model.solve()
```

## Project Structure

- `src/`: Core source code
  - `optimization/`: Optimization model components
    - `network.py`: Core class managing the optimization network structure
      - Uses NetworkX's `DiGraph` to represent the power grid
      - Handles nodes (regions, policies) and edges (transmission lines)
      - Manages policies and plant assignments
    - `base/` and `buses/`:
      - `Region`: Represents geographical areas containing assets
      - `Policy`: Handles renewable requirements for different jurisdictions
    - `assets/`:
      - `Producer`: Power plants with capacity, costs, emissions
      - `Store`: Energy storage facilities
      - `Load`: Power demand centers
      - `Line`: Transmission lines connecting regions
    - `model.py`:
      - Uses Pyomo for optimization
      - Defines variables, constraints, and objective function components for each asset type
  - `graph/`: Network graph handling
  - `inputs/`: Data processing utilities
- `Data/`: Input data files

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