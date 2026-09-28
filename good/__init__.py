'''
GOOD: Grid Optimized Operation Dispatch.

A linear economic-dispatch and capacity-expansion model for zonal power
systems. Models are built with linopy and solved with HiGHS by default.
'''

__version__ = "2.0.0"

from . import utilities  # Generally useful stuff
from . import progress_bar  # Progress bar for status tracking
from . import graph  # Graph utilities not in NetworkX
from . import economics  # Capital cost annualization
from . import criteria  # Attribute filters for policies
from . import schema  # Input validation
from . import aggregate  # Aggregate assets to reduce problem complexity
from . import migrate  # Convert GOOD 1.x graphs and policies
from . import optimization  # Building and running the model
from .optimization import Network


def __getattr__(name):

    # Plotting needs matplotlib, which is optional, so load it on first use.
    if name == "visualization":

        import importlib

        return importlib.import_module(".visualization", __name__)

    raise AttributeError(f"module 'good' has no attribute {name!r}")
