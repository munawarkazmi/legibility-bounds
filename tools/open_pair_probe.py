"""Is the bound worth anything? The kill-criterion probe, on the simplest world.

    python tools/open_pair_probe.py

`open_pair` has no obstacles and two goals, so the budget-admissible region
is a plain ellipse and every geodesic is a straight line. If a crude upper
bound sits far above what the local optimiser reaches here, it will not do
better anywhere harder, and the approach is dead.

The probe reports three things beside each other, because a bound is only
readable against what is achievable and against what the bound would be if
it said nothing:

  achieved    the best legibility any search here actually reached, which is
              a lower bound on the optimum by construction
  bound       the reachability upper bound
  crude       the largest belief anywhere in the admissible ellipse, which is
              the bound obtained by ignoring when the robot could be there

It also checks the one case where the answer is known exactly. At a ceiling
of one the only admissible trajectory in an obstacle-free world is the
straight line, so the optimum is that trajectory's legibility and no search
is involved.

Numbers are written to results/open_pair_probe.json so that anything quoted
elsewhere can be traced back to a run rather than to a person.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legibility_bounds import vendored  # noqa: E402
from legibility_bounds.reachability import (  # noqa: E402
    belief_field,
    lipschitz_constant,
    reachability_bound,
)

from legible_motion_bench.planners.legible import LegiblePlanner  # noqa: E402
from legible_motion_bench.planners.shortest import ShortestPathPlanner  # noqa: E402

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "results" / "open_pair_probe.json"


def crude_bound(scenario, observer, ceiling, grid):
    """The largest belief anywhere a budget-feasible trajectory could pass.

    A point x can lie on a trajectory of cost ratio at most c only if
    C*(S -> x) + C*(x -> G) <= c C*(S -> G). This maximises the belief over
    that region and ignores everything about when the robot could be there.
    """
    start = scenario.start
    goal = scenario.true_goal_position
    optimal = vendored.geodesic_cost(start, goal, scenario.obstacles)
    bounds = scenario.bounds
    gx = np.arange(bounds.xmin, bounds.xmax + grid, grid)
    gy = np.arange(bounds.ymin, bounds.ymax + grid, grid)
    mesh_x, mesh_y = np.meshgrid(gx, gy)
    admissible = (
        np.hypot(mesh_x - start[0], mesh_y - start[1])
        + np.hypot(mesh_x - goal[0], mesh_y - goal[1])
        <= ceiling * optimal + grid
    )
    field = belief_field(scenario, observer, mesh_x, mesh_y)
    slack = lipschitz_constant(observer) * grid * np.sqrt(2) / 2.0
    return min(1.0, float(field[admissible].max()) + slack)


def best_achieved(scenario, observer, ceiling, budget, waypoint_counts):
    """The best legibility any search here reached, and what produced it."""
    shortest = ShortestPathPlanner().plan(scenario)
    scored = vendored.metrics.evaluate(scenario, observer, shortest.points)
    best = {
        "legibility": scored.legibility,
        "cost_ratio": scored.cost_ratio,
        "by": "shortest path",
    }
    attempts = [dict(best)]
    for waypoints in waypoint_counts:
        planner = LegiblePlanner(
            waypoints=waypoints, budget=budget, restarts=4, cost_budget=ceiling
        )
        result = vendored.metrics.evaluate(
            scenario, observer, planner.plan(scenario).points
        )
        attempt = {
            "legibility": result.legibility,
            "cost_ratio": result.cost_ratio,
            "by": f"optimiser k={waypoints} restarts=4 budget={budget}",
        }
        attempts.append(attempt)
        if attempt["legibility"] > best["legibility"]:
            best = attempt
    return best, attempts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="open_pair")
    parser.add_argument("--ceiling", type=float, default=1.25)
    parser.add_argument("--grids", default="0.04,0.02,0.01")
    parser.add_argument("--budget", type=int, default=4000)
    parser.add_argument("--waypoints", default="3,5,8,12")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    grids = [float(g) for g in args.grids.split(",")]
    waypoint_counts = [int(k) for k in args.waypoints.split(",")]
    scenario = vendored.scenario(args.scenario)
    observer = vendored.Observer(condition="geodesic")

    print(f"scenario:  {scenario.id}")
    print(f"observer:  {observer.name}")
    print(f"geometry:  legible-motion-bench at {vendored.PINNED_COMMIT[:7]}")
    print(f"ceiling:   {args.ceiling}\n")

    print("the bound as the lattice is refined")
    refinement = []
    for grid in grids:
        result = reachability_bound(scenario, observer, args.ceiling, grid=grid)
        refinement.append(result.as_record())
        print(f"   grid {grid:<7} bound {result.bound:.4f}   "
              f"detour {result.cell_detour:.4f}   samples {result.samples}")
    finest = refinement[-1]
    print(flush=True)

    print("the one case where the optimum is known without searching")
    straight = vendored.metrics.evaluate(
        scenario, observer, [scenario.start, scenario.true_goal_position]
    )
    at_one = reachability_bound(scenario, observer, 1.0, grid=grids[-1])
    print(f"   ceiling 1.00, exact optimum  {straight.legibility:.4f}")
    print(f"   ceiling 1.00, bound          {at_one.bound:.4f}")
    print(f"   gap                          {at_one.bound - straight.legibility:.4f}\n",
          flush=True)

    print(f"what a search reaches at ceiling {args.ceiling}")
    best, attempts = best_achieved(
        scenario, observer, args.ceiling, args.budget, waypoint_counts
    )
    for attempt in attempts:
        print(f"   {attempt['by']:<44} {attempt['legibility']:.4f}   "
              f"cost ratio {attempt['cost_ratio']:.4f}")

    crude = crude_bound(scenario, observer, args.ceiling, grids[-1])
    gap = finest["bound"] - best["legibility"]
    print(f"\n   achieved   {best['legibility']:.4f}   ({best['by']})")
    print(f"   bound      {finest['bound']:.4f}")
    print(f"   gap        {gap:.4f}")
    print(f"   crude      {crude:.4f}   (the bound that ignores reachability)")
    print("\n   the bound holds" if gap >= 0 else
          "\n   THE BOUND IS BELOW AN ACHIEVED VALUE AND IS THEREFORE WRONG")

    record = {
        "scenario": scenario.id,
        "observer": observer.name,
        "geometry_commit": vendored.PINNED_COMMIT,
        "ceiling": args.ceiling,
        "search_budget": args.budget,
        "refinement": refinement,
        "bound": finest["bound"],
        "crude_bound": crude,
        "achieved": best,
        "attempts": attempts,
        "gap": gap,
        "ceiling_one": {
            "exact_optimum": straight.legibility,
            "bound": at_one.bound,
            "gap": at_one.bound - straight.legibility,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"\nwritten to {output}")
    return 0 if gap >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
