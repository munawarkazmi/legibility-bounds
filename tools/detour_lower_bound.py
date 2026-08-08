"""How much of the detour constant could any argument recover?

    python tools/detour_lower_bound.py

The wrapping constant is an upper bound: `D <= (3 + pi) r` for a cell that
holds an obstacle corner. `detour_slack.py` measures how loose that is against
the worlds in the suite, which answers "how much slack is there here" and not
"how much of it could ever be removed". Those are different questions and only
the second one bounds what a sharper argument is worth.

This answers the second. It exhibits a single configuration, admissible under
exactly the precondition the bound assumes, in which the true geodesic from a
point of a cell to that cell's own lattice point is more than three and a half
cell radii. No constant below that can hold, so the whole of the available
improvement is the ratio between it and `(3 + pi)`.

What makes the configuration admissible matters, because it is the part that
would be easy to get wrong. The precondition `cells_certified` enforces is that
no obstacle passes clean through the cell and that no cell meets two obstacles.
It does not require an obstacle to be wider than a cell: that test was tried
and withdrawn, since minimum width is global and a sharp vertex can be thinner
than a cell while the polygon is far wider. The obstacle below is thinner than
a cell and would have failed the withdrawn test. It passes the one actually in
force, which is why it bounds the constant actually in use.

Nothing here is asserted. The obstacle is built with the vendored polygon type,
the precondition is decided by `lattice.cells_certified` rather than by a local
reimplementation, and the distance is computed by `vendored.geodesic_cost`, the
same exact visibility-graph routine every other number in this repository
rests on.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legibility_bounds import lattice as lattice_module  # noqa: E402
from legibility_bounds import vendored  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results" / "detour_lower_bound.json"

# The cell is taken to have radius one, so every length below is already in
# cell radii and the lattice point is the origin. Found by maximising the true
# geodesic over convex obstacles and over the point, then verified here.
CELL_RADIUS = 1.0
LATTICE_POINT = (0.0, 0.0)
OBSTACLE = (
    (-1.9001, -1.0448),
    (0.8577, -0.5141),
    (0.8763, 0.4817),
)
POINT = (-0.6055, -0.7958)


def measure() -> dict:
    obstacle = vendored.ConvexPolygon(id="lower_bound", vertices=OBSTACLE)

    px = np.array([[LATTICE_POINT[0]]])
    py = np.array([[LATTICE_POINT[1]]])
    certified = bool(
        lattice_module.cells_certified(px, py, [obstacle], CELL_RADIUS)[0, 0]
    )

    measured = vendored.geodesic_cost(POINT, LATTICE_POINT, [obstacle])
    direct = math.hypot(
        POINT[0] - LATTICE_POINT[0], POINT[1] - LATTICE_POINT[1]
    )
    claimed = lattice_module.BAND_DETOUR_FACTOR

    return {
        "geometry_commit": vendored.PINNED_COMMIT,
        "cell_radius": CELL_RADIUS,
        "lattice_point": list(LATTICE_POINT),
        "point": list(POINT),
        "obstacle": [list(v) for v in OBSTACLE],
        "cell_certifies_the_precondition": certified,
        "lattice_point_is_free": not obstacle.contains_interior(LATTICE_POINT),
        "point_is_free": not obstacle.contains_interior(POINT),
        "point_is_within_the_cell": direct <= CELL_RADIUS + 1e-9,
        "distance_from_the_lattice_point": direct,
        "obstacle_minimum_width": lattice_module.minimum_width(obstacle),
        "obstacle_is_thinner_than_the_cell": (
            lattice_module.minimum_width(obstacle) < 2.0 * CELL_RADIUS
        ),
        "geodesic_in_cell_radii": measured / CELL_RADIUS,
        "claimed_in_cell_radii": claimed,
        "recoverable_ratio": claimed / (measured / CELL_RADIUS),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    found = measure()

    problems = []
    if not found["cell_certifies_the_precondition"]:
        problems.append("the cell does not certify, so this bounds nothing")
    if not found["lattice_point_is_free"]:
        problems.append("the lattice point is inside the obstacle")
    if not found["point_is_free"]:
        problems.append("the point is inside the obstacle")
    if not found["point_is_within_the_cell"]:
        problems.append("the point lies outside the cell")
    if found["geodesic_in_cell_radii"] >= found["claimed_in_cell_radii"]:
        problems.append("the geodesic exceeds the claimed bound, which is a "
                        "violation and not a lower bound")

    print(f"geometry: legible-motion-bench at {vendored.PINNED_COMMIT[:7]}\n")
    print(f"  cell certifies the precondition   "
          f"{found['cell_certifies_the_precondition']}")
    print(f"  lattice point free                {found['lattice_point_is_free']}")
    print(f"  point free                        {found['point_is_free']}")
    print(f"  point within the cell             "
          f"{found['point_is_within_the_cell']} "
          f"(at {found['distance_from_the_lattice_point']:.4f} radii)")
    print(f"  obstacle minimum width            "
          f"{found['obstacle_minimum_width']:.4f} radii, thinner than the cell: "
          f"{found['obstacle_is_thinner_than_the_cell']}")
    print()
    print(f"  geodesic to the lattice point     "
          f"{found['geodesic_in_cell_radii']:.4f} cell radii")
    print(f"  claimed bound                     "
          f"{found['claimed_in_cell_radii']:.4f} cell radii")
    print(f"  available to any sharper argument "
          f"{found['recoverable_ratio']:.4f}x")

    if problems:
        print("\nthis configuration establishes nothing:")
        for p in problems:
            print(f"   {p}")
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(found, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
