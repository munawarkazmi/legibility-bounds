"""The lattice says true things about a world with obstacles.

A coarse lattice is used throughout. Building one is the expensive step and
none of these tests are about resolution: they are about the quantities being
the ones they claim to be, and about the two inequalities the treatment of
obstacle-adjacent cells rests on.
"""

from __future__ import annotations

import math

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


def test_the_belief_bound_is_above_the_belief_and_is_a_probability(walled):
    _, _, built = walled
    bound = built.belief_bound()
    usable = built.usable
    assert (bound[usable] >= built.belief[usable] - 1e-12).all()
    assert (bound >= 0.0).all() and (bound <= 1.0).all()
    # The band is bounded more loosely than the rest, but no longer by the
    # cap of one wherever the detour is certified.
    band = built.near_obstacle & usable
    if built.detour_certified and band.any():
        assert (bound[band] < 1.0).any()


def _detours_to_centre(name):
    """The geometric claim the band bound rests on, checked rather than argued.

    The claim is that a free point of a cell is no further from that cell's own
    lattice point, geodesically, than (3 + pi) times the cell radius, given that
    no obstacle is thinner than a cell and no two obstacles are closer together
    than one. That is the quantity `belief_bound` and `reachable` use, since
    both read a value at the lattice point and relax it to cover the cell.

    The geodesic between two arbitrary points of a cell is a different and
    harder quantity, and nothing in the library needs it. This measures it too,
    and reports it, but does not assert the constant against it. An earlier
    version of this test did assert it, which passed only because the constant
    was loose enough to absorb the difference: it was checking a claim the
    argument had stopped making.

    The first version of the constant was 24 per cent smaller than the version
    that replaced it, derived by counting one diameter of straight travel where
    the construction needed two. It passed on one world with a single seed,
    which is why this now runs over four worlds and reports the headroom: a
    test that only says "passed" would not have distinguished a sound constant
    from a lucky one.

    This does not require that the obstacle separate anything in every world,
    because it does not. Measured at this lattice, `wall_choice`, `narrow_gap`
    and `pillar_aisle` produce no separated point at all in several thousand
    samples each: their obstacles are wider than a cell everywhere, including
    at the corners, so nothing can sit between a point and the centre of its
    own cell, and the true detour there is simply the cell radius. Only
    `door_pair` has a feature thin enough to separate. The non-trivial case is
    therefore asserted separately, in the test below, rather than demanded here
    of worlds whose geometry cannot supply it.
    """
    scenario = vendored.scenario(name)
    observer = vendored.Observer(condition="geodesic")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    assert built.detour_certified, f"{name} at this lattice should certify"
    band = np.argwhere(built.near_obstacle & built.usable)
    assert len(band) > 0

    rng = np.random.default_rng(19)
    radius = built.cell_radius
    half = built.grid / 2.0

    # Cells beside an obstacle corner, and a random spread of the rest.
    #
    # The precondition says obstacles are wider than a cell, so two points of
    # one cell can only be separated by an obstacle where the segment between
    # them clips a corner. Sampling uniformly over the band almost never lands
    # there, which would leave this test passing without ever measuring a
    # detour. Corner cells are chosen deliberately for that reason.
    corners = [v for ob in scenario.obstacles for v in ob.vertices]
    centres = np.stack([built.x[band[:, 0], band[:, 1]],
                        built.y[band[:, 0], band[:, 1]]], axis=1)
    to_corner = np.min(
        np.stack([
            np.hypot(centres[:, 0] - c[0], centres[:, 1] - c[1]) for c in corners
        ]),
        axis=0,
    )
    beside_a_corner = band[np.argsort(to_corner)[:20]]
    spread = band[rng.choice(len(band), size=min(20, len(band)), replace=False)]
    sampled = np.concatenate([beside_a_corner, spread])

    def free(q):
        return not any(ob.contains_interior(q) for ob in scenario.obstacles)

    checked = 0
    detoured = 0
    worst = 0.0
    worst_detoured = 0.0
    worst_pair = 0.0
    for row, col in sampled:
        cx, cy = float(built.x[row, col]), float(built.y[row, col])
        centre = (cx, cy)
        if not free(centre):
            continue
        for _ in range(20):
            # Over the cell itself, which is the square of side `grid`, not the
            # square of side twice the cell radius. The cell radius is the half
            # diagonal, so drawing offsets from it samples a box 41 per cent
            # wider than the cell in each direction. That is still sound, being
            # a superset, but it puts the worst reported figure at the corner of
            # a box no cell has, and that figure is what the looseness ratio in
            # the README is computed from.
            offsets = [float(v) for v in rng.uniform(-half, half, size=4)]
            a = (cx + offsets[0], cy + offsets[1])
            b = (cx + offsets[2], cy + offsets[3])
            if not free(a):
                continue
            measured = vendored.geodesic_cost(a, centre, scenario.obstacles)
            worst = max(worst, measured / radius)
            assert measured <= built.band_detour + 1e-9, (
                f"{name}: geodesic {measured:.4f} from {a} to its own lattice "
                f"point {centre} exceeds the claimed detour bound "
                f"{built.band_detour:.4f}"
            )
            checked += 1
            # A point whose straight line to the centre is already free tells
            # us nothing about a bound that exists for the ones it is not.
            direct = math.hypot(a[0] - cx, a[1] - cy)
            if measured > direct + 1e-9:
                detoured += 1
                worst_detoured = max(worst_detoured, measured / radius)
            if free(b):
                worst_pair = max(
                    worst_pair,
                    vendored.geodesic_cost(a, b, scenario.obstacles) / radius,
                )

    assert checked > 100, f"{name}: only {checked} points were actually testable"
    # Recorded so a future change to the constant can be judged against what
    # the geometry actually does rather than against whether the test passed.
    # The pair figure is reported and deliberately not asserted: see above.
    print(
        f"\n{name}: worst detour to centre {worst:.3f} cell radii overall and "
        f"{worst_detoured:.3f} among the {detoured} points the obstacle "
        f"separated, against a claimed {lattice_module.BAND_DETOUR_FACTOR:.3f}, "
        f"over {checked} points. Worst between two points of one cell "
        f"{worst_pair:.3f}, not claimed."
    )
    return {"checked": checked, "detoured": detoured, "worst": worst}


