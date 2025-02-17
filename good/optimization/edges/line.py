from ..base.edge import Edge
import pyomo.environ as pyomo

class Line(Edge):
    '''
    Links enable transfer of energy between nodes. Each link has exactly one source node
    and exactly one target node with energy transferred from source to target.
    '''
    def __init__(self, handle, **kwargs):

        super().__init__(handle, **kwargs)
        
        self.installed_capacity = kwargs.get('installed_capacity', 0)
        self.operating_cost = kwargs.get('operating_cost', 0)
        self.efficiency = kwargs.get('efficiency', 1)

        # Can capacity be expanded
        self.capex_limit = kwargs.get('capex_limit', 0)
        self.capex_cost = kwargs.get('capex_cost', 0)
        self.extensible = self.capex_limit > 0

    def parameters(self, model):

        # Capacity Expansion
        if not self.extensible:

            handle = f"{self.handle}::capex"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Param(initialize = 0),
            )

        return model

    def variables(self, model):

        # Production (transmission flow)
        handle = f"{self.handle}::transmission"
        self.handles.append(handle)
        setattr(
            model, handle,
            pyomo.Var(
                model.steps,
                initialize = [0] * len(model.steps),
                within = pyomo.NonNegativeReals
                ),
            )

        # Capacity Expansion
        if self.extensible:

            handle = f"{self.handle}::capex"
            self.handles.append(handle)
            setattr(
                model, handle,
                pyomo.Var(
                    initialize = 0,
                    bounds = (0, self.capex_limit), within = pyomo.NonNegativeReals,
                    ),
                )

        return model

    def constraints(self, model):

        # Capacity constraint
        transmission = getattr(model, f"{self.handle}::transmission")
        capex = getattr(model, f"{self.handle}::capex")
        
        setattr(
            model, f"{self.handle}::capacity_constraint",
            pyomo.Constraint(
                model.steps,
                rule=lambda m, t: transmission[t] <= self.installed_capacity + capex
            )
        )
        
        return model

    def transmit(self, model, step = None):

        transmission = getattr(model, f"{self.handle}::transmission")

        if step is None:

            energy = pyomo.quicksum(
                transmission[i] * model.time_step for i in model.steps
            )

        else:

            energy = transmission[step] * model.time_step

        return energy

    def receive(self, model, step = None):

        transmission = getattr(model, f"{self.handle}::transmission")

        if step is None:

            energy = pyomo.quicksum(
                transmission[i] * model.time_step * self.efficiency for i in model.steps
            )

        else:

            energy = transmission[step] * model.time_step * self.efficiency

        return energy

    def capacity(self, model, step = None):

        capex = getattr(model, f"{self.handle}::capex")

        capacity = self.installed_capacity + capex

        return capacity

    def objective(self, model):
        """
        Calculate the cost of transmission
        """

        transmission = getattr(model, f"{self.handle}::transmission")

        transmission_cost =  pyomo.quicksum(
            transmission[t] * model.time_step * self.operating_cost for t in model.steps
        )

        capex = getattr(model, f"{self.handle}::capex")

        expansion_cost = capex * self.capex_cost

        cost = transmission_cost + expansion_cost

        return cost