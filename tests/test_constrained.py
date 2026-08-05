"""The safety-constrained bound is a bound, and a different one.

Keep-out zones do not block motion in the vendored metric: a trajectory may
cross one and is scored for having done so. So "the most legible trajectory
within a cost budget" and "the most legible trajectory within a cost budget
that never enters a keep-out zone" are two questions with two answers, and
only the second is about the frontier the sibling project exists to measure.
"""

from __future__ import annotations

import pytest

from legibility_bounds import lattice as lattice_module
from legibility_bounds import vendored
from legibility_bounds.reachability import BoundError, reachability_bound

TEST_GRID = 0.05
CEILING = 1.25


@pytest.fixture
def observer():
    return vendored.Observer(condition="geodesic")


def test_constraining_cannot_raise_the_bound(observer):
    """Fewer admissible trajectories cannot admit a more legible one.

    The constrained problem's feasible set is a subset of the unconstrained
    one, so its optimum is at most the unconstrained optimum. The bounds need
    not obey that in principle, since they are two relaxations rather than two
    optima, but the constrained relaxation is the unconstrained one with cells
    removed and distances raised, so it does.
    """
    scenario = vendored.scenario("keep_out_shortcut")
    assert scenario.keep_out_zones
    free = reachability_bound(scenario, observer, CEILING, grid=TEST_GRID)
    safe = reachability_bound(
        scenario, observer, CEILING, grid=TEST_GRID, respect_keep_out=True
    )
    assert safe.bound <= free.bound + 1e-12
    assert safe.respect_keep_out and not free.respect_keep_out


def test_it_separates_two_worlds_the_unconstrained_bound_cannot(observer):
    """open_pair and keep_out_shortcut differ only by a keep-out zone.

    The unconstrained bound is blind to that, necessarily, and returns the
    same number for both. The constrained bound is the reason the pair is
    worth having in the suite at all.
    """
    empty = vendored.scenario("open_pair")
    zoned = vendored.scenario("keep_out_shortcut")
    assert not empty.keep_out_zones and zoned.keep_out_zones

    free_empty = reachability_bound(empty, observer, CEILING, grid=TEST_GRID)
    free_zoned = reachability_bound(zoned, observer, CEILING, grid=TEST_GRID)
    assert free_empty.bound == pytest.approx(free_zoned.bound, abs=1e-12)

    safe_zoned = reachability_bound(
        zoned, observer, CEILING, grid=TEST_GRID, respect_keep_out=True
    )
    assert safe_zoned.bound < free_zoned.bound


def test_it_bounds_the_safety_constrained_planner(observer):
    """The planner that refuses keep-out zones must stay under it."""
    from legible_motion_bench.planners.legible import LegiblePlanner

    scenario = vendored.scenario("keep_out_shortcut")
    safe = reachability_bound(
        scenario, observer, CEILING, grid=TEST_GRID, respect_keep_out=True
    )
    plan = LegiblePlanner(
        waypoints=3,
        budget=500,
        restarts=3,
        cost_budget=CEILING,
        respect_keep_out=True,
    ).plan(scenario)
    scored = vendored.metrics.evaluate(scenario, observer, plan.points)
    assert scored.feasible
    assert scored.safety.keep_out_entries == 0
    assert scored.cost_ratio <= CEILING + 1e-9
    assert scored.legibility <= safe.bound


def test_a_world_with_no_keep_out_zones_is_unaffected(observer):
    scenario = vendored.scenario("open_pair")
    free = reachability_bound(scenario, observer, CEILING, grid=TEST_GRID)
    safe = reachability_bound(
        scenario, observer, CEILING, grid=TEST_GRID, respect_keep_out=True
    )
    assert safe.bound == pytest.approx(free.bound, abs=1e-12)


def test_the_two_lattices_are_not_interchangeable(observer):
    scenario = vendored.scenario("keep_out_shortcut")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    with pytest.raises(BoundError) as raised:
        reachability_bound(
            scenario, observer, CEILING, grid=TEST_GRID, built=built,
            respect_keep_out=True,
        )
    assert "different problems" in str(raised.value)


def test_the_observer_does_not_see_the_keep_out_zone(observer):
    """A keep-out zone constrains the robot, not the watcher.

    The belief is a function of the observer's cost-to-go, which is defined
    over obstacles alone. If respecting a zone changed the belief field, the
    constrained bound would be answering a question about a different observer
    rather than about a different feasible set.
    """
    scenario = vendored.scenario("keep_out_shortcut")
    free = lattice_module.build(scenario, observer, TEST_GRID)
    safe = lattice_module.build(
        scenario, observer, TEST_GRID, respect_keep_out=True
    )
    shared = free.usable & safe.usable
    assert shared.any()
    assert (abs(free.belief[shared] - safe.belief[shared]) < 1e-12).all()
    # The reachability side, by contrast, has to have moved.
    assert (safe.geodesic_to_goal[shared] >= free.geodesic_to_goal[shared] - 1e-12).all()
    assert (safe.geodesic_to_goal[shared] > free.geodesic_to_goal[shared] + 1e-9).any()
