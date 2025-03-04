from ..base.node import Node
from ..assets.load import Load
from ..assets.producer import Producer
import pyomo.environ as pyomo

class Region(Node):
    '''
    Nodes are the fundamental unit of analysis for the optimization. Nodes host assets
    and link terminals whose outputs must be balanced. The balancing constraint is nodal.

    Regions enforce energy balance at each time step. This can be enforced rigidly or
    permissively depending on shortfall and wastage parameters.

    Shortfall/wastage are included as a supplemental factor that allows for up to a certain
    amount of wiggle room in the energy balance constraint and should receive a very high cost
    such that it will only be used if needed.

    The limits of shortfall are  [0, shortfall_capacity]
    The cost of shortfall is shortfall_cost

    The limits of wastage are  [0, wastage_capacity]
    The cost of wastage is wastage_cost
    '''
    def __init__(self, handle, **kwargs):
        
        super().__init__(handle, **kwargs)

        self.assets = kwargs.get('assets', [])
        self.imports = kwargs.get('imports', [])
        self.exports = kwargs.get('exports', [])

        self.shortfall_capacity = kwargs.get('shortfall_capacity', 0)
        self.shortfall_cost = kwargs.get('shortfall_cost', 1)

        self.wastage_capacity = kwargs.get('wastage_capacity', 0)
        self.wastage_cost = kwargs.get('wastage_cost', 1)

    def parameters(self, model):

        for asset in self.assets:

            model = asset['object'].parameters(model)

        return model

    def variables(self, model):
        """Define variables for the region"""
        
        # Define shortfall and wastage variables for each time step with proper bounds
        model.add_component(
            f"{self.handle}::shortfall",
            pyomo.Var(model.steps, domain=pyomo.NonNegativeReals, 
                     bounds=(0, self.shortfall_capacity))
        )
        
        model.add_component(
            f"{self.handle}::wastage",
            pyomo.Var(model.steps, domain=pyomo.NonNegativeReals,
                     bounds=(0, self.wastage_capacity))
        )
        
        # Initialize variables to zero
        for step in model.steps:
            getattr(model, f"{self.handle}::shortfall")[step] = 0
            getattr(model, f"{self.handle}::wastage")[step] = 0
        
        for asset in self.assets:
            model = asset['object'].variables(model)

        return model

    def constraints(self, model):
        """Energy balance constraints"""
        
        for asset in self.assets:
            model = asset['object'].constraints(model)
        
        # Add constraints for all time steps
        for step in model.steps:
            # Energy
            asset_net_energy = sum(
                asset['object'].energy(model, step) for asset in self.assets 
            )
            
            imported_energy = sum(
                import_edge['object'].receive(model, step) for import_edge in self.imports
                )
            
            exported_energy = sum(
                export_edge['object'].transmit(model, step) for export_edge in self.exports
                )
            
            shortfall = getattr(model, f"{self.handle}::shortfall")[step]
            wastage = getattr(model, f"{self.handle}::wastage")[step]
            
            # Energy balance constraint
            net_energy = (
                asset_net_energy + imported_energy - exported_energy + shortfall - wastage
                )
            
            # Always add the energy balance constraint
            setattr(
                model, f"{self.handle}::balance:{step}",
                pyomo.Constraint(expr = net_energy == 0)
            )
        
        return model

    def objective(self, model):
        """Sum the objectives of all assets"""

        net_asset_cost = sum(asset['object'].objective(model) for asset in self.assets)

        imports_cost = sum(
            import_edge['object'].objective(model) for import_edge in self.imports
            )

        exports_cost = sum(
            export_edge['object'].objective(model) for export_edge in self.exports
            )

        shortfall_cost = sum(
            getattr(model, f"{self.handle}::shortfall")[step] for step in model.steps
            ) * self.shortfall_cost

        wastage_cost = sum(
            getattr(model, f"{self.handle}::wastage")[step] for step in model.steps
            ) * self.wastage_cost

        cost = net_asset_cost + imports_cost - exports_cost + shortfall_cost + wastage_cost

        return cost

    def results(self, model, results):

        for handle in self.handles:

            value = list(getattr(model, handle).extract_values().values())
            results[handle] = value

        for asset in self.assets:

            results = asset['object'].results(model, results)

        return results 