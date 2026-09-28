from ... import criteria
from .component import Component


class Policy(Component):
    """A constraint on a set of assets, possibly spanning several nodes.

    Asset sets are chosen with attribute filters (see :mod:`good.criteria`),
    so a policy can follow jurisdictions that do not line up with balancing
    regions. Policies build one instance at a time; there are few of them.
    """

    def select(self, net, spec):
        """Handles of assets matching ``spec``, grouped by asset class."""

        handles = criteria.select(net.asset_attributes, spec)

        return net.group_handles(handles)

    @staticmethod
    def total(parts):
        """Sum a list of scalar expressions and numbers."""

        total = 0.0

        for part in parts:

            total = part + total if not isinstance(part, (int, float)) else total + part

        return total

    def generation(self, net, grouped):

        return self.total(cls.generation(net, handles) for cls, handles in grouped.items())

    def capacity(self, net, grouped, weight=lambda o: 1.0):

        return self.total(cls.capacity(net, handles, weight) for cls, handles in grouped.items())

    def demand(self, net, grouped):

        return self.total(cls.demand(net, handles) for cls, handles in grouped.items())

    @classmethod
    def build(cls, net, objs):

        for obj in objs:

            obj.build_one(net)

    def build_one(self, net):
        """Add this policy's constraints."""

    def non_compliance(self, net):
        """Scalar slack variable, bounded by non_compliance_capacity and priced in the objective."""

        var = net.model.add_variables(
            lower=0, upper=self.p.non_compliance_capacity, name=f"{type(self).__name__}-{self.handle}-non_compliance"
        )

        net.add_cost(var * self.p.non_compliance_cost)

        return var

    @classmethod
    def solution(cls, net, objs):

        out = {}

        for o in objs:

            var = net.model.variables[f"{cls.__name__}-{o.handle}-non_compliance"]

            out[o.handle] = {"non_compliance": [float(var.solution.values)]}

        return out
