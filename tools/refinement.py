"""Does a finer lattice tighten the bound, and does it shrink the band?

    python tools/refinement.py

Two different questions, and they have different answers, which is the reason
this tool exists rather than a note in a status file.

The lattice enters the bound in two places. It sets the Lipschitz slack added
to every cell, which is half a cell diagonal times the gradient bound, and it
sets the width of the band of cells too close to an obstacle to bound
properly. Both shrink with the lattice, so the expectation before running this
was that refining would tighten the bound and narrow the band together.

The slack behaves as expected. The band does not, and the reason is
structural rather than numerical: a slice of the trajectory is decided by the
band whenever its reachable set touches an obstacle at all. Making the band
thinner does not stop lenses touching it. So the share of the bound decided
by cells capped at a belief of one is very nearly the same at every lattice,
and refining cannot fix it.

What that means for the project is that the next improvement has to be a real
bound on the belief over a cell that straddles an obstacle, rather than more
cells.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legibility_bounds import lattice as lattice_module  # noqa: E402
from legibility_bounds import vendored  # noqa: E402
from legibility_bounds.reachability import reachability_bound  # noqa: E402

DEFAULT_GRIDS = (0.05, 0.025, 0.0125, 0.00625)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "results" / "refinement.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", default="wall_choice,narrow_gap,pillar_aisle")
    parser.add_argument("--ceiling", type=float, default=1.25)
    parser.add_argument("--observer", default="geodesic")
    parser.add_argument("--grids", default=",".join(str(g) for g in DEFAULT_GRIDS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    grids = [float(g) for g in args.grids.split(",")]
    observer = vendored.Observer(condition=args.observer)
    names = [n.strip() for n in args.scenarios.split(",") if n.strip()]

    print(f"geometry:  legible-motion-bench at {vendored.PINNED_COMMIT[:7]}")
    print(f"observer:  {observer.name}")
    print(f"ceiling:   {args.ceiling}\n")

    rows = []
    for name in names:
        scenario = vendored.scenario(name)
        print(name)
        for grid in grids:
            started = time.perf_counter()
            built = lattice_module.build(scenario, observer, grid)
            build_seconds = time.perf_counter() - started
            result = reachability_bound(
                scenario, observer, args.ceiling, grid=grid, built=built
            )
            row = {
                "scenario": scenario.id,
                "ceiling": args.ceiling,
                "grid": grid,
                "cells": int(built.usable.size),
                "bound": result.bound,
                "weight_from_band": result.weight_from_band,
                "lipschitz_slack": result.lipschitz_slack,
                "band_cells": result.band_cells,
                "build_seconds": build_seconds,
            }
            rows.append(row)
            print(
                f"   grid {grid:<9} bound {result.bound:.4f}   "
                f"band {result.weight_from_band:.2f}   "
                f"slack {result.lipschitz_slack:.4f}   "
                f"cells {row['cells']:>8}   built in {build_seconds:>6.2f}s",
                flush=True,
            )

        first = [r for r in rows if r["scenario"] == scenario.id][0]
        last = [r for r in rows if r["scenario"] == scenario.id][-1]
        print(
            f"   over that refinement the bound moved {first['bound'] - last['bound']:.4f} "
            f"and the band share moved "
            f"{first['weight_from_band'] - last['weight_from_band']:.4f}\n",
            flush=True,
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "geometry_commit": vendored.PINNED_COMMIT,
                "observer": observer.name,
                "ceiling": args.ceiling,
                "rows": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
