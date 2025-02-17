import json
from pyomo.environ import value
from src.optimization.model import OptimizationModel
from src.optimization.assets.producer import Producer
from src.optimization.assets.store import Store

class OptimizationResults:
    def __init__(self, model, network):
        self.model = model
        self.network = network
        self.results = {}
        
    def collect_generator_outputs(self):
        """Collect per-generator outputs at each timestep"""
        generator_results = {}
        
        # Iterate through all nodes
        for node_id, node_data in self.network.graph.nodes(data=True):
            node = node_data['object']
            
            # Process each generator in the node
            for asset in node.assets:
                if isinstance(asset, Producer):
                    generator_results[asset.handle] = {
                        'metadata': {
                            'type': 'renewable' if asset.renewable else 'conventional',
                            'installed_capacity': asset.installed_capacity,
                            'operating_cost': asset.operating_cost,
                            'node': node_id
                        },
                        'timeseries': {
                            'production': {},
                            'capacity_factor': {}
                        }
                    }
                    
                    # Get production variable
                    production = getattr(self.model, f"{asset.handle}::production")
                    
                    # Record production and capacity factor for each timestep
                    for t in self.model.steps:
                        prod_value = value(production[t])
                        generator_results[asset.handle]['timeseries']['production'][t] = prod_value
                        
                        # Calculate capacity factor
                        if asset.installed_capacity > 0:
                            if asset.renewable and asset.profile:
                                available = asset.profile[t] * asset.installed_capacity
                            else:
                                available = asset.installed_capacity
                            cap_factor = (prod_value / available) if available > 0 else 0
                            generator_results[asset.handle]['timeseries']['capacity_factor'][t] = cap_factor
        
        self.results['generators'] = generator_results
        return generator_results

    def collect_optimal_variables(self):
        """Collect optimization variables not in input files"""
        optimal_vars = {
            'transmission_flows': {},
            'storage_levels': {},
            'curtailment': {}
        }
        
        # Collect transmission flows
        for source, target, data in self.network.graph.edges(data=True):
            line = data['object']
            flow_var = getattr(self.model, f"{line.handle}::production")
            
            optimal_vars['transmission_flows'][f"{source}->{target}"] = {
                t: value(flow_var[t]) for t in self.model.steps
            }
            
        # Collect storage levels if any
        for node_id, node_data in self.network.graph.nodes(data=True):
            for asset in node_data['object'].assets:
                if isinstance(asset, Store):
                    level_var = getattr(self.model, f"{asset.handle}::level")
                    optimal_vars['storage_levels'][asset.handle] = {
                        t: value(level_var[t]) for t in self.model.steps
                    }
        
        self.results['optimal_variables'] = optimal_vars
        return optimal_vars

    def save_results(self, filepath):
        """Save results to JSON file"""
        if not self.results:
            self.collect_generator_outputs()
            self.collect_optimal_variables()
            
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)