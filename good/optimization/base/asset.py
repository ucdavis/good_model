from .component import Component


class Asset(Component):
    """Something inside a node that produces, consumes or stores energy.

    Besides ``build`` and ``solution``, asset classes expose three class
    methods that policies use. Each takes the handles of the selected assets
    of this class:

    * ``generation(net, handles)``: total energy produced (MWh), a scalar
      linopy expression or 0.
    * ``capacity(net, handles, weight)``: total capacity (MW) weighted per
      asset by ``weight(obj)``, a scalar expression or number.
    * ``demand(net, handles)``: total demand per step (MW), a time-indexed
      DataArray or 0.
    """

    def __init__(self, handle, node=None, **kwargs):

        super().__init__(handle, **kwargs)

        self.node = node

    @classmethod
    def generation(cls, net, handles):

        return 0.0

    @classmethod
    def capacity(cls, net, handles, weight=lambda o: 1.0):

        return 0.0

    @classmethod
    def demand(cls, net, handles):

        return 0.0
