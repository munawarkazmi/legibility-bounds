"""What can be certified about every world in the suite, at every ceiling.

    python tools/suite_bounds.py

For each world and each cost ceiling this reports two numbers and the space
between them: the best legibility a search actually reached, which is a lower
bound on the optimum by construction, and an upper bound that no trajectory
within the budget can exceed.

The pair licenses a statement the sibling benchmark could not make about its
own worlds. Its status document records why:

    The optimiser is a local search. It cannot prove that no trajectory
    exists, only that it did not find one, and the two are not the same
    claim.

An upper bound of B at ceiling c means no trajectory with cost ratio at most
c reaches legibility B, whatever search anyone runs. That is a decidable
property rather than a report of what was found.

Three columns have to be read together and the tool prints them together.
`band` is the share of the bound decided by cells too close to an obstacle to
bound properly, which is the honest measure of how much of the result rests
on the one part of the argument that is loose. A world with a high band share
has a weak bound, and saying so is the point of the column.
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

from legible_motion_bench.planners.legible import LegiblePlanner  # noqa: E402
from legible_motion_bench.planners.shortest import ShortestPathPlanner  # noqa: E402

DEFAULT_CEILINGS = (1.05, 1.1, 1.25, 1.5)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "results" / "suite_bounds.json"


def _load_reusable(args, observer) -> dict:
    """Achieved values from a previous run, if they describe the same search.

    The optimiser knows nothing about the lattice, so a value it produced is
    still the value it would produce at a different one. Everything else it
    does depend on has to match exactly, and a mismatch is refused rather than
    worked around: a table whose rows came from different search settings
    would be a table of two different experiments.
    """
    path = Path(args.reuse)
    if not path.is_file():
        raise SystemExit(f"--reuse names no file: {path}")
    previous = json.loads(path.read_text(encoding="utf-8"))

    for field, mine in (
        ("geometry_commit", vendored.PINNED_COMMIT),
        ("observer", observer.name),
        ("search_budget", args.budget),
        ("waypoints", args.waypoints),
    ):
        theirs = previous.get(field)
        if theirs != mine:
            raise SystemExit(
                f"refusing to reuse {path.name}: its {field} is {theirs!r} and "
                f"this run's is {mine!r}. Achieved values are only "
                f"transferable between runs that searched the same way."
            )

    return {
        (row["scenario"], float(row["ceiling"])): row
        for row in previous.get("rows", [])
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=float, default=0.05)
    parser.add_argument("--budget", type=int, default=500)
    parser.add_argument("--waypoints", type=int, default=3)
    parser.add_argument("--observer", default="geodesic")
    parser.add_argument(
        "--ceilings", default=",".join(str(c) for c in DEFAULT_CEILINGS)
    )
    parser.add_argument("--scenarios", default="")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--reuse",
        default="",
        help=(
            "a previous results file whose achieved values may be taken "
            "rather than searched for again. The search knows nothing about "
            "the lattice, so re-running at a new lattice cannot change them, "
            "and repeating 32 searches to confirm that is most of the cost of "
            "this tool. Reuse is refused unless the geometry, observer and "
            "search settings match exactly, and every reused row is checked "
            "against a freshly computed shortest path."
        ),
    )
    args = parser.parse_args(argv)

    ceilings = [float(c) for c in args.ceilings.split(",")]
    observer = vendored.Observer(condition=args.observer)
    names = (
        [n.strip() for n in args.scenarios.split(",") if n.strip()]
        or sorted(p.stem for p in vendored.SCENARIO_DIR.glob("*.json"))
    )

    reused = _load_reusable(args, observer) if args.reuse else {}

    print(f"geometry:  legible-motion-bench at {vendored.PINNED_COMMIT[:7]}")
    print(f"observer:  {observer.name}")
    print(f"lattice:   {args.grid}")
    print(f"search:    {args.budget} evaluations, {args.waypoints} waypoints")
    if args.reuse:
        print(f"reusing:   {len(reused)} achieved values from {args.reuse}")
    print()

    header = (
        f"{'world':<20}{'ceiling':>9}{'achieved':>10}{'bound':>9}"
        f"{'gap':>8}{'band':>7}"
    )
    print(header)
    print("-" * len(header))

    rows = []
    for name in names:
        scenario = vendored.scenario(name)
        started = time.perf_counter()
        built = lattice_module.build(scenario, observer, args.grid)
        build_seconds = time.perf_counter() - started

        shortest = ShortestPathPlanner().plan(scenario)
        baseline = vendored.metrics.evaluate(scenario, observer, shortest.points)

        for ceiling in ceilings:
            result = reachability_bound(
                scenario, observer, ceiling, grid=args.grid, built=built
            )
            previous = reused.get((scenario.id, ceiling))
            if previous is None:
                plan = LegiblePlanner(
                    waypoints=args.waypoints,
                    budget=args.budget,
                    restarts=3,
                    cost_budget=ceiling,
                ).plan(scenario)
                scored = vendored.metrics.evaluate(scenario, observer, plan.points)
                achieved = max(scored.legibility, baseline.legibility)
                achieved_ratio = scored.cost_ratio
                source = "searched"
            else:
                # The stored shortest path legibility is recomputed above and
                # has to agree, which is a check that the reused row describes
                # this world rather than merely carrying its name.
                stored = previous["shortest_path_legibility"]
                if abs(stored - baseline.legibility) > 1e-12:
                    raise SystemExit(
                        f"refusing to reuse {scenario.id} at ceiling {ceiling}: "
                        f"the stored shortest path legibility is {stored!r} but "
                        f"this world scores {baseline.legibility!r}"
                    )
                achieved = previous["achieved"]
                achieved_ratio = previous["achieved_cost_ratio"]
                source = f"reused from {Path(args.reuse).name}"

            row = {
                "scenario": scenario.id,
                "ceiling": ceiling,
                "achieved": achieved,
                "achieved_cost_ratio": achieved_ratio,
                "achieved_source": source,
                "shortest_path_legibility": baseline.legibility,
                "bound": result.bound,
                "gap": result.bound - achieved,
                "weight_from_band": result.weight_from_band,
                "band_cells": result.band_cells,
                "uncertified_cells": result.uncertified_cells,
                "unusable_cells": result.unusable_cells,
                "detour_certified": result.detour_certified,
                "band_detour": result.band_detour,
                "has_obstacles": bool(scenario.obstacles),
                "lattice_build_seconds": build_seconds,
            }
            rows.append(row)
            print(
                f"{scenario.id:<20}{ceiling:>9.2f}{achieved:>10.4f}"
                f"{result.bound:>9.4f}{row['gap']:>8.4f}"
                f"{result.weight_from_band:>7.2f}",
                flush=True,
            )
            if row["gap"] < 0:
                print(
                    f"   THE BOUND IS BELOW AN ACHIEVED VALUE IN {scenario.id} "
                    f"AT CEILING {ceiling} AND IS THEREFORE WRONG",
                    flush=True,
                )
        print(flush=True)

    broken = [r for r in rows if r["gap"] < 0]
    record = {
        "geometry_commit": vendored.PINNED_COMMIT,
        "observer": observer.name,
        "grid": args.grid,
        "reused_from": args.reuse or None,
        "reused_rows": sum(1 for r in rows if r["achieved_source"] != "searched"),
        "search_budget": args.budget,
        "waypoints": args.waypoints,
        "rows": rows,
        "violations": len(broken),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    obstacle_rows = [r for r in rows if r["has_obstacles"]]
    print(f"{len(rows)} world and ceiling pairs, {len(broken)} violations")
    if obstacle_rows:
        worst = max(obstacle_rows, key=lambda r: r["weight_from_band"])
        print(
            f"largest share decided by the band: {worst['weight_from_band']:.2f} "
            f"in {worst['scenario']} at ceiling {worst['ceiling']}"
        )
    print(f"written to {output}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
