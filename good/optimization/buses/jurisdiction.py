from ..base.node import Node
import pyomo.environ as pyomo

class Jurisdiction(Node):
    """
    Jurisdictions enforce renewable energy mix requirements across plants in a political unit.
    Requirements are enforced at a daily granularity.
    """

    def __init__(self, handle, **kwargs):

        super().__init__(handle, **kwargs)

        self.assets = kwargs.get('assets', [])
        self.policies = kwargs.get('policies', [])

    def parameters(self, model):

        # print(self.policies)

        # print(self.handle, len(self.assets))

        for policy in self.policies:

            model = policy['object'].parameters(model, self.assets)

        return model

    def variables(self, model):

        for policy in self.policies:

            model = policy['object'].variables(model, self.assets)

        return model

    def constraints(self, model):

        for policy in self.policies:

            model = policy['object'].constraints(model, self.assets)

        return model

    def objective(self, model):

        cost = 0

        for policy in self.policies:

            cost += policy['object'].objective(model, self.assets)

        return cost

    def results(self, model, results):

        for policy in self.policies:

            results = policy['object'].results(model, results)

        return results 
