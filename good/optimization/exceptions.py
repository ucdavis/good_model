class GOOD_ClassNotFound(Exception):

    def __init__(self):

        self.message = (
            "String does not match a default Class."
            )

        super().__init__(self.message)

class GOOD_NodeNotFound(Exception):

    def __init__(self, node = ''):

        self.message = (
            f"Node {node} not found. Nodes must be added before assets which belong to them."
            )

        super().__init__(self.message)

class GOOD_EdgeNotFound(Exception):

    def __init__(self, edge = ''):

        self.message = (
            f"Edge {edge} not found. Edges must be added before assets which belong to them."
            )

        super().__init__(self.message)

class GOOD_InvalidBaseClass(Exception):

    def __init__(self):

        self.message = (
            f"Invalid base class"
            )

        super().__init__(self.message)