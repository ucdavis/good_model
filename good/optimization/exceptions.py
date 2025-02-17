default_classes = ['Region', 'Jurisdiction', 'Producer', 'Load', 'Store', 'Line', 'RPS']
base_classes = ['Node', 'Edge', 'Asset', 'Policy']

class GOOD_ClassNotFound(Exception):

    def __init__(self):

        self.message = (
            "String does not match a default Class. " +
            f"Please choose from: {*default_classes,} " +
            "or enter a class"
            )

        super().__init__(self.message)

class GOOD_NodeNotFound(Exception):

    def __init__(self, node = ''):

        self.message = (
            f"Node {node} not found. Nodes must be added before assets which belong to them."
            )

        super().__init__(self.message)

class GOOD_InvalidBaseClass(Exception):

    def __init__(self):

        self.message = (
            f"Invalid base class. GOOD objects must have a base class from: {*base_classes,}"
            )

        super().__init__(self.message)