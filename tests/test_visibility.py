"""The fast visibility test agrees with the vendored one everywhere.

This is a differential test in the sibling repository's sense: the fast path
is held to the slow one by comparison over every point of a lattice rather
than by argument about floating point. The fast path exists only because the
slow one is too slow at lattice scale, so nothing is gained if the two ever
disagree.

The comparison is made against the fully exact rational implementation, not
against the guarded one, so a defect in the guard could not hide here.
"""

from __future__ import annotations

import numpy as np
import pytest

from legibility_bounds import vendored
from legibility_bounds.visibility import visible

GRID = 0.1


def _guarded(polygon, a, b):
    return polygon.segment_enters_interior(a, b)


def _exact(polygon, a, b):
    return polygon.segment_enters_interior_exact(a, b)


def _lattice(scenario, grid):
    bounds = scenario.bounds
    xs = np.arange(bounds.xmin, bounds.xmax + grid, grid)
    ys = np.arange(bounds.ymin, bounds.ymax + grid, grid)
    return np.meshgrid(xs, ys)


def _nodes(scenario):
    seen, nodes = set(), []
    for obstacle in scenario.obstacles:
        for vertex in obstacle.vertices:
            if vertex not in seen:
                seen.add(vertex)
                nodes.append(vertex)
    for goal in scenario.goals:
        nodes.append(goal.position)
    nodes.append(scenario.start)
    return nodes


@pytest.mark.parametrize("name", ["wall_choice", "narrow_gap", "pillar_aisle"])
def test_the_fast_test_matches_the_exact_one_at_every_lattice_point(name):
    scenario = vendored.scenario(name)
    assert scenario.obstacles, f"{name} is supposed to have obstacles"
    mesh_x, mesh_y = _lattice(scenario, GRID)

    checked = 0
    for node in _nodes(scenario):
        fast = visible(mesh_x, mesh_y, node, scenario.obstacles, _exact)
        slow = np.array([
            not any(
                _exact(polygon, (float(x), float(y)), node)
                for polygon in scenario.obstacles
            )
            for x, y in zip(mesh_x.ravel(), mesh_y.ravel())
        ]).reshape(mesh_x.shape)
        disagreements = int((fast.visible != slow).sum())
        assert disagreements == 0, (
            f"{name}: {disagreements} disagreements against node {node}"
        )
        checked += fast.visible.size
    assert checked > 0


def test_the_guarded_and_exact_vendored_tests_agree_on_this_lattice():
    """If they did not, the test above would be comparing against the wrong thing."""
    scenario = vendored.scenario("wall_choice")
    mesh_x, mesh_y = _lattice(scenario, 0.25)
    for node in _nodes(scenario):
        for x, y in zip(mesh_x.ravel(), mesh_y.ravel()):
            point = (float(x), float(y))
            for polygon in scenario.obstacles:
                assert _guarded(polygon, point, node) == _exact(polygon, point, node)


def test_the_fallback_rate_is_reported_and_small():
    """A fast path that fell back on everything would not be a fast path."""
    scenario = vendored.scenario("wall_choice")
    mesh_x, mesh_y = _lattice(scenario, GRID)
    rates = [
        visible(mesh_x, mesh_y, node, scenario.obstacles, _exact).uncertain_fraction
        for node in _nodes(scenario)
    ]
    assert max(rates) < 0.25, f"fell back on too much: {max(rates):.3f}"


def test_a_world_with_no_obstacles_sees_everything():
    scenario = vendored.scenario("open_pair")
    mesh_x, mesh_y = _lattice(scenario, 0.5)
    result = visible(mesh_x, mesh_y, scenario.true_goal_position, scenario.obstacles, _exact)
    assert result.visible.all()
    assert not result.uncertain.any()
