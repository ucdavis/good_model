from ...schema import CapacityTargetParams
from ..base import Policy


class Capacity_Target(Policy):
    '''
    A minimum on the total capacity (MW) of the included assets, existing plus new:

        included_capacity + non_compliance >= target
    '''

    Params = CapacityTargetParams

    def build_one(self, net):

        capacity = self.capacity(net, self.select(net, self.p.include))
        slack = self.non_compliance(net)

        net.add_policy_constraint(capacity + slack >= self.p.target, name=f"Capacity_Target-{self.handle}")
