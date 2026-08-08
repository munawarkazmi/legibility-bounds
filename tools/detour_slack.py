"""How loose is the detour constant the obstacle bound rests on?

    python tools/detour_slack.py

Cells near an obstacle are bounded through `D`, an upper bound on the geodesic
distance from a point of the cell to its centre, and the argument gives
`D <= (3 + pi) r`. That is a worst case reached by a configuration nobody has
exhibited. This measures what the geometry actually does, by sampling real
points in real band cells and computing the true geodesic with the vendored
implementation.

Two quantities are measured, because they are not the same one and an earlier
version of the constant was stated for the wrong one of them. To the centre is
what the bound claims and what `belief_bound` and `reachable` rely on: the
geodesic from a point of a cell to that cell's own lattice point. Between two
points is the geodesic between two arbitrary points of the same cell, which is
strictly harder and which nothing in the library needs. Only the first is
compared against the constant. The second is recorded because it is easy to
confuse with the first, and because it was once tested as though it were.

The gap between claim and measurement is not a defect. A bound has to hold in
the worst case and the worst case is rarely met. What the gap is worth is a
separate question and is answered in `suite_bounds.json` rather than guessed at
here: halving this constant closed 1.6 per cent of the suite's total interval
width, because twenty of the thirty two pairs have no band weight at all and
cannot move however tight it gets.

Sampling deliberately targets cells beside obstacle corners. Under the
precondition an obstacle is wider than a cell, so a point can only be separated
from its own centre where the segment between them clips a corner, and uniform
sampling almost never lands there.
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
DEFAULT_OUTPUT = ROOT / "results" / "detour_slack.json"


def measure(scenario, observer, grid, cells, pairs, rng):
    """The largest detour actually found, in units of the cell radius."""
    built = lattice_module.build(scenario, observer, grid)
    if not built.detour_certified:
        raise SystemExit(
            f"{scenario.id} does not certify the detour bound at grid {grid}, "
            f"so there is no constant to measure against"
        )
    band = np.argwhere(built.near_obstacle & built.usable)
    if not len(band):
        return None

    corners = [v for ob in scenario.obstacles for v in ob.vertices]
    centres = np.stack([
        built.x[band[:, 0], band[:, 1]], built.y[band[:, 0], band[:, 1]]
    ], axis=1)
    to_corner = np.min(np.stack([
        np.hypot(centres[:, 0] - c[0], centres[:, 1] - c[1]) for c in corners
    ]), axis=0)
    chosen = band[np.argsort(to_corner)[:cells]]

    radius = built.cell_radius
    # The cell is the square of side `grid`. The cell radius is its half
    # diagonal, so sampling offsets from the radius would cover a box 41 per
    # cent wider than the cell in each direction and report a worst case at a
    # corner no cell has. Results are still expressed in cell radii.
    half = grid / 2.0
    obstacles = scenario.obstacles

    def free(q):
        return not any(ob.contains_interior(q) for ob in obstacles)

    worst_centre = 0.0
    worst_centre_separated = 0.0
    centre_separated = 0
    points_checked = 0

    worst_pair = 0.0
    worst_pair_separated = 0.0
    pair_separated = 0
    pairs_checked = 0

    for row, col in chosen:
        cx = float(built.x[row, col])
        cy = float(built.y[row, col])
        centre = (cx, cy)
        if not free(centre):
            continue
        for _ in range(pairs):
            offsets = [float(v) for v in rng.uniform(-half, half, size=4)]
            a = (cx + offsets[0], cy + offsets[1])
            b = (cx + offsets[2], cy + offsets[3])
            if not free(a):
                continue

            # What the constant actually claims.
            to_centre = vendored.geodesic_cost(a, centre, obstacles)
            points_checked += 1
            worst_centre = max(worst_centre, to_centre / radius)
            direct = math.hypot(a[0] - cx, a[1] - cy)
            if to_centre > direct + 1e-9:
                centre_separated += 1
                worst_centre_separated = max(
                    worst_centre_separated, to_centre / radius
                )

            # The harder quantity, recorded but not compared.
            if not free(b):
                continue
            measured = vendored.geodesic_cost(a, b, obstacles)
            pairs_checked += 1
            worst_pair = max(worst_pair, measured / radius)
            straight = math.hypot(a[0] - b[0], a[1] - b[1])
            if measured > straight + 1e-9:
                pair_separated += 1
                worst_pair_separated = max(worst_pair_separated, measured / radius)
    return {
        "scenario": scenario.id,
        "grid": grid,
        "cell_radius": radius,
        "band_cells": int((built.near_obstacle & built.usable).sum()),
        "points_checked": points_checked,
        "points_separated_from_their_centre": centre_separated,
        "worst_to_centre_in_cell_radii": worst_centre,
        "worst_separated_to_centre_in_cell_radii": worst_centre_separated,
        "pairs_checked": pairs_checked,
        "pairs_separated_by_the_obstacle": pair_separated,
        "worst_pair_in_cell_radii": worst_pair,
        "worst_separated_pair_in_cell_radii": worst_pair_separated,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenarios", default="wall_choice,narrow_gap,pillar_aisle,door_pair"
    )
    parser.add_argument("--grid", type=float, default=0.05)
    parser.add_argument("--cells", type=int, default=40)
    parser.add_argument("--pairs", type=int, default=20)
    parser.add_argument("--observer", default="geodesic")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    observer = vendored.Observer(condition=args.observer)
    rng = np.random.default_rng(19)
    claimed = lattice_module.BAND_DETOUR_FACTOR

    print(f"geometry: legible-motion-bench at {vendored.PINNED_COMMIT[:7]}")
    print(f"claimed:  D <= {claimed:.4f} cell radii, point to its own centre\n")
    print(
        f"{'world':<20}{'to centre':>10}{'separated':>11}{'points':>8}"
        f"{'ratio':>8}{'pair':>8}"
    )

    rows = []
    for name in [n.strip() for n in args.scenarios.split(",") if n.strip()]:
        found = measure(
            vendored.scenario(name), observer, args.grid,
            args.cells, args.pairs, rng,
        )
        if found is None:
            continue
        found["claimed_in_cell_radii"] = claimed
        found["looseness_ratio"] = claimed / max(
            found["worst_to_centre_in_cell_radii"], 1e-9
        )
        rows.append(found)
        print(
            f"{name:<20}{found['worst_to_centre_in_cell_radii']:>10.3f}"
            f"{found['points_separated_from_their_centre']:>11}"
            f"{found['points_checked']:>8}"
            f"{found['looseness_ratio']:>8.2f}"
            f"{found['worst_pair_in_cell_radii']:>8.3f}",
            flush=True,
        )

    worst = max(r["worst_to_centre_in_cell_radii"] for r in rows)
    worst_pair = max(r["worst_pair_in_cell_radii"] for r in rows)
    record = {
        "geometry_commit": vendored.PINNED_COMMIT,
        "observer": observer.name,
        "grid": args.grid,
        "claimed_in_cell_radii": claimed,
        "worst_measured_in_cell_radii": worst,
        "worst_pair_in_cell_radii": worst_pair,
        "looseness_ratio": claimed / worst,
        "rows": rows,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    print(
        f"\nworst to its own centre: {worst:.3f} cell radii against a claimed "
        f"{claimed:.3f}, a factor of {claimed / worst:.2f}"
    )
    print(
        f"worst between two points of one cell: {worst_pair:.3f} cell radii, "
        f"which the constant does not claim and nothing here needs"
    )
    print(f"written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
