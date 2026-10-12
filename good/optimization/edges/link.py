from ...schema import LinkParams
from ..base import Edge


class Link(Edge):
    '''
    The directed edge from one region to another. It holds the transmission
    lines between them and adds nothing to the model itself; each line's
    costs are counted once, by the line.
    '''

    Params = LinkParams
