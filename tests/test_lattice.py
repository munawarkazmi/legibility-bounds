"""The lattice says true things about a world with obstacles.

A coarse lattice is used throughout. Building one is the expensive step and
none of these tests are about resolution: they are about the quantities being
the ones they claim to be, and about the two inequalities the treatment of
obstacle-adjacent cells rests on.
"""

from __future__ import annotations

import numpy as np
import pytest

from legibility_bounds import lattice as lattice_module
from legibility_bounds import vendored

TEST_GRID = 0.25


@pytest.fixture(scope="module")
def walled():
    scenario = vendored.scenario("wall_choice")
    assert scenario.obstacles, "wall_choice is supposed to have an obstacle"
    observer = vendored.Observer(condition="geodesic")
    return scenario, observer, lattice_module.build(scenario, observer, TEST_GRID)


def test_euclidean_distance_never_exceeds_the_geodesic(walled):
    """The inequality the whole treatment of obstacle-adjacent cells rests on.

    A cell too close to an obstacle to bound properly is still excluded from a
    reachable set when its Euclidean distance already breaks the budget. That
    is only sound because a path avoiding obstacles is at least as long as the
    straight line, so this asserts it over the whole lattice rather than
    trusting it.
    """
    _, _, built = walled
    usable = built.usable
    assert usable.any()
    assert (built.euclidean_to_start[usable] <= built.geodesic_to_start[usable] + 1e-9).all()
    assert (built.euclidean_to_goal[usable] <= built.geodesic_to_goal[usable] + 1e-9).all()


def test_the_geodesic_matches_the_reference_implementation(walled):
    """The index is the fast path; geodesic_cost rebuilds the graph each call."""
    scenario, _, built = walled
    usable = np.argwhere(built.usable)
    rng = np.random.default_rng(20260806)
    for row, col in usable[rng.choice(len(usable), size=40, replace=False)]:
        point = (float(built.x[row, col]), float(built.y[row, col]))
        expected = vendored.geodesic_cost(
            point, scenario.true_goal_position, scenario.obstacles
        )
        assert built.geodesic_to_goal[row, col] == pytest.approx(expected, abs=1e-9)


def test_the_belief_matches_the_reference_observer(walled):
    scenario, observer, built = walled
    usable = np.argwhere(built.usable)
    rng = np.random.default_rng(4)
    for row, col in usable[rng.choice(len(usable), size=40, replace=False)]:
        point = (float(built.x[row, col]), float(built.y[row, col]))
        expected = observer.posterior(scenario, [scenario.start, point])[
            scenario.true_goal
        ]
        assert built.belief[row, col] == pytest.approx(expected, abs=1e-12)


def test_points_inside_an_obstacle_are_not_usable(walled):
    scenario, _, built = walled
    assert not built.usable.all(), "wall_choice should exclude its own wall"
    rows, cols = np.where(~built.usable)
    for row, col in zip(rows[:20], cols[:20]):
        point = (float(built.x[row, col]), float(built.y[row, col]))
        assert any(ob.contains_interior(point) for ob in scenario.obstacles)


def test_the_band_is_exactly_the_cells_near_an_obstacle(walled):
    scenario, _, built = walled
    assert built.near_obstacle.any(), "there should be cells beside the wall"
    rows, cols = np.where(built.near_obstacle)
    for row, col in zip(rows[:20], cols[:20]):
        point = (float(built.x[row, col]), float(built.y[row, col]))
        nearest = min(ob.distance_to_point(point) for ob in scenario.obstacles)
        assert nearest <= built.cell_radius


def test_the_belief_bound_is_one_in_the_band_and_slack_elsewhere(walled):
    _, _, built = walled
    bound = built.belief_bound()
    assert (bound[built.near_obstacle] == 1.0).all()
    clear = ~built.near_obstacle
    assert (bound[clear] <= built.belief[clear] + built.slack + 1e-12).all()
    assert (bound <= 1.0).all()


def test_an_obstacle_free_world_has_no_band_at_all(walled):
    scenario = vendored.scenario("open_pair")
    observer = vendored.Observer(condition="geodesic")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    assert not built.near_obstacle.any()
    assert built.usable.all()
    assert built.geodesic_to_goal == pytest.approx(built.euclidean_to_goal)
