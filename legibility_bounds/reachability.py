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

    C*(S -> x_i) <= s L_path      and      C*(x_i -> G) <= (1 - s) L_path

because arc length is at least optimal cost-to-go. So `x_i` lies in a lens
`R(s)`, and

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

Worlds with obstacles are handled, and the cells where the straight-line
argument fails are handled separately rather than glossed. See `lattice.py`,
which is where all of that lives. The one number to read alongside a bound in
such a world is `weight_from_band`: the share of the result that came from
cells too close to an obstacle to bound properly.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from . import lattice as lattice_module
from .lattice import Lattice, lipschitz_constant
from .vendored import Observer, Scenario, geodesic_cost, metrics

__all__ = [
    "BoundError",
    "ReachabilityBound",
    "belief_field",
    "lipschitz_constant",
    "reachability_bound",
]


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
    weight_from_band: float
    band_cells: int
    unusable_cells: int

    def as_record(self) -> dict:
        return asdict(self)


def belief_field(scenario: Scenario, observer: Observer, px, py):
    """Belief in the true goal at each of the given points.

    Kept as the obstacle-free vectorised form, and held to the vendored
    `Observer.posterior` by `tests/test_reachability.py` rather than by
    argument, in the way the sibling repository holds its fast paths to its
    slow ones. A world with obstacles goes through `lattice.build` instead,
    which uses the exact cost-to-go index.
    """
    if scenario.obstacles:
        raise BoundError(
            f"scenario {scenario.id!r} has obstacles, so the geodesic is not "
            f"the straight line and this field would be wrong. Build a "
            f"lattice instead."
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
    shift = np.maximum.reduce(list(exponents.values()))
    weights = {
        goal_id: prior[goal_id] * np.exp(value - shift)
        for goal_id, value in exponents.items()
    }
    return weights[scenario.true_goal] / sum(weights.values())


def reachability_bound(
    scenario: Scenario,
    observer: Observer,
    ceiling: float,
    grid: float = 0.01,
    spacing: float = metrics.DEFAULT_SAMPLE_SPACING,
    built: Lattice | None = None,
) -> ReachabilityBound:
    """Upper bound on the legibility of any trajectory within the ceiling.

    Pass `built` to reuse a lattice across several ceilings, which is worth
    doing because building one is most of the cost in a world with obstacles
    and it does not depend on the ceiling at all.
    """
    if ceiling < 1.0:
        raise BoundError(
            f"the ceiling is a ratio against the optimal path and cannot be "
            f"below one, found {ceiling!r}"
        )
    if grid <= 0:
        raise BoundError(f"grid spacing must be positive, found {grid!r}")

    if built is None:
        built = lattice_module.build(scenario, observer, grid)
    elif built.grid != grid:
        raise BoundError(
            f"the lattice given was built at grid {built.grid!r} but a bound "
            f"at grid {grid!r} was asked for"
        )
    if built.scenario_id != scenario.id or built.observer != observer.name:
        raise BoundError(
            f"the lattice given is for {built.scenario_id!r} under "
            f"{built.observer!r}, not {scenario.id!r} under {observer.name!r}"
        )

    optimal = geodesic_cost(
        scenario.start, scenario.true_goal_position, scenario.obstacles
    )
    length = ceiling * optimal

    ceiling_on_belief = built.belief_bound()
    steps = max(1, math.ceil(length / spacing))

    numerator = 0.0
    denominator = 0.0
    from_band = 0.0
    for i in range(steps + 1):
        s = i / steps
        reachable = built.reachable(s * length, (1.0 - s) * length)
        weight = 1.0 - s

        # Split the slice so the band's contribution can be read rather than
        # inferred. A band cell is capped at one, so the band decided this
        # slice exactly when no cell we could bound properly reached as high.
        clear = reachable & ~built.near_obstacle
        in_band = bool((reachable & built.near_obstacle).any())
        best_clear = float(ceiling_on_belief[clear].max()) if clear.any() else 0.0

        if in_band:
            best = max(best_clear, 1.0)
            banded = best_clear < 1.0
        elif clear.any():
            best = best_clear
            banded = False
        else:
            # No lattice point survives the lens. The belief is a probability
            # whatever the truth is, so one is still a bound.
            best = 1.0
            banded = True
        numerator += best * weight
        denominator += weight
        if banded:
            from_band += weight

    return ReachabilityBound(
        scenario_id=scenario.id,
        observer=observer.name,
        ceiling=ceiling,
        optimal_cost=optimal,
        path_length=length,
        samples=steps + 1,
        grid=grid,
        lipschitz_slack=built.slack,
        bound=numerator / denominator,
        weight_from_band=from_band / denominator,
        band_cells=int(built.near_obstacle.sum()),
        unusable_cells=int((~built.usable).sum()),
    )
