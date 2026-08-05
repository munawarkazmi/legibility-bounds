"""A trajectory built from the bound, to certify the other end of the gap.

The upper bound says no trajectory within the budget beats some value. The
lower end of the interval has so far been whatever the vendored local search
happened to reach, which is a valid lower bound but carries no argument of its
own, and the suite shows where that hurts: at loose ceilings the interval
widens at the bottom rather than the top, because the search stops improving
while the bound keeps rising.

This builds a trajectory instead of searching for one, out of what the bound
already knows. For each of a few fractions of the way along, it takes the
reachable lattice cell where the observer's belief is highest, and threads a
path through those anchors. Two properties make the result trustworthy without
any argument about the construction:

  the anchors are joined by exact geodesics, so the trajectory cannot pass
  through an obstacle whatever the anchors are;

  and the result is scored by the vendored metric, so the number is a
  measurement of a real trajectory rather than an estimate of one.

A lower bound obtained this way is certified in the only sense that matters
for the interval: the trajectory exists and it scores what is claimed.

Anchors that overshoot the cost budget are pulled back towards the shortest
path until the budget is met, which is a one-dimensional search on a scalar
rather than an optimisation over waypoints.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .lattice import Lattice
from .vendored import (
    GeometryError,
    Observer,
    Scenario,
    geodesic,
    metrics,
    polyline_length,
)


class WitnessError(ValueError):
    """Raised when a witness cannot be built for the inputs given."""


@dataclass(frozen=True)
class Witness:
    scenario_id: str
    observer: str
    ceiling: float
    respect_keep_out: bool
    anchors: int
    pullback: float
    legibility: float
    cost_ratio: float
    keep_out_entries: int
    points: tuple

    def as_record(self) -> dict:
        return {
            "scenario": self.scenario_id,
            "observer": self.observer,
            "ceiling": self.ceiling,
            "respect_keep_out": self.respect_keep_out,
            "anchors": self.anchors,
            "pullback": self.pullback,
            "legibility": self.legibility,
            "cost_ratio": self.cost_ratio,
            "keep_out_entries": self.keep_out_entries,
            "points": [list(p) for p in self.points],
        }


def _blockers(scenario: Scenario, respect_keep_out: bool):
    if respect_keep_out:
        return tuple(scenario.obstacles) + tuple(scenario.keep_out_zones)
    return tuple(scenario.obstacles)


def _join(scenario: Scenario, waypoints, blockers) -> tuple:
    """Thread a path through the waypoints along exact geodesics.

    Joining with geodesics rather than straight lines is what makes the result
    feasible by construction: a geodesic avoids the obstacle interiors by
    definition, so no anchor can produce a trajectory that walks through a
    wall however badly it is placed.
    """
    points: list = []
    for a, b in zip(waypoints, waypoints[1:]):
        leg = geodesic(a, b, blockers).path
        if points and points[-1] == leg[0]:
            leg = leg[1:]
        points.extend(leg)
    return tuple(points)


def _point_at(path, fraction: float):
    """The point a given fraction of the arc length along a polyline.

    Plain Python floats, deliberately. Everything here feeds the vendored
    exact predicate, which branches on comparisons and builds a sign by
    subtracting them; a numpy scalar reaching it raises rather than answers.
    """
    lengths = [0.0]
    for a, b in zip(path, path[1:]):
        lengths.append(lengths[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = lengths[-1]
    if total <= 0:
        return (float(path[0][0]), float(path[0][1]))
    target = total * min(1.0, max(0.0, fraction))
    for i in range(len(path) - 1):
        if lengths[i + 1] >= target:
            span = lengths[i + 1] - lengths[i]
            t = 0.0 if span <= 0 else (target - lengths[i]) / span
            a, b = path[i], path[i + 1]
            return (
                float(a[0] + t * (b[0] - a[0])),
                float(a[1] + t * (b[1] - a[1])),
            )
    return (float(path[-1][0]), float(path[-1][1]))


def _best_cell(built: Lattice, spent: float, remaining: float):
    """The reachable lattice point where the observer's belief is highest.

    The belief at the point rather than its bound over the cell, because this
    is somewhere the trajectory will actually go.
    """
    reachable = built.reachable(spent, remaining)
    if not reachable.any():
        return None
    values = np.where(reachable, built.belief, -np.inf)
    row, col = np.unravel_index(int(np.argmax(values)), values.shape)
    return (float(built.x[row, col]), float(built.y[row, col]))


def build(
    scenario: Scenario,
    observer: Observer,
    ceiling: float,
    built: Lattice,
    anchors: int = 3,
    respect_keep_out: bool = False,
    steps: int = 24,
    spacing: float = metrics.DEFAULT_SAMPLE_SPACING,
) -> Witness | None:
    """One witness trajectory, or None if no admissible one could be built."""
    if anchors < 1:
        raise WitnessError(f"a witness needs at least one anchor, found {anchors}")
    if built.respect_keep_out != respect_keep_out:
        raise WitnessError(
            "the lattice given describes the other problem; a safe witness "
            "needs a lattice built with respect_keep_out"
        )

    blockers = _blockers(scenario, respect_keep_out)
    start, goal = scenario.start, scenario.true_goal_position
    base = geodesic(start, goal, blockers)
    optimal = metrics.evaluate(scenario, observer, base.path).optimal_cost
    budget = ceiling * optimal

    fractions = [(i + 1) / (anchors + 1) for i in range(anchors)]
    targets = []
    for fraction in fractions:
        cell = _best_cell(built, fraction * budget, (1.0 - fraction) * budget)
        if cell is None:
            return None
        targets.append(cell)

    # Pull the anchors back towards the shortest path until the budget holds.
    # At pullback zero the trajectory is the shortest path, which always fits,
    # so a feasible answer always exists and the search is for the largest
    # pullback that still fits rather than for feasibility.
    anchored = [_point_at(base.path, f) for f in fractions]
    best = None
    low, high = 0.0, 1.0
    for _ in range(steps):
        middle = (low + high) / 2.0
        waypoints = [start]
        for anchor, target in zip(anchored, targets):
            waypoints.append((
                anchor[0] + middle * (target[0] - anchor[0]),
                anchor[1] + middle * (target[1] - anchor[1]),
            ))
        waypoints.append(goal)
        try:
            points = _join(scenario, waypoints, blockers)
        except GeometryError:
            # A waypoint landed inside an obstacle, which is a fact about the
            # geometry and means this pullback is too far. Nothing wider is
            # caught here on purpose: an earlier version swallowed every
            # exception, and a type error in the interpolation was reported
            # for hours as "no admissible trajectory exists" in every world
            # with an obstacle.
            high = middle
            continue
        if polyline_length(points) <= budget:
            scored = metrics.evaluate(scenario, observer, points, spacing=spacing)
            if scored.feasible and (
                not respect_keep_out or scored.safety.keep_out_entries == 0
            ):
                best = (middle, points, scored)
                low = middle
            else:
                high = middle
        else:
            high = middle

    if best is None:
        return None
    pullback, points, scored = best
    return Witness(
        scenario_id=scenario.id,
        observer=observer.name,
        ceiling=ceiling,
        respect_keep_out=respect_keep_out,
        anchors=anchors,
        pullback=pullback,
        legibility=scored.legibility,
        cost_ratio=scored.cost_ratio,
        keep_out_entries=scored.safety.keep_out_entries,
        points=points,
    )


def best_witness(
    scenario: Scenario,
    observer: Observer,
    ceiling: float,
    built: Lattice,
    anchor_counts=(1, 2, 3, 5),
    respect_keep_out: bool = False,
    **kwargs,
) -> Witness | None:
    """The best witness over a few anchor counts.

    More anchors track the bound's own maximisers more closely but spend more
    path doing it, and which wins is a property of the world rather than
    something to guess, so a handful are tried and the best kept.
    """
    found = [
        build(
            scenario, observer, ceiling, built, anchors=count,
            respect_keep_out=respect_keep_out, **kwargs,
        )
        for count in anchor_counts
    ]
    alive = [w for w in found if w is not None]
    return max(alive, key=lambda w: w.legibility) if alive else None
