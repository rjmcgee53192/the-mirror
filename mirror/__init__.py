"""The Mirror — a blinded testing commons for extraordinary claims."""
from .core import Experiment, MirrorError, binomial_tail, verdict_for

__all__ = ["Experiment", "MirrorError", "binomial_tail", "verdict_for"]
__version__ = "0.1.0"
