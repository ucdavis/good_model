from .component import Component


class Node(Component):
    """A location that balances energy: the nodes of the power system graph."""

    def __init__(self, handle, **kwargs):

        super().__init__(handle, **kwargs)

        self.assets = {}
