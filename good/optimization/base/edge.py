from .component import Component


class Edge(Component):
    """A directed connection between two nodes. Holds lines."""

    def __init__(self, handle, source=None, target=None, **kwargs):

        super().__init__(handle, **kwargs)

        self.source = source
        self.target = target
        self.lines = {}
