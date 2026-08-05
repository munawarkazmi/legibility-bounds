"""The reachability bound is a bound.

A number that sits close above what a search found is either the result or a
defect, and nothing in the number says which. These tests are the attempt to
make it fail: against a case where the true optimum is known exactly, and
against trajectories that a search actually produced.
"""

from __future__ import annotations

import numpy as np
import pytest

from legibility_bounds import vendored
from legibility_bounds.reachability import (
    BoundError,
    belief_field,
    lipschitz_constant,
    reachability_bound,
)

# Coarse on purpose. A coarser lattice carries more Lipschitz slack and a
# wider dilation, so it gives a looser bound, and a looser bound is still a
# bound. These tests are about validity, not tightness.
TEST_GRID = 0.05


@pytest.fixture
def open_pair():
    return vendored.scenario("open_pair")


@pytest.fixture
def observer():
    return vendored.Observer(condition="geodesic")


def test_the_field_matches_the_reference_observer(open_pair, observer):
    rng = np.random.default_rng(20260806)
    xs = rng.uniform(open_pair.bounds.xmin, open_pair.bounds.xmax, 200)
    ys = rng.uniform(open_pair.bounds.ymin, open_pair.bounds.ymax, 200)

    fast = belief_field(open_pair, observer, xs, ys)
    slow = np.array([
        observer.posterior(open_pair, [open_pair.start, (float(x), float(y))])[
            open_pair.true_goal
        ]
        for x, y in zip(xs, ys)
    ])
    assert np.abs(fast - slow).max() < 1e-12


def test_the_vectorised_field_refuses_a_world_it_would_be_wrong_in(observer):
    """The obstacle-free shortcut must not be reachable for a walled world."""
    walled = vendored.scenario("wall_choice")
    assert walled.obstacles, "wall_choice is supposed to have an obstacle"
    with pytest.raises(BoundError) as raised:
        belief_field(walled, observer, [1.0], [1.0])
    assert "geodesic" in str(raised.value)


def test_it_bounds_the_optimiser_in_a_world_with_an_obstacle(observer):
    """The case the project exists for, where a local search cannot decide.

    Coarse lattice on purpose: this is about the bound holding in a world
    where the geodesic is not the straight line, not about how tight it is.
    """
    from legible_motion_bench.planners.legible import LegiblePlanner

    walled = vendored.scenario("wall_choice")
    result = reachability_bound(walled, observer, ceiling=1.25, grid=0.25)
    plan = LegiblePlanner(
        waypoints=3, budget=300, restarts=2, cost_budget=1.25
    ).plan(walled)
    achieved = vendored.metrics.evaluate(walled, observer, plan.points)
    assert achieved.feasible
    assert achieved.cost_ratio <= 1.25 + 1e-9
    assert achieved.legibility <= result.bound


def test_the_band_share_is_reported_and_is_a_share(observer):
    walled = reachability_bound(
        vendored.scenario("wall_choice"), observer, ceiling=1.25, grid=0.25
    )
    empty = reachability_bound(
        vendored.scenario("open_pair"), observer, ceiling=1.25, grid=0.25
    )
    assert 0.0 <= walled.weight_from_band <= 1.0
    assert walled.band_cells > 0
    # An obstacle-free world has nothing the argument cannot cover, so none of
    # its bound may be attributed to the band.
    assert empty.weight_from_band == 0.0
    assert empty.band_cells == 0


def test_at_ceiling_one_it_bounds_the_only_admissible_trajectory(open_pair, observer):
    """The single case where the true optimum is known without searching.

    At a ceiling of exactly one the path may not be longer than the optimal
    path, and in a world with no obstacles the only such path from the start
    to the goal is the straight line between them. So the true maximum is
    that trajectory's legibility, computed exactly, and the bound has to lie
    at or above it.
    """
    straight = vendored.metrics.evaluate(
        open_pair, observer, [open_pair.start, open_pair.true_goal_position]
    )
    result = reachability_bound(open_pair, observer, ceiling=1.0, grid=TEST_GRID)
    assert result.bound >= straight.legibility


def test_it_bounds_what_the_optimiser_actually_reaches(open_pair, observer):
    from legible_motion_bench.planners.legible import LegiblePlanner

    result = reachability_bound(open_pair, observer, ceiling=1.25, grid=TEST_GRID)
    for waypoints in (3, 5):
        plan = LegiblePlanner(
            waypoints=waypoints, budget=400, restarts=2, cost_budget=1.25
        ).plan(open_pair)
        achieved = vendored.metrics.evaluate(open_pair, observer, plan.points)
        assert achieved.cost_ratio <= 1.25 + 1e-9
        assert achieved.legibility <= result.bound


def test_a_looser_ceiling_cannot_lower_the_bound(open_pair, observer):
    values = [
        reachability_bound(open_pair, observer, ceiling=c, grid=TEST_GRID).bound
        for c in (1.0, 1.1, 1.25, 1.5)
    ]
    assert values == sorted(values)


def test_the_bound_stays_a_probability(open_pair, observer):
    result = reachability_bound(open_pair, observer, ceiling=2.0, grid=TEST_GRID)
    assert 0.0 <= result.bound <= 1.0


def test_the_lipschitz_constant_bounds_the_field_it_is_used_on(open_pair, observer):
    """The slack is only honest if the constant it comes from is."""
    step = 1e-6
    rng = np.random.default_rng(11)
    xs = rng.uniform(open_pair.bounds.xmin, open_pair.bounds.xmax, 400)
    ys = rng.uniform(open_pair.bounds.ymin, open_pair.bounds.ymax, 400)

    here = belief_field(open_pair, observer, xs, ys)
    dx = (belief_field(open_pair, observer, xs + step, ys) - here) / step
    dy = (belief_field(open_pair, observer, xs, ys + step) - here) / step
    assert np.hypot(dx, dy).max() <= lipschitz_constant(observer) + 1e-6


def test_a_ceiling_below_one_is_refused(open_pair, observer):
    with pytest.raises(BoundError):
        reachability_bound(open_pair, observer, ceiling=0.9, grid=TEST_GRID)
