"""An upper bound on achievable legibility, from reachability alone.

This is the loosest useful member of the family of bounds this project is
about, and it is here first because it is the one that decides whether the
idea is alive.

The argument
------------

Legibility is a weighted average of the observer's belief along the path,

    L = sum_i b(x_i) w_i / sum_i w_i,    w_i = 1 - i/N,

where `b` is a static field over the plane, `N + 1` is the number of samples,
and `x_i` is the sample at normalised arc length `s = i/N`. Both facts that
make this so are asserted in `tests/test_vendored.py`: the belief depends
only on position, and the duration cancels out of the weighting.

A trajectory of length `L_path` that starts at `S`, ends at the goal `G`, and
passes through `x_i` after `s L_path` of arc length must satisfy

    d(S, x_i) <= s L_path        and        d(x_i, G) <= (1 - s) L_path

because arc length is at least distance. So `x_i` lies in a lens `R(s)`, and

    L <= sum_i [ max over R(s_i) of b ] w_i / sum_i w_i.

Both radii grow with `L_path`, so `R(s)` grows with it too, and evaluating at
the largest admissible length `c C*(S -> G)` covers every shorter one. That
is why this does not have to range over path lengths.

What it throws away
-------------------

Everything connecting one sample to the next. The relaxation lets the point
jump anywhere inside the next lens, so it bounds a trajectory that need not
be a trajectory. Constraining consecutive samples to lie within `L_path / N`
of each other is what a tighter bound would add, and it is not done here.

Where it does not apply
-----------------------

Worlds with obstacles. The field below is computed from Euclidean distance,
which equals the geodesic only when nothing stands in the way, and the lens
condition uses the same distance. A world with obstacles is refused rather
than bounded wrongly.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from .vendored import Observer, Scenario, geodesic_cost, metrics


class BoundError(ValueError):
    """Raised when a bound is asked for something it cannot mean."""


@dataclass(frozen=True)
class ReachabilityBound:
    scenario_id: str
    observer: str
    ceiling: float
    optimal_cost: float
    path_length: float
    samples: int
    grid: float
    lipschitz_slack: float
    bound: float

    def as_record(self) -> dict:
        return asdict(self)


def belief_field(scenario: Scenario, observer: Observer, px, py):
    """Belief in the true goal at each point of a grid, vectorised.

    The same quantity the vendored `Observer.posterior` returns, computed for
    many points at once. It is held to that reference implementation by
    `tests/test_reachability.py` rather than by argument, in the way the
    sibling repository holds its fast paths to its slow ones.
    """
    if scenario.obstacles:
        raise BoundError(
            f"scenario {scenario.id!r} has obstacles, so the geodesic is not "
            f"the straight line and this field would be wrong"
        )
    px = np.asarray(px, dtype=float)
    py = np.asarray(py, dtype=float)
    baseline = observer.baseline(scenario)
    prior = observer.prior_for(scenario)

    exponents = {
        goal.id: observer.beta
        * (baseline[goal.id] - np.hypot(px - goal.position[0], py - goal.position[1]))
        for goal in scenario.goals
    }
    # The same shift the reference implementation applies, for the same
    # reason: without it a point far from every goal underflows every weight
    # to zero and the normalisation divides by it.
    shift = np.maximum.reduce(list(exponents.values()))
    weights = {
        goal_id: prior[goal_id] * np.exp(value - shift)
        for goal_id, value in exponents.items()
    }
    total = sum(weights.values())
    return weights[scenario.true_goal] / total


def lipschitz_constant(observer: Observer) -> float:
    """A bound on |grad b|, used to make a grid maximum into a real maximum.

    The belief is a softmax of terms whose gradients in space have magnitude
    at most beta, so

        |grad b| <= beta * [ b (1 - b) + b * sum of the other beliefs ]
                  = 2 beta b (1 - b)
                  <= beta / 2,

    for any number of goals. Nothing here assumes there are two.
    """
    return observer.beta / 2.0


def reachability_bound(
    scenario: Scenario,
    observer: Observer,
    ceiling: float,
    grid: float = 0.01,
    spacing: float = metrics.DEFAULT_SAMPLE_SPACING,
) -> ReachabilityBound:
    """Upper bound on the legibility of any trajectory within the ceiling.

    The bound is computed over a lattice of the world at `grid` spacing. A
    lattice maximum is not a maximum, so two things make it into one: the
    lens test is dilated by a whole grid step, which cannot exclude a lattice
    point near an admissible one, and the Lipschitz slack above is added to
    the result.
    """
    if ceiling < 1.0:
        raise BoundError(
            f"the ceiling is a ratio against the optimal path and cannot be "
            f"below one, found {ceiling!r}"
        )
    if grid <= 0:
        raise BoundError(f"grid spacing must be positive, found {grid!r}")
    if scenario.obstacles:
        raise BoundError(
            f"scenario {scenario.id!r} has obstacles. This bound uses "
            f"Euclidean distance for both the belief field and the lens "
            f"condition, and neither is the geodesic once something stands "
            f"in the way. Worlds with obstacles need their own treatment."
        )

    start = scenario.start
    goal = scenario.true_goal_position
    optimal = geodesic_cost(start, goal, scenario.obstacles)
    length = ceiling * optimal

    bounds = scenario.bounds
    gx = np.arange(bounds.xmin, bounds.xmax + grid, grid)
    gy = np.arange(bounds.ymin, bounds.ymax + grid, grid)
    mesh_x, mesh_y = np.meshgrid(gx, gy)

    to_start = np.hypot(mesh_x - start[0], mesh_y - start[1])
    to_goal = np.hypot(mesh_x - goal[0], mesh_y - goal[1])
    field = belief_field(scenario, observer, mesh_x, mesh_y)

    # Half the diagonal of a cell is the furthest any point can be from the
    # nearest lattice point.
    slack = lipschitz_constant(observer) * grid * math.sqrt(2) / 2.0

    steps = max(1, math.ceil(length / spacing))
    numerator = 0.0
    denominator = 0.0
    for i in range(steps + 1):
        s = i / steps
        reachable = (to_start <= s * length + grid) & (
            to_goal <= (1.0 - s) * length + grid
        )
        if reachable.any():
            best = min(1.0, float(field[reachable].max()) + slack)
        else:
            # No lattice point survives the lens. The belief is a probability
            # whatever the truth is, so one is still a bound.
            best = 1.0
        weight = 1.0 - s
        numerator += best * weight
        denominator += weight

    return ReachabilityBound(
        scenario_id=scenario.id,
        observer=observer.name,
        ceiling=ceiling,
        optimal_cost=optimal,
        path_length=length,
        samples=steps + 1,
        grid=grid,
        lipschitz_slack=slack,
        bound=numerator / denominator,
    )
