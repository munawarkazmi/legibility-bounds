"""How loose is the detour constant the obstacle bound rests on?

    python tools/detour_slack.py

Cells near an obstacle are bounded through `D`, an upper bound on the geodesic
distance from a point of the cell to its centre, and the argument gives
`D <= (3 + 2 pi) r`. That is a worst case reached by a configuration nobody has
exhibited. This measures what the geometry actually does, by sampling real
point pairs in real band cells and computing the true geodesic with the
vendored implementation.

The gap between the two is not a defect. A bound has to hold in the worst case
and the worst case is rarely met. It is reported because it is the size of the
prize: a sharper argument for the same cells would tighten every obstacle world
in the suite by roughly the ratio recorded here, and nothing else on the list
of remaining improvements is worth as much.

Sampling deliberately targets cells beside obstacle corners. Under the
precondition an obstacle is wider than a cell, so two points of one cell can
only be separated by it where the segment between them clips a corner, and
uniform sampling almost never lands there.
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
    worst = 0.0
    worst_separated = 0.0
    separated = 0
    checked = 0
    for row, col in chosen:
        cx = float(built.x[row, col])
        cy = float(built.y[row, col])
        for _ in range(pairs):
            offsets = [float(v) for v in rng.uniform(-radius, radius, size=4)]
            a = (cx + offsets[0], cy + offsets[1])
            b = (cx + offsets[2], cy + offsets[3])
            if any(ob.contains_interior(a) or ob.contains_interior(b)
                   for ob in scenario.obstacles):
                continue
            measured = vendored.geodesic_cost(a, b, scenario.obstacles)
            checked += 1
            worst = max(worst, measured / radius)
            straight = math.hypot(a[0] - b[0], a[1] - b[1])
            if measured > straight + 1e-9:
                separated += 1
                worst_separated = max(worst_separated, measured / radius)
    return {
        "scenario": scenario.id,
        "grid": grid,
        "cell_radius": radius,
        "band_cells": int((built.near_obstacle & built.usable).sum()),
        "pairs_checked": checked,
        "pairs_separated_by_the_obstacle": separated,
        "worst_detour_in_cell_radii": worst,
        "worst_separated_detour_in_cell_radii": worst_separated,
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
    print(f"claimed:  D <= {claimed:.4f} cell radii\n")
    print(f"{'world':<20}{'worst':>8}{'separated':>11}{'pairs':>8}{'ratio':>8}")

    rows = []
    for name in [n.strip() for n in args.scenarios.split(",") if n.strip()]:
        found = measure(
            vendored.scenario(name), observer, args.grid,
            args.cells, args.pairs, rng,
        )
        if found is None:
            continue
        found["claimed_in_cell_radii"] = claimed
        found["looseness_ratio"] = claimed / max(found["worst_detour_in_cell_radii"], 1e-9)
        rows.append(found)
        print(
            f"{name:<20}{found['worst_detour_in_cell_radii']:>8.3f}"
            f"{found['pairs_separated_by_the_obstacle']:>11}"
            f"{found['pairs_checked']:>8}"
            f"{found['looseness_ratio']:>8.2f}",
            flush=True,
        )

    worst = max(r["worst_detour_in_cell_radii"] for r in rows)
    record = {
        "geometry_commit": vendored.PINNED_COMMIT,
        "observer": observer.name,
        "grid": args.grid,
        "claimed_in_cell_radii": claimed,
        "worst_measured_in_cell_radii": worst,
        "looseness_ratio": claimed / worst,
        "rows": rows,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    print(
        f"\nworst measured anywhere: {worst:.3f} cell radii against a claimed "
        f"{claimed:.3f}, a factor of {claimed / worst:.2f}"
    )
    print(f"written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