@pytest.mark.parametrize(
    "name", ["wall_choice", "narrow_gap", "pillar_aisle", "door_pair"]
)
def test_the_detour_bound_holds_against_real_geodesics(name):
    """No sampled point of any cell exceeds the constant, in four worlds."""
    _detours_to_centre(name)


def test_the_detour_bound_is_exercised_where_an_obstacle_can_separate():
    """The bound's non-trivial case, kept under test rather than assumed.

    Three of the four worlds above cannot separate a point from the centre of
    its own cell, so a bound that only ever ran on them would be checked
    against nothing: the straight segment is free and the detour is the cell
    radius, whatever constant is written down.

    `door_pair` can, because one of its features is thin enough near a corner
    for a point of a cell to sit beyond it. This pins that, so a future change
    to the geometry, the lattice or the cell selection that quietly stops
    exercising the wrapping case fails here instead of passing everywhere.

    Worth stating plainly, because it bears on how much the constant is worth:
    even here the detour stays under one cell radius. Points do go round the
    obstacle rather than through it, but they are close enough to their own
    lattice point that the way round is still shorter than the radius. So at
    this lattice no world in the suite needs the wrapping argument at all, and
    the constant is slack of roughly six times over rather than the four the
    pair measurement used to suggest. That is a reason to doubt the constant is
    the place to spend effort, not a reason to weaken this test.
    """
    found = _detours_to_centre("door_pair")
    assert found["detoured"] > 0, (
        "door_pair no longer separates any sampled point from its own centre, "
        "so the wrapping case is now untested in every world"
    )


