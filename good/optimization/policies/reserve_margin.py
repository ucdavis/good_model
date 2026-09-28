from ...schema import ReserveMarginParams
from ..base import Policy


class Reserve_Margin(Policy):
    '''
    A planning reserve margin against peak demand:

        sum(capacity_credit * capacity of supply assets) + non_compliance >= (1 + margin) * max_t demand[t]

    ``supply`` and ``demand`` are attribute filters. Each supply asset counts
    its ``capacity_credit`` (default 1.0) times its capacity, so wind, solar
    and storage should be given credits below 1. Demand is the base demand
    of the matching loads, before any flexible shifting.
    '''

    Params = ReserveMarginParams

    def build_one(self, net):

        supply = self.capacity(
            net, self.select(net, self.p.supply), weight=lambda o: getattr(o.p, "capacity_credit", 1.0)
        )
        demand = self.demand(net, self.select(net, self.p.demand))

        # Credited capacity does not vary by step, so the peak step is the only one that can bind.
        if hasattr(demand, "max"):

            demand = float(demand.max())

        slack = self.non_compliance(net)

        net.add_policy_constraint(
            supply + slack >= (1 + self.p.margin) * demand, name=f"Reserve_Margin-{self.handle}"
        )
