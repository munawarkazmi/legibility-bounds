"""What respecting a keep-out zone certifiably costs in legibility.

    python tools/safety_price.py

The sibling benchmark measures the trade between clarity and safety by
running two searches and comparing what they found. That comparison cannot
say the constraint costs anything: a search that did worse under a constraint
may have been a worse search.

Two of the numbers here are of different kinds and putting them together is
the point.

  free achieved   a trajectory that exists, within the cost budget, scored by
                  the vendored metric. It may cross a keep-out zone.
  safe bound      an upper bound no trajectory within the budget can pass if
                  it never enters a keep-out zone.

When the first exceeds the second, the gap between them is a certified lower
bound on what safety costs: something is achievable, and nothing safe can
match it. That is a statement about every trajectory rather than about the
two a search happened to return.

Where the first does not exceed the second, nothing is certified, and the row
says so rather than reporting a negative price as though it were a finding.
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
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "results" / "safety_price.json"


def _search(scenario, observer, ceiling, budget, waypoints, respect):
    plan = LegiblePlanner(
        waypoints=waypoints,
        budget=budget,
        restarts=3,
        cost_budget=ceiling,
        respect_keep_out=respect,
    ).plan(scenario)
    return vendored.metrics.evaluate(scenario, observer, plan.points)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", type=float, default=0.025)
    parser.add_argument("--budget", type=int, default=500)
    parser.add_argument("--waypoints", type=int, default=3)
    parser.add_argument("--observer", default="geodesic")
    parser.add_argument(
        "--ceilings", default=",".join(str(c) for c in DEFAULT_CEILINGS)
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    ceilings = [float(c) for c in args.ceilings.split(",")]
    observer = vendored.Observer(condition=args.observer)
    names = [
        p.stem
        for p in sorted(vendored.SCENARIO_DIR.glob("*.json"))
        if vendored.scenario(p.stem).keep_out_zones
    ]

    print(f"geometry:  legible-motion-bench at {vendored.PINNED_COMMIT[:7]}")
    print(f"observer:  {observer.name}")
    print(f"lattice:   {args.grid}")
    print(f"search:    {args.budget} evaluations, {args.waypoints} waypoints")
    print(f"worlds:    {', '.join(names) or 'none carry keep-out zones'}\n")

    header = (
        f"{'world':<20}{'ceiling':>9}{'free ach':>10}{'safe ach':>10}"
        f"{'safe bound':>12}{'price':>9}"
    )
    print(header)
    print("-" * len(header))

    rows = []
    for name in names:
        scenario = vendored.scenario(name)
        started = time.perf_counter()
        built = lattice_module.build(
            scenario, observer, args.grid, respect_keep_out=True
        )
        build_seconds = time.perf_counter() - started
        shortest = ShortestPathPlanner().plan(scenario)
        baseline = vendored.metrics.evaluate(scenario, observer, shortest.points)

        for ceiling in ceilings:
            safe_bound = reachability_bound(
                scenario, observer, ceiling, grid=args.grid, built=built,
                respect_keep_out=True,
            )
            free = _search(
                scenario, observer, ceiling, args.budget, args.waypoints, False
            )
            safe = _search(
                scenario, observer, ceiling, args.budget, args.waypoints, True
            )

            # The shortest path ignores keep-out zones, so it only counts as a
            # safe achievement when it happens not to enter one.
            free_achieved = max(free.legibility, baseline.legibility)
            safe_achieved = safe.legibility if safe.feasible else None
            if (
                baseline.safety.keep_out_entries == 0
                and safe_achieved is not None
            ):
                safe_achieved = max(safe_achieved, baseline.legibility)

            certified = free_achieved - safe_bound.bound
            row = {
                "scenario": scenario.id,
                "ceiling": ceiling,
                # Whether the cheapest route already respects the zone. Where
                # it does, the constraint costs a robot nothing until it tries
                # to communicate, and the price below is the price of trying.
                "shortest_path_legibility": baseline.legibility,
                "shortest_path_is_safe": baseline.safety.keep_out_entries == 0,
                "free_achieved": free_achieved,
                "free_enters_keep_out": free.safety.keep_out_entries > 0,
                "safe_achieved": safe_achieved,
                "safe_bound": safe_bound.bound,
                "safe_gap": (
                    None if safe_achieved is None
                    else safe_bound.bound - safe_achieved
                ),
                "certified_price": certified if certified > 0 else None,
                "weight_from_band": safe_bound.weight_from_band,
                "uncertified_cells": safe_bound.uncertified_cells,
                "lattice_build_seconds": build_seconds,
            }
            rows.append(row)
            price = f"{certified:.4f}" if certified > 0 else "none"
            achieved = "none" if safe_achieved is None else f"{safe_achieved:.4f}"
            print(
                f"{scenario.id:<20}{ceiling:>9.2f}{free_achieved:>10.4f}"
                f"{achieved:>10}{safe_bound.bound:>12.4f}{price:>9}",
                flush=True,
            )
            if row["safe_gap"] is not None and row["safe_gap"] < 0:
                print(
                    f"   THE SAFE BOUND IS BELOW A SAFE ACHIEVED VALUE IN "
                    f"{scenario.id} AT CEILING {ceiling} AND IS THEREFORE WRONG",
                    flush=True,
                )
        print(flush=True)

    priced = [r for r in rows if r["certified_price"] is not None]
    broken = [r for r in rows if r["safe_gap"] is not None and r["safe_gap"] < 0]
    print(f"{len(rows)} world and ceiling pairs, {len(broken)} violations")
    print(f"{len(priced)} of them certify that safety costs legibility")
    if priced:
        worst = max(priced, key=lambda r: r["certified_price"])
        print(
            f"largest certified price: {worst['certified_price']:.4f} in "
            f"{worst['scenario']} at ceiling {worst['ceiling']}"
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "geometry_commit": vendored.PINNED_COMMIT,
                "observer": observer.name,
                "grid": args.grid,
                "search_budget": args.budget,
                "waypoints": args.waypoints,
                "rows": rows,
                "violations": len(broken),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"written to {output}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
