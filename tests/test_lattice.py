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


@pytest.mark.parametrize(
    "name", ["wall_choice", "narrow_gap", "pillar_aisle", "door_pair"]
)
def test_the_detour_bound_holds_against_real_geodesics(name):
    """The geometric claim the band bound rests on, checked rather than argued.

    The claim is that two free points of the same cell are no further apart
    geodesically than (4 + 2 pi) times the cell radius, given that no obstacle
    is thinner than a cell and no two obstacles are closer together than one.
    This samples point pairs inside real band cells and measures the true
    geodesic with the vendored implementation.

    The first version of the constant was 24 per cent smaller, derived by
    counting one diameter of straight travel where the construction needs two.
    It passed on one world with a single seed, which is why this now runs over
    four worlds and reports the headroom: a test that only says "passed" would
    not have distinguished a sound constant from a lucky one.
    """
    scenario = vendored.scenario(name)
    observer = vendored.Observer(condition="geodesic")
    built = lattice_module.build(scenario, observer, TEST_GRID)
    assert built.detour_certified, f"{name} at this lattice should certify"
    band = np.argwhere(built.near_obstacle & built.usable)
    assert len(band) > 0

    rng = np.random.default_rng(19)
    radius = built.cell_radius

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

    checked = 0
    detoured = 0
    worst = 0.0
    worst_detoured = 0.0
    for row, col in sampled:
        cx, cy = float(built.x[row, col]), float(built.y[row, col])
        for _ in range(20):
            offsets = [float(v) for v in rng.uniform(-radius, radius, size=4)]
            a = (cx + offsets[0], cy + offsets[1])
            b = (cx + offsets[2], cy + offsets[3])
            if any(ob.contains_interior(a) or ob.contains_interior(b)
                   for ob in scenario.obstacles):
                continue
            measured = vendored.geodesic_cost(a, b, scenario.obstacles)
            worst = max(worst, measured / radius)
            assert measured <= built.band_detour + 1e-9, (
                f"{name}: geodesic {measured:.4f} between {a} and {b} exceeds "
                f"the claimed detour bound {built.band_detour:.4f}"
            )
            checked += 1
            # A pair whose straight line is already free tells us nothing
            # about a bound that exists for pairs the obstacle separates.
            straight = math.hypot(a[0] - b[0], a[1] - b[1])
            if measured > straight + 1e-9:
                detoured += 1
                worst_detoured = max(worst_detoured, measured / radius)

    assert checked > 100, f"{name}: only {checked} pairs were actually testable"
    assert detoured > 0, (
        f"{name}: not one sampled pair was separated by the obstacle, so this "
        f"test never exercised the case the bound exists for"
    )
    # Recorded so a future change to the constant can be judged against what
    # the geometry actually does rather than against whether the test passed.
    print(
        f"\n{name}: worst detour {worst:.3f} cell radii overall and "
        f"{worst_detoured:.3f} among the {detoured} pairs the obstacle "
        f"separated, against a claimed {lattice_module.BAND_DETOUR_FACTOR:.3f}, "
        f"over {checked} pairs"
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
