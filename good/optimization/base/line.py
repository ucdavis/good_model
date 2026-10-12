from .component import Component


class Line(Component):
    """Something on an edge that moves energy from the source to the target node."""

    def __init__(self, handle, edge=None, **kwargs):

        super().__init__(handle, **kwargs)

        self.edge = tuple(edge) if edge is not None else None

    @property
    def source(self):

        return self.edge[0]

    @property
    def target(self):

        return self.edge[1]