def test_no_constant_below_the_exhibited_configuration_can_hold():
    """The lower bound the paper's limitations section rests on.

    Slack measured against the suite says how much room there is in these
    worlds. It does not say how much of it a sharper argument could take, and
    the two are very different: most of the measured looseness is a property of
    the scenarios rather than of the proof. What bounds the argument is a
    configuration the constant has to survive, and this is one.

    It is deliberately not a world from the suite. The obstacle is thinner than
    a cell, so it would fail the global width test that `cells_certified`
    replaced, and it passes the per-cell test that is actually in force. That is
    the point: it bounds the constant being used rather than the one an earlier
    version of the argument assumed.

    `tools/detour_lower_bound.py` writes the same numbers to results. This is
    here so that a change to the certification rule, the geometry, or the
    constant cannot quietly invalidate a published claim without a test saying
    so.
    """
    radius = 1.0
    lattice_point = (0.0, 0.0)
    point = (-0.6055, -0.7958)
    obstacle = vendored.ConvexPolygon(
        id="lower_bound",
        vertices=((-1.9001, -1.0448), (0.8577, -0.5141), (0.8763, 0.4817)),
    )

    px, py = np.array([[lattice_point[0]]]), np.array([[lattice_point[1]]])
    assert lattice_module.cells_certified(px, py, [obstacle], radius)[0, 0], (
        "the exhibited configuration no longer certifies the precondition, so "
        "it bounds nothing and the paper's limitations section is wrong"
    )
    assert not obstacle.contains_interior(lattice_point)
    assert not obstacle.contains_interior(point)
    assert math.hypot(*point) <= radius + 1e-9, "the point must lie in the cell"

    measured = vendored.geodesic_cost(point, lattice_point, [obstacle]) / radius
    assert measured > 3.4, (
        f"the exhibited configuration now reaches only {measured:.4f} cell "
        f"radii, so the stated lower bound no longer holds"
    )
    assert measured < lattice_module.BAND_DETOUR_FACTOR, (
        f"the geodesic {measured:.4f} exceeds the claimed bound "
        f"{lattice_module.BAND_DETOUR_FACTOR:.4f}. That is a violation of the "
        f"bound itself, not a lower bound on it"
    )
    assert lattice_module.minimum_width(obstacle) < 2.0 * radius, (
        "this configuration is supposed to be one the withdrawn global width "
        "test would have excluded; if it is no longer thinner than a cell it "
        "no longer makes that point"
    )


def test_a_lattice_too_coarse_for_its_obstacles_refuses_to_certify(walled):
    """A cell an obstacle passes clean through must say so rather than claim it."""
    scenario, observer, fine = walled
    assert fine.detour_certified, "wall_choice at this lattice should certify"

    narrowest = min(
        lattice_module.minimum_width(ob) for ob in scenario.obstacles
    )
    coarse = lattice_module.build(scenario, observer, narrowest * 2.0)
    assert not coarse.detour_certified
    assert coarse.uncertified_cells > 0
    banded = coarse.near_obstacle & coarse.usable
    assert (coarse.belief_bound()[banded & ~np.isfinite(coarse.detour)] == 1.0).all()


def test_a_sharp_vertex_defeats_the_global_width_test_but_not_this_one():
    """The reason the precondition is decided per cell rather than per world.

    Minimum width is a property of a whole obstacle. A convex polygon with a
    sharp vertex can be far wider than a cell overall while its tip is thinner
    than one and passes straight through, splitting a cell's free part in two
    and putting the halves an obstacle apart rather than a cell apart.

    The long acute triangle below has minimum width close to 2, so a global
    test at cell radius 0.5 would certify every cell in the world. A cell
    beside its tip is crossed by it, and this test asserts that the per-cell
    check refuses exactly that cell while accepting one out at the fat end.
    """
    needle = vendored.ConvexPolygon.from_vertices(
        "needle", [(0.0, 0.0), (20.0, 1.0), (20.0, -1.0)]
    )
    radius = 0.5
    assert lattice_module.minimum_width(needle) > 2.0 * radius, (
        "the point of this fixture is an obstacle a global width test accepts"
    )

    # Near the tip, where the triangle is 0.2 thick against a cell radius of
    # 0.5, so a cell centred just outside it still reaches free ground on the
    # far side and the triangle passes clean through. Spanning an obstacle
    # needs it thinner than the radius, not the diameter, since the centre has
    # to sit outside it to begin with.
    thin_x = np.array([[2.0]])
    thin_y = np.array([[0.15]])
    assert not lattice_module.cells_certified(
        thin_x, thin_y, [needle], radius
    )[0, 0]

    # Out at the blunt end, where it is thicker than the cell and only its
    # edge passes through.
    fat_x = np.array([[19.5]])
    fat_y = np.array([[1.3]])
    assert lattice_module.cells_certified(fat_x, fat_y, [needle], radius)[0, 0]


