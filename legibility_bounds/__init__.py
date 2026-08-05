"""Certified two-sided bounds on legibility under a path cost budget.

What this package computes, for a world, a cost ceiling and a stated
observer, is a pair of numbers: a trajectory that achieves legibility L_low,
and an argument that no trajectory inside the budget exceeds L_high. The gap
between them is reported rather than hidden, because a bound whose gap is not
stated says nothing about how much room is left.

The objective is not defined here. It is the legibility of Dragan, Lee and
Srinivasa as implemented in legible-motion-bench, imported through
`vendored` and pinned to a commit. This project bounds that objective and
does not redefine it.
"""

from .vendored import PINNED_COMMIT, VENDOR_ROOT, VendorError, scenario

__all__ = ["PINNED_COMMIT", "VENDOR_ROOT", "VendorError", "scenario"]
