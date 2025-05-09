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

    Shortfall/wastage are included as a supplemental factor that allows for up to a 
    certain amount of wiggle room in the energy balance constraint and should receive a
    very high cost such that it will only be used if needed.

    The limits of shortfall are  [0, shortfall_capacity]
    The cost of shortfall is shortfall_cost

    The limits of wastage are  [0, wastage_capacity]
    The cost of wastage is wastage_cost
    '''
    def __init__(self, handle, **kwargs):
        
        super().__init__(handle, **kwargs)

        self.assets = kwargs.get('assets', {})
        self.imports = kwargs.get('imports', {})
        self.exports = kwargs.get('exports', {})

        self.shortfall_capacity = kwargs.get('shortfall_capacity', 0)
        self.shortfall_cost = kwargs.get('shortfall_cost', 1)

        self.wastage_capacity = kwargs.get('wastage_capacity', 0)
        self.wastage_cost = kwargs.get('wastage_cost', 1)

    def parameters(self, model):

        for asset in self.assets.values():

            model = asset['object'].parameters(model)

        return model

    def variables(self, model):

        for asset in self.assets.values():

            model = asset['object'].variables(model)

        # Shortfall - avoids infeasibility due to insufficient supply
        handle = f"{self.handle}::shortfall"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Var(
                model.steps,
                initialize = [0] * len(model.steps),
                bounds = (0, self.shortfall_capacity),
                ),
            )

        # Wastage - avoids infeasibility due to excess supply
        handle = f"{self.handle}::wastage"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Var(
                model.steps,
                initialize = [0] * len(model.steps),
                bounds = (0, self.wastage_capacity),
                ),
            )

        return model

    def constraints(self, model):
        """Energy balance constraints"""

        for asset in self.assets.values():

            model = asset['object'].constraints(model)

        # Add constraints for all time steps
        for step in model.steps:

            # Energy
            asset_net_energy = sum(
                asset['object'].energy(model, step) for asset in self.assets.values()
            )

            imported_energy = sum(
                import_edge['object'].receive(model, step) \
                for import_edge in self.imports.values()
                )

            exported_energy = sum(
                export_edge['object'].transmit(model, step) \
                for export_edge in self.exports.values()
                )

            shortfall = getattr(model, f"{self.handle}::shortfall")[step]
            wastage = getattr(model, f"{self.handle}::wastage")[step]
            
            net_energy = (
                asset_net_energy + imported_energy -
                exported_energy + shortfall - wastage
                )
            
            if not isinstance(asset_net_energy, float):

                setattr(
                    model, f"{self.handle}::balance:{step}",
                    pyomo.Constraint(expr = net_energy == 0)
                )

        return model

    def objective(self, model):
        """Sum the objectives of all assets"""

        net_asset_cost = sum(
            asset['object'].objective(model) for asset in self.assets.values()
            )

        imports_cost = sum(
            import_edge['object'].objective(model) for \
            import_edge in self.imports.values()
            )

        exports_cost = sum(
            export_edge['object'].objective(model) for \
            export_edge in self.exports.values()
            )

        shortfall_cost = sum(
            getattr(model, f"{self.handle}::shortfall")[step] for step in model.steps
            ) * self.shortfall_cost

        wastage_cost = sum(
            getattr(model, f"{self.handle}::wastage")[step] for step in model.steps
            ) * self.wastage_cost

        cost = (
            net_asset_cost + imports_cost - exports_cost + shortfall_cost + wastage_cost
            )

        return cost

    def results(self, model, results):

        local_results = {}

        for handle in self.handles:

            value = list(getattr(model, handle).extract_values().values())
            local_results[handle.split('::')[1]] = value

        local_results['assets'] = {}

        for asset in self.assets.values():

            local_results['assets'] = asset['object'].results(
                model, local_results['assets']
                )

        if hasattr(model, 'dual'):

            handle = f"{self.handle}::balance"

            duals = {str(k): model.dual[k] for k in model.dual.keys()}

            local_results['clearing_price'] = (
                [v for k, v in duals.items() if handle in k]
                )

        results[self.handle] = local_results

        return results

    def solution(self, model):

        solution = {}

        for handle in self.handles:

            value = list(getattr(model, handle).extract_values().values())
            solution[handle.split('::')[1]] = value

        # solution['assets'] = {}

        # for key, asset in self.assets.items():

        #     solution['assets'][key] = asset['object'].solution(model)

        if hasattr(model, 'dual'):

            handle = f"{self.handle}::balance"

            duals = {str(k): model.dual[k] for k in model.dual.keys()}

            solution['clearing_price'] = (
                [v for k, v in duals.items() if handle in k]
                )

        return solution