def test_only_cells_holding_a_corner_need_the_wrapping_bound(walled):
    """The band is bounded by the cell radius except where a corner sits.

    A cell that holds no vertex and that the obstacle does not pass through
    has its obstacle boundary inside a single edge, so the free part of the
    cell is convex and the segment from its centre to any free point of it is
    free. Nothing has to wrap, and the detour is the cell radius.
    """
    scenario, _, built = walled
    band = built.near_obstacle & built.usable
    assert band.any()

    corners = [v for ob in scenario.obstacles for v in ob.vertices]
    wrapping = band & (built.detour > built.cell_radius) & np.isfinite(built.detour)
    plain = band & (built.detour == built.cell_radius)

    assert plain.any(), "most band cells should need no wrapping bound"
    assert plain.sum() > wrapping.sum(), (
        "cells holding a corner should be the rare case, not the common one"
    )

    # Every cell that does wrap has a corner within its own radius.
    rows, cols = np.where(wrapping)
    for row, col in zip(rows, cols):
        point = (float(built.x[row, col]), float(built.y[row, col]))
        nearest = min(math.hypot(point[0] - c[0], point[1] - c[1]) for c in corners)
        assert nearest <= built.cell_radius + 1e-9

    # And every plain band cell really does have a convex free part, which is
    # what the claim rests on: its boundary lies within one edge.
    rows, cols = np.where(plain)
    rng = np.random.default_rng(5)
    for index in rng.choice(len(rows), size=min(30, len(rows)), replace=False):
        point = (float(built.x[rows[index], cols[index]]),
                 float(built.y[rows[index], cols[index]]))
        nearest = min(math.hypot(point[0] - c[0], point[1] - c[1]) for c in corners)
        assert nearest > built.cell_radius


def test_the_detour_is_the_cell_radius_where_the_free_part_is_convex(walled):
    """Measured, not argued: sample plain band cells and check nothing wraps."""
    scenario, _, built = walled
    plain = np.argwhere(
        built.near_obstacle & built.usable & (built.detour == built.cell_radius)
    )
    assert len(plain) > 0

    rng = np.random.default_rng(23)
    radius = built.cell_radius
    checked = 0
    for row, col in plain[rng.choice(len(plain), size=min(40, len(plain)), replace=False)]:
        centre = (float(built.x[row, col]), float(built.y[row, col]))
        for _ in range(15):
            offsets = [float(v) for v in rng.uniform(-radius, radius, size=2)]
            point = (centre[0] + offsets[0], centre[1] + offsets[1])
            if math.hypot(offsets[0], offsets[1]) > radius:
                continue
            if any(ob.contains_interior(point) for ob in scenario.obstacles):
                continue
            measured = vendored.geodesic_cost(point, centre, scenario.obstacles)
            straight = math.hypot(offsets[0], offsets[1])
            assert measured <= straight + 1e-9, (
                f"a plain band cell wrapped: {measured:.6f} against a straight "
                f"{straight:.6f} between {point} and {centre}"
            )
            assert measured <= radius + 1e-9
            checked += 1
    assert checked > 100


def test_a_cell_meeting_two_obstacles_is_not_certified():
    """The argument follows one boundary, so two obstacles is out of scope."""
    scenario = vendored.scenario("narrow_gap")
    assert len(scenario.obstacles) >= 2

    # A cell wide enough to reach both sides of the gap.
    gap = lattice_module.minimum_separation(scenario.obstacles)
    assert math.isfinite(gap)
    observer = vendored.Observer(condition="geodesic")
    coarse = lattice_module.build(scenario, observer, gap * 2.0)
    assert coarse.uncertified_cells > 0


def test_an_obstacle_free_world_has_no_band_at_all(walled):
    scenario = vendored.scenario("open_pair")
    observer = vendored.Observer(condition="geodesic")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    assert not built.near_obstacle.any()
    assert built.usable.all()
    assert built.geodesic_to_goal == pytest.approx(built.euclidean_to_goal)
