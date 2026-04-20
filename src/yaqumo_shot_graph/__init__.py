"""yaqumo-shot-graph — typed shot-graph IR + heterogeneous-backend compiler.

"""
__version__ = "0.0.1"

from yaqumo_shot_graph.ir.graph import ShotGraph  # re-export for ergonomics
from yaqumo_shot_graph.ir import nodes

__all__ = ["ShotGraph", "nodes", "__version__"]
