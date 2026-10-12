from ...schema import PortfolioStandardParams
from ..base import Policy


class Portfolio_Standard(Policy):
    '''
    A generation-share requirement such as a renewable portfolio standard:

        included_generation + non_compliance >= ratio * (included_generation + excluded_generation)

    over the model horizon, in MWh. ``include`` and ``exclude`` are attribute
    filters (see :mod:`good.criteria`); an asset matching both counts as
    included. Only assets that generate (producers and stores) contribute.
    '''

    Params = PortfolioStandardParams

    def build_one(self, net):

        include = self.select(net, self.p.include)
        included = {h for handles in include.values() for h in handles}

        exclude = {}

        if self.p.exclude is not None:

            exclude = self.select(net, self.p.exclude)
            exclude = {cls: [h for h in hs if h not in included] for cls, hs in exclude.items()}

        qualifying = self.generation(net, include)
        other = self.generation(net, exclude)
        slack = self.non_compliance(net)

        ratio = self.p.ratio

        net.add_policy_constraint(
            qualifying * (1 - ratio) - other * ratio + slack >= 0, name=f"Portfolio_Standard-{self.handle}"
        )
