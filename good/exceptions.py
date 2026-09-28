__all__ = [
    "GOOD_Error", "GOOD_ClassNotFound", "GOOD_NodeNotFound", "GOOD_EdgeNotFound",
    "GOOD_InvalidBaseClass", "GOOD_ValidationError", "GOOD_LegacyInput", "GOOD_SolveError",
]


class GOOD_Error(Exception):
    """Base class for GOOD errors."""


class GOOD_ClassNotFound(GOOD_Error):

    def __init__(self, name='', known=()):

        known = ', '.join(sorted(known))

        super().__init__(
            f"No GOOD component class named {name!r}. Known classes: {known}."
        )


class GOOD_NodeNotFound(GOOD_Error):

    def __init__(self, node=''):

        super().__init__(
            f"Node {node!r} not found. Add nodes before the assets that belong to them."
        )


class GOOD_EdgeNotFound(GOOD_Error):

    def __init__(self, edge=''):

        super().__init__(
            f"Edge {edge!r} not found. Add edges before the lines that belong to them."
        )


class GOOD_InvalidBaseClass(GOOD_Error):

    def __init__(self, cls=None):

        super().__init__(
            f"{cls!r} is not a Node, Edge, Asset, Line or Policy subclass."
        )


class GOOD_ValidationError(GOOD_Error):
    """Raised when component inputs fail validation. Lists every problem found."""

    def __init__(self, problems):

        self.problems = list(problems)

        shown = self.problems[:25]
        more = len(self.problems) - len(shown)

        message = f"{len(self.problems)} input problem(s):\n  - " + "\n  - ".join(shown)

        if more > 0:

            message += f"\n  ... and {more} more."

        super().__init__(message)


class GOOD_LegacyInput(GOOD_Error):
    """Raised for inputs written for GOOD 1.x."""


class GOOD_SolveError(GOOD_Error):
    """Raised when the solver does not return an optimal solution."""
