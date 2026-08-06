"""The anchored bound is a bound, and a tighter one than the plain bound.

It is not used by any tool. It is kept, with these tests, because the finding
that it does not pay is worth being able to re-derive, and because a negative
result from an implementation nobody can check is not a result.

A coarse lattice throughout: none of this is about resolution.
"""

from __future__ import annotations

import numpy as np
import pytest

from legibility_bounds import lattice as lattice_module
from legibility_bounds import vendored
from legibility_bounds.anchored import _sweep_max, anchored_bound
from legibility_bounds.reachability import BoundError, reachability_bound

TEST_GRID = 0.1
CEILING = 1.25


@pytest.fixture
def observer():
    return vendored.Observer(condition="geodesic")


def test_the_window_maximum_is_the_window_maximum():
    """The fast path against brute force, including at the edges.

    Two earlier versions were wrong here and both would have corrupted the
    finding rather than announced themselves: one rounded the window up to a
    power of two, and one ran off the front of the array and returned minus
    infinity for every window overhanging an edge.
    """
    rng = np.random.default_rng(3)
    for _ in range(40):
        rows, cols = int(rng.integers(3, 25)), int(rng.integers(3, 25))
        values = rng.uniform(-1.0, 1.0, size=(rows, cols))
        half = int(rng.integers(1, 8))
        axis = int(rng.integers(0, 2))

        fast = _sweep_max(values, half, axis)
        slow = np.empty_like(values)
        for i in range(rows):
            for j in range(cols):
                if axis == 0:
                    lo, hi = max(0, i - half), min(rows - 1, i + half)
                    slow[i, j] = values[lo:hi + 1, j].max()
                else:
                    lo, hi = max(0, j - half), min(cols - 1, j + half)
                    slow[i, j] = values[i, lo:hi + 1].max()
        assert np.abs(fast - slow).max() == 0.0


@pytest.mark.parametrize("name", ["open_pair", "wall_choice"])
def test_an_anchor_can_only_tighten(name, observer):
    """Adding a constraint cannot admit more, so it cannot raise the bound.

    This is also the regression test for the defect that mattered here. An
    anchor with no reachable sample at some fraction is infeasible, not
    unknown; scoring it at one, as a first version did, let impossible anchors
    win a maximum taken over anchors and pushed the result above the plain
    bound.
    """
    scenario = vendored.scenario(name)
    built = lattice_module.build(scenario, observer, TEST_GRID)
    plain = reachability_bound(
        scenario, observer, CEILING, grid=TEST_GRID, built=built
    )
    for fraction in (0.25, 0.5, 0.75):
        anchored = anchored_bound(
            scenario, observer, CEILING, built, fraction=fraction
        )
        assert anchored.bound <= plain.bound + 1e-12
        assert anchored.unanchored == pytest.approx(plain.bound, abs=1e-12)
        assert anchored.tightening >= -1e-12


@pytest.mark.parametrize("name", ["open_pair", "wall_choice"])
def test_it_still_bounds_what_a_search_reaches(name, observer):
    from legible_motion_bench.planners.legible import LegiblePlanner

    scenario = vendored.scenario(name)
    built = lattice_module.build(scenario, observer, TEST_GRID)
    anchored = anchored_bound(scenario, observer, CEILING, built, fraction=0.5)

    plan = LegiblePlanner(
        waypoints=3, budget=300, restarts=2, cost_budget=CEILING
    ).plan(scenario)
    scored = vendored.metrics.evaluate(scenario, observer, plan.points)
    assert scored.feasible
    assert scored.legibility <= anchored.bound


def test_the_anchor_it_reports_is_somewhere_the_robot_could_be(observer):
    scenario = vendored.scenario("open_pair")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    anchored = anchored_bound(scenario, observer, CEILING, built, fraction=0.5)
    assert anchored.anchor is not None

    optimal = vendored.geodesic_cost(
        scenario.start, scenario.true_goal_position, scenario.obstacles
    )
    length = CEILING * optimal
    x, y = anchored.anchor
    to_start = vendored.geodesic_cost(scenario.start, (x, y), scenario.obstacles)
    to_goal = vendored.geodesic_cost(
        (x, y), scenario.true_goal_position, scenario.obstacles
    )
    assert to_start + to_goal <= length + built.cell_radius * 2


def test_an_anchor_outside_the_trajectory_is_refused(observer):
    scenario = vendored.scenario("open_pair")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    for fraction in (0.0, 1.0, -0.5, 1.5):
        with pytest.raises(BoundError):
            anchored_bound(scenario, observer, CEILING, built, fraction=fraction)


def test_it_needs_a_lattice_for_the_same_problem(observer):
    scenario = vendored.scenario("keep_out_shortcut")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    with pytest.raises(BoundError):
        anchored_bound(
            scenario, observer, CEILING, built, respect_keep_out=True
        )
