"""A witness is a trajectory, so what it claims is what it scores.

Nothing here asserts that a witness is good. It asserts that it exists, that
it is admissible, and that the vendored metric agrees with what the witness
says about itself. Those are the properties that make it a lower bound; being
better than a local search is a result rather than a requirement, and it is
not true in every world.
"""

from __future__ import annotations

import pytest

from legibility_bounds import lattice as lattice_module
from legibility_bounds import vendored
from legibility_bounds import witness as witness_module

TEST_GRID = 0.05
CEILING = 1.25


@pytest.fixture
def observer():
    return vendored.Observer(condition="geodesic")


@pytest.mark.parametrize("name", ["open_pair", "wall_choice", "door_pair"])
def test_a_witness_is_admissible_and_scores_what_it_claims(name, observer):
    scenario = vendored.scenario(name)
    built = lattice_module.build(scenario, observer, TEST_GRID)
    found = witness_module.best_witness(scenario, observer, CEILING, built)
    assert found is not None, f"no witness could be built in {name}"

    scored = vendored.metrics.evaluate(scenario, observer, found.points)
    assert scored.feasible, scored.infeasibility
    assert scored.legibility == pytest.approx(found.legibility, abs=1e-12)
    assert scored.cost_ratio == pytest.approx(found.cost_ratio, abs=1e-12)
    assert scored.cost_ratio <= CEILING + 1e-9
    assert 0.0 <= found.pullback <= 1.0
    assert found.points[0] == scenario.start
    assert found.points[-1] == scenario.true_goal_position


@pytest.mark.parametrize("name", ["open_pair", "wall_choice", "door_pair"])
def test_a_witness_never_exceeds_the_bound(name, observer):
    """The two ends of the interval have to be on the right sides of it."""
    from legibility_bounds.reachability import reachability_bound

    scenario = vendored.scenario(name)
    built = lattice_module.build(scenario, observer, TEST_GRID)
    bound = reachability_bound(
        scenario, observer, CEILING, grid=TEST_GRID, built=built
    )
    found = witness_module.best_witness(scenario, observer, CEILING, built)
    assert found is not None
    assert found.legibility <= bound.bound


def test_a_safe_witness_enters_no_keep_out_zone(observer):
    scenario = vendored.scenario("keep_out_shortcut")
    built = lattice_module.build(
        scenario, observer, TEST_GRID, respect_keep_out=True
    )
    found = witness_module.best_witness(
        scenario, observer, CEILING, built, respect_keep_out=True
    )
    assert found is not None
    scored = vendored.metrics.evaluate(scenario, observer, found.points)
    assert scored.feasible
    assert scored.safety.keep_out_entries == 0
    assert found.keep_out_entries == 0


def test_a_safe_witness_needs_the_matching_lattice(observer):
    scenario = vendored.scenario("keep_out_shortcut")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    with pytest.raises(witness_module.WitnessError):
        witness_module.build(
            scenario, observer, CEILING, built, respect_keep_out=True
        )


def test_at_a_ceiling_of_one_the_witness_is_the_shortest_path(observer):
    """No budget to spend means nowhere to go, and the pullback should say so."""
    scenario = vendored.scenario("open_pair")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    found = witness_module.best_witness(scenario, observer, 1.0, built)
    assert found is not None
    assert found.cost_ratio == pytest.approx(1.0, abs=1e-6)
    straight = vendored.metrics.evaluate(
        scenario, observer, [scenario.start, scenario.true_goal_position]
    )
    assert found.legibility == pytest.approx(straight.legibility, abs=1e-4)


def test_asking_for_no_anchors_is_refused(observer):
    scenario = vendored.scenario("open_pair")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    with pytest.raises(witness_module.WitnessError):
        witness_module.build(scenario, observer, CEILING, built, anchors=0)


def test_a_geometry_failure_is_not_read_as_infeasibility(observer):
    """The narrow catch is deliberate and this is what it protects.

    The pullback search treats a waypoint landing inside an obstacle as a
    fact about the geometry. An earlier version caught every exception there,
    and a type error in the interpolation was reported as "no admissible
    trajectory exists" in every world with an obstacle. Anything that is not a
    geometry error must still escape.
    """
    scenario = vendored.scenario("wall_choice")
    built = lattice_module.build(scenario, observer, TEST_GRID)

    class Boom(RuntimeError):
        pass

    def explode(*args, **kwargs):
        raise Boom("not a geometry error")

    original = witness_module._join
    witness_module._join = explode
    try:
        with pytest.raises(Boom):
            witness_module.build(scenario, observer, CEILING, built, anchors=1)
    finally:
        witness_module._join = original
