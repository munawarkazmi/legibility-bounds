"""The vendored geometry is the right one, and behaves as the bound assumes.

Two of these tests are about provenance: the submodule is present and sits on
the commit the results were computed against.

The other three are load bearing. The whole formulation rests on two facts
about the objective, and neither is obvious from reading its definition. They
are asserted here against the vendored implementation rather than argued in
prose, so that an upstream change which broke either one would fail this
suite instead of quietly invalidating a bound.
"""

from __future__ import annotations

import subprocess

import pytest

from legibility_bounds import vendored


def test_the_submodule_is_checked_out_at_the_pinned_commit():
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=vendored.VENDOR_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert head == vendored.PINNED_COMMIT, (
        f"the vendored geometry is at {head}, but every number in this "
        f"repository was computed against {vendored.PINNED_COMMIT}"
    )


def test_the_vendored_cost_to_go_reproduces_the_scenario_property():
    """The cost the scenario carries as a machine-checked fact is the cost we get.

    open_pair records its own optimal cost from the start to goal A. Reading
    it from the scenario file rather than typing it means this test cannot
    drift from the world it is about.
    """
    scenario = vendored.scenario("open_pair")
    recorded = [
        p for p in scenario.properties
        if p.kind == "geodesic_cost" and p.args.get("to") == "A"
    ]
    assert len(recorded) == 1, "open_pair should carry exactly one such property"
    computed = vendored.geodesic_cost(
        scenario.start, scenario.true_goal_position, scenario.obstacles
    )
    assert computed == pytest.approx(recorded[0].value, abs=1e-12)


def test_belief_depends_only_on_where_the_robot_is():
    """The travelled term cancels in the normalisation, so belief is a field.

    The observer scores each goal by C*(S -> G) - C(travelled) - C*(x -> G),
    and the travelled term is the same for every goal, so it disappears when
    the scores are normalised. That is what makes legibility a weighted
    average of a static scalar field along the path, and it is the fact the
    whole bounding argument is built on. If it stopped holding, the field
    would depend on the path's history and no per-point bound would be
    available.
    """
    scenario = vendored.scenario("open_pair")
    observer = vendored.Observer(condition="geodesic")
    start = scenario.start
    here = (7.0, 8.5)
    detours = [(2.0, 1.0), (11.5, 9.5), (6.0, 5.0), (0.5, 9.0)]

    direct = observer.posterior(scenario, [start, here])[scenario.true_goal]
    for detour in detours:
        roundabout = observer.posterior(
            scenario, [start, detour, here]
        )[scenario.true_goal]
        assert roundabout == pytest.approx(direct, abs=1e-12)


def test_legibility_does_not_depend_on_how_fast_the_robot_moves():
    """f(t) = T - t normalised by its own sum is a function of shape alone.

    The weights are T(1 - i/N) and they are divided by their sum, so T
    cancels exactly. Legibility therefore sees the path's shape and its
    sample count, and nothing about duration. This is why the bound does not
    have to range over the interval of durations the cost budget allows.
    """
    scenario = vendored.scenario("open_pair")
    observer = vendored.Observer(condition="geodesic")
    path = [scenario.start, (5.0, 9.0), scenario.true_goal_position]

    slow = vendored.metrics.evaluate(scenario, observer, path, speed=1.0)
    fast = vendored.metrics.evaluate(scenario, observer, path, speed=3.7)

    assert slow.legibility == fast.legibility
    assert slow.duration != fast.duration


def test_asking_for_a_scenario_that_is_not_vendored_says_what_is():
    with pytest.raises(vendored.VendorError) as raised:
        vendored.scenario("no_such_world")
    assert "open_pair" in str(raised.value)
