from ..base.edge import Edge
import pyomo.environ as pyomo

class Link(Edge):
    '''
    Links enable transfer of energy between nodes. Each link has exactly one source node
    and exactly one target node with energy transferred from source to target.
    '''
    def __init__(self, handle, **kwargs):

        super().__init__(handle, **kwargs)

        self.lines = kwargs.get('lines', {})

    def parameters(self, model):

        for line in self.lines.values():

            model = line['object'].parameters(model)

        return model

    def variables(self, model):

        for line in self.lines.values():

            model = line['object'].variables(model)

        return model

    def constraints(self, model):
        """Energy balance constraints"""

        for line in self.lines.values():

            model = line['object'].constraints(model)

        return model

    def objective(self, model):
        """Sum the objectives of all lines"""

        cost = sum(
            line['object'].objective(model) for line in self.lines.values()
            )

        return cost