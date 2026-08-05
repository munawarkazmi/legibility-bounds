"""The one place that knows where the exact geometry comes from.

The cost-to-go, the observer and the metrics this project bounds are not
reimplemented here. They are imported from legible-motion-bench, which is
vendored as a git submodule under vendor/ and pinned to a commit.

The reason is that the whole claim rests on the cost-to-go being exact. Two
copies of that code would be two things to keep correct, and a bound is only
worth stating about the objective it is actually bounding. Importing means
the bound cannot drift from the benchmark, and the pin means a result can be
reproduced against the exact geometry it was computed with.

The pin is recorded here as well as in the git index so that a test can say
out loud which commit the numbers came from, and fail if the submodule has
been moved to another one.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = REPO_ROOT / "vendor" / "legible-motion-bench"
SCENARIO_DIR = VENDOR_ROOT / "scenarios"

# legible-motion-bench at this commit: 245 tests, eight scenarios, 46
# machine-checked properties. Every number this project reports is computed
# against this commit and no other.
PINNED_COMMIT = "a376ab28ce6cccc7a5af75fe64c06e60dd197db6"


class VendorError(RuntimeError):
    """Raised when the vendored geometry is missing or is the wrong one."""


def _ensure_on_path() -> None:
    if not VENDOR_ROOT.is_dir():
        raise VendorError(
            f"the vendored geometry is not at {VENDOR_ROOT}. This repository "
            f"carries legible-motion-bench as a submodule, so a fresh clone "
            f"needs 'git submodule update --init'."
        )
    if not (VENDOR_ROOT / "legible_motion_bench" / "__init__.py").is_file():
        raise VendorError(
            f"{VENDOR_ROOT} exists but holds no legible_motion_bench package; "
            f"the submodule is present but not checked out."
        )
    path = str(VENDOR_ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)


_ensure_on_path()

from legible_motion_bench import metrics  # noqa: E402
from legible_motion_bench.costs import (  # noqa: E402
    CostToGoIndex,
    geodesic_cost,
    straight_line_cost,
)
from legible_motion_bench.geometry import (  # noqa: E402
    ConvexPolygon,
    orientation,
    polyline_length,
    segment_segment_distance,
)
from legible_motion_bench.observer import Observer  # noqa: E402
from legible_motion_bench.world import Scenario, load_scenario  # noqa: E402

__all__ = [
    "ConvexPolygon",
    "CostToGoIndex",
    "Observer",
    "orientation",
    "PINNED_COMMIT",
    "SCENARIO_DIR",
    "Scenario",
    "VENDOR_ROOT",
    "VendorError",
    "geodesic_cost",
    "load_scenario",
    "metrics",
    "polyline_length",
    "scenario",
    "segment_segment_distance",
    "straight_line_cost",
]


def scenario(name: str) -> Scenario:
    """Load one of the vendored scenarios by id, for example 'open_pair'."""
    path = SCENARIO_DIR / f"{name}.json"
    if not path.is_file():
        available = sorted(p.stem for p in SCENARIO_DIR.glob("*.json"))
        raise VendorError(
            f"no vendored scenario named {name!r}; available: {available}"
        )
    return load_scenario(path)
