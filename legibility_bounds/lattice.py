"""A lattice over a world, carrying exact geodesic quantities at each point.

The bound needs three things at every point of the plane: the belief the
observer would hold there, the optimal cost to get there from the start, and
the optimal cost to reach the goal from it. All three are exact and come from
the vendored visibility-graph implementation. What a lattice adds is a finite
set of places to evaluate them, and the job of this module is to make a
lattice maximum into a real maximum rather than a sample of one.

One number per cell does that work: `detour`, an upper bound on the geodesic
distance between two points of the same cell. Everything else follows from it,
because both the belief and the reachability conditions are built out of
cost-to-go, and cost-to-go is 1-Lipschitz in the geodesic metric.

Cells near an obstacle
----------------------

Away from obstacles the detour is half a cell diagonal: the segment between
two points of the cell is obstacle free, so the geodesic between them is that
segment.

Near an obstacle it is not, and the difference has to be got right rather than
glossed. Two points a millimetre apart on opposite sides of a wall are a
wall's length apart geodesically, so no bound on the detour is available in
general, and none is claimed here. What is available is a bound under a
precondition that can be checked:

    if no obstacle is thinner than a cell, and no two obstacles are closer
    together than a cell, then a cell's free part is in one piece and meets
    at most one obstacle

Under that precondition a path between two free points of a cell can be run
inside the cell itself, going straight where it can and following the
obstacle boundary where it cannot. Inside a disc of radius r that costs at
most 2r of straight travel plus the boundary arc, and a convex arc inside a
disc of radius r is no longer than its circumference, so

    detour <= 2r + 2 pi r = 2 (1 + pi) r

The precondition is computed per scenario in `certifies_detour` and is
reported rather than assumed. Where it fails, the detour is infinite and the
bounds fall back to what holds unconditionally: a belief of one, and a
reachability test on Euclidean distance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import visibility
from .vendored import (
    CostToGoIndex,
    Observer,
    Scenario,
    segment_segment_distance,
)

# The constant in the detour bound, applied to the cell radius.
#
# What has to be bounded is the geodesic distance from a point of the cell to
# the lattice point at its centre, not between two arbitrary points of the
# cell, and the centre being free is what makes the argument short:
#
#   from a point outside a convex body, the ray heading directly away from
#   that body's nearest point never re-enters it. So the centre reaches the
#   circle along such a ray in exactly r, and any other point of the cell
#   reaches it in at most 2r, both staying inside the cell and outside the
#   obstacle;
#
#   and the free part of the circle is a single arc whenever the obstacle does
#   not cross the cell, so the two arrival points are joined along it in at
#   most its own length, 2 pi r.
#
#   so  D <= r + 2r + 2 pi r = (3 + 2 pi) r
#
# Two earlier versions were wrong. The first said 2(1 + pi) and was not a
# bound at all, having counted one diameter of straight travel where the
# construction needed two. The second said (4 + 2 pi) and was sound, but
# bounded the distance between two arbitrary points of a cell, which is a
# harder quantity than anything here needs.
#
# `tests/test_lattice.py` samples real point pairs in real band cells,
# targeting the corner cells where an obstacle can separate two points of one
# cell at all, and reports the headroom rather than only passing.
BAND_DETOUR_FACTOR = 3.0 + 2.0 * math.pi


class LatticeError(ValueError):
    """Raised when a lattice cannot be built for the inputs given."""


def _sigmoid(z):
    """Logistic function, without overflowing on large negative input."""
    out = np.empty_like(np.asarray(z, dtype=float))
    positive = z >= 0
    with np.errstate(over="ignore"):
        out[positive] = 1.0 / (1.0 + np.exp(-z[positive]))
        tail = np.exp(z[~positive])
        out[~positive] = tail / (1.0 + tail)
    return out


def _reference(polygon, a, b) -> bool:
    """The vendored guarded predicate, for the cases the fast path declines."""
    return polygon.segment_enters_interior(a, b)


def _point_segment_distance(px, py, a, b):
    """Distance from each point to one segment, vectorised."""
    ax, ay = float(a[0]), float(a[1])
    ex, ey = float(b[0]) - ax, float(b[1]) - ay
    length_squared = ex * ex + ey * ey
    if length_squared <= 0.0:
        return np.hypot(px - ax, py - ay)
    t = np.clip(((px - ax) * ex + (py - ay) * ey) / length_squared, 0.0, 1.0)
    return np.hypot(px - (ax + t * ex), py - (ay + t * ey))


def _near_any_obstacle(px, py, obstacles, radius):
    """Cells whose disc of the given radius meets an obstacle.

    Computed in plain floating point, and deliberately generous: counting a
    cell as near an obstacle when it is not costs tightness, since such a cell
    gets the weaker detour bound, while missing one would cost soundness. The
    margin makes the error fall on the safe side.
    """
    margin = radius * 1e-6 + 1e-12
    near = np.zeros(px.shape, dtype=bool)
    for polygon in obstacles:
        distance = np.full(px.shape, np.inf)
        for v, w in polygon.edges():
            np.minimum(distance, _point_segment_distance(px, py, v, w), out=distance)
        inside = np.ones(px.shape, dtype=bool)
        for v, w in polygon.edges():
            ex, ey = float(w[0]) - float(v[0]), float(w[1]) - float(v[1])
            inside &= ex * (py - float(v[1])) - ey * (px - float(v[0])) >= 0.0
        near |= inside | (distance <= radius + margin)
    return near


def minimum_width(polygon) -> float:
    """The narrowest the polygon is in any direction.

    For a convex polygon the narrowest direction is perpendicular to one of
    its edges, so the width is the smallest, over edges, of the furthest any
    vertex lies from that edge's line.
    """
    best = math.inf
    for v, w in polygon.edges():
        ex, ey = w[0] - v[0], w[1] - v[1]
        length = math.hypot(ex, ey)
        if length <= 0:
            continue
        furthest = max(
            abs(ex * (p[1] - v[1]) - ey * (p[0] - v[0])) / length
            for p in polygon.vertices
        )
        best = min(best, furthest)
    return best


def minimum_separation(obstacles) -> float:
    """The closest any two distinct obstacles come to each other."""
    best = math.inf
    for i, first in enumerate(obstacles):
        for second in obstacles[i + 1:]:
            for a, b in first.edges():
                for c, d in second.edges():
                    best = min(best, segment_segment_distance(a, b, c, d))
    return best


def _crossings_with_circle(px, py, radius, a, b, tolerance):
    """How many times one segment crosses each cell's circle, and where it is
    too close to call.

    Returns the count and a mask of the cells whose count cannot be trusted,
    which is any cell where the segment is nearly tangent to the circle or
    meets it nearly at an endpoint. Those cells are treated as uncertified
    rather than guessed at.
    """
    ax, ay = float(a[0]), float(a[1])
    dx, dy = float(b[0]) - ax, float(b[1]) - ay
    fx, fy = ax - px, ay - py

    quadratic = dx * dx + dy * dy
    linear = 2.0 * (fx * dx + fy * dy)
    constant = fx * fx + fy * fy - radius * radius

    if quadratic <= 0.0:
        return np.zeros(px.shape, dtype=int), np.zeros(px.shape, dtype=bool)

    discriminant = linear * linear - 4.0 * quadratic * constant
    # A tangency only matters where it actually touches the segment. The line
    # through an edge can graze the circle far beyond that edge's ends, and
    # treating those cells as doubtful would cost certification for nothing.
    grazing = -linear / (2.0 * quadratic)
    unsure = (np.abs(discriminant) <= tolerance) & (
        (grazing >= -tolerance) & (grazing <= 1.0 + tolerance)
    )
    positive = discriminant > tolerance
    root = np.sqrt(np.where(positive, discriminant, 0.0))

    count = np.zeros(px.shape, dtype=int)
    for sign in (-1.0, 1.0):
        t = (-linear + sign * root) / (2.0 * quadratic)
        inside = positive & (t > tolerance) & (t < 1.0 - tolerance)
        near_end = positive & (np.abs(t) <= tolerance) | (
            positive & (np.abs(t - 1.0) <= tolerance)
        )
        count += inside.astype(int)
        unsure |= near_end
    return count, unsure


def cells_certified(px, py, obstacles, radius: float):
    """Which cells the detour bound may be claimed for, one by one.

    Two things have to hold and both are local, which is why this is decided
    per cell rather than per world.

    No obstacle may pass clean through a cell, since that splits the free part
    in two and puts the halves a whole obstacle apart rather than a cell
    apart. A convex obstacle crosses a cell exactly when its boundary meets
    the cell's circle four times, so the crossings are counted.

    And no cell may meet two obstacles at once, since the argument follows a
    single boundary.

    An earlier version tested `minimum_width(obstacle) > 2 r` for the whole
    world instead. That is not sufficient and the difference is not academic:
    minimum width is a global property, and a convex polygon with a sharp
    vertex, a long acute triangle for instance, can be far wider than a cell
    overall while its tip is thinner than one and passes straight through.
    Every obstacle in the vendored suite is a rectangle, so no committed
    number ever depended on the difference, but the condition was stated as
    though general and was not.
    """
    certified = np.ones(px.shape, dtype=bool)
    if not obstacles:
        return certified

    tolerance = max(radius, 1.0) * 1e-9
    touching = np.zeros(px.shape, dtype=int)
    for polygon in obstacles:
        distance = np.full(px.shape, np.inf)
        for v, w in polygon.edges():
            np.minimum(distance, _point_segment_distance(px, py, v, w), out=distance)
        meets = distance <= radius
        touching += meets.astype(int)

        crossings = np.zeros(px.shape, dtype=int)
        unsure = np.zeros(px.shape, dtype=bool)
        for v, w in polygon.edges():
            count, doubtful = _crossings_with_circle(px, py, radius, v, w, tolerance)
            crossings += count
            unsure |= doubtful
        certified &= ~(meets & (unsure | (crossings >= 4)))

    return certified & (touching <= 1)


@dataclass(frozen=True)
class Lattice:
    """Exact geodesic quantities at every usable point of a square lattice.

    Every array below has the shape of the lattice. `usable` is false where a
    point has no obstacle-avoiding route to the start or to a goal, which
    includes every point inside an obstacle, and the other arrays carry no
    meaning there.

    `log_odds` is the log of the odds against the true goal at the lattice
    point, which is what the belief bound is stated in. `detour` is the one
    number per cell that everything else rests on.
    """

    scenario_id: str
    observer: str
    grid: float
    x: np.ndarray
    y: np.ndarray
    usable: np.ndarray
    near_obstacle: np.ndarray
    belief: np.ndarray
    log_odds: np.ndarray
    detour: np.ndarray
    motion_detour: np.ndarray
    geodesic_to_start: np.ndarray
    geodesic_to_goal: np.ndarray
    euclidean_to_start: np.ndarray
    euclidean_to_goal: np.ndarray
    beta: float
    respect_keep_out: bool = False

    @property
    def detour_certified(self) -> bool:
        """Whether every usable band cell could claim the detour bound."""
        return self.uncertified_cells == 0

    @property
    def cell_radius(self) -> float:
        """Half the diagonal: the furthest a point can be from its lattice point."""
        return self.grid * math.sqrt(2) / 2.0

    @property
    def band_detour(self) -> float:
        return BAND_DETOUR_FACTOR * self.cell_radius

    @property
    def uncertified_cells(self) -> int:
        unbounded = ~np.isfinite(self.detour) | ~np.isfinite(self.motion_detour)
        return int((unbounded & self.usable).sum())

    def belief_bound(self) -> np.ndarray:
        """An upper bound on the belief anywhere in each cell.

        Write the belief as odds against the true goal:

            b = 1 / (1 + sum over the other goals of
                          (p_G / p_A) exp(beta[(C_G - g_G) - (C_A - g_A)]))

        Bounding `b` from above does not need an upper bound on any single
        cost-to-go, which is the thing an obstacle makes impossible. It needs
        a lower bound on the difference between two of them. Every cost-to-go
        is 1-Lipschitz in the geodesic metric, so moving a distance `D` inside
        a cell shifts that difference by at most `2D`, and

            b(x) <= 1 / (1 + odds(p) exp(-2 beta D))

        holds over the whole cell. Where `D` is infinite this returns one,
        which is all that can be said without it.
        """
        with np.errstate(over="ignore", invalid="ignore"):
            shifted = self.log_odds - 2.0 * self.beta * self.detour
            bound = _sigmoid(-shifted)
        return np.clip(np.where(np.isfinite(self.detour), bound, 1.0), 0.0, 1.0)

    def reachable(self, spent: float, remaining: float) -> np.ndarray:
        """Cells that may hold a path point with `spent` arc behind it.

        A point on a trajectory that has travelled `spent` and must still
        reach the goal within `remaining` satisfies both geodesic conditions,
        since arc length is at least geodesic distance.

        Two necessary conditions are applied and a cell has to pass both. The
        geodesic at the lattice point, relaxed by the cell's own detour, is
        the sharper one wherever that detour is finite. Euclidean distance is
        the weaker one but it needs nothing at all: a path avoiding obstacles
        is at least as long as the straight line, so it can never exclude a
        cell that should be in, even where the geodesic inside the cell is
        beyond reach.
        """
        with np.errstate(invalid="ignore"):
            geodesic = (self.geodesic_to_start <= spent + self.motion_detour) & (
                self.geodesic_to_goal <= remaining + self.motion_detour
            )
        euclidean = (self.euclidean_to_start <= spent + self.cell_radius) & (
            self.euclidean_to_goal <= remaining + self.cell_radius
        )
        return self.usable & euclidean & geodesic


def lipschitz_constant(observer: Observer) -> float:
    """A bound on the gradient of the belief, in the observer's own metric.

    Kept because it is the plainest statement of why a cell can be bounded at
    all, and because the reachability module reports it. The belief is a
    softmax whose terms are cost-to-go multiplied by beta, and cost-to-go has
    unit gradient, so

        |grad b| <= beta [ b (1 - b) + b * sum of the other beliefs ]
                  = 2 beta b (1 - b)
                  <= beta / 2

    for any number of goals. The belief bound above uses the odds form
    instead, which is the same fact stated multiplicatively and is tighter.
    """
    return lipschitz_constant_from_beta(observer.beta)


def lipschitz_constant_from_beta(beta: float) -> float:
    return beta / 2.0


def build(
    scenario: Scenario,
    observer: Observer,
    grid: float,
    progress=None,
    respect_keep_out: bool = False,
) -> Lattice:
    """Evaluate the exact geometry at every point of a lattice of this world.

    With `respect_keep_out` the lattice describes the safety-constrained
    problem instead: trajectories that never enter a keep-out zone. Keep-out
    zones constrain the robot and not the watcher, so they enter the
    reachability conditions and leave the belief alone, and that asymmetry is
    the whole of the difference. It costs a second geodesic sweep, because the
    distances the motion obeys and the distances the observer reasons with are
    then two different things over the same lattice.
    """
    if grid <= 0:
        raise LatticeError(f"grid spacing must be positive, found {grid!r}")

    bounds = scenario.bounds
    xs = np.arange(bounds.xmin, bounds.xmax + grid, grid)
    ys = np.arange(bounds.ymin, bounds.ymax + grid, grid)
    mesh_x, mesh_y = np.meshgrid(xs, ys)
    shape = mesh_x.shape

    start = scenario.start
    goal = scenario.true_goal_position
    obstacles = scenario.obstacles
    goal_positions = [g.position for g in scenario.goals]

    # What blocks the robot, and what the watcher reasons about, are not the
    # same set once keep-out zones are respected.
    blockers = tuple(obstacles)
    if respect_keep_out:
        blockers = blockers + tuple(scenario.keep_out_zones)

    targets = list(goal_positions)
    if start not in targets:
        targets.append(start)
    index = CostToGoIndex(obstacles, targets) if obstacles else None

    baseline = observer.baseline(scenario, index)
    prior = observer.prior_for(scenario)
    radius = grid * math.sqrt(2) / 2.0

    euclid_start = np.hypot(mesh_x - start[0], mesh_y - start[1])
    euclid_goal = np.hypot(mesh_x - goal[0], mesh_y - goal[1])
    wanted = list(dict.fromkeys([start, goal, *goal_positions]))

    def straight_costs():
        return {p: np.hypot(mesh_x - p[0], mesh_y - p[1]) for p in wanted}

    # Distances the motion obeys, which the reachability conditions use.
    if blockers:
        motion_index = CostToGoIndex(blockers, targets)
        motion = _geodesic_costs(
            mesh_x, mesh_y, blockers, motion_index, targets, wanted, progress
        )
    else:
        motion = straight_costs()

    # Distances the observer reasons with, which the belief uses. These are
    # the same arrays unless keep-out zones are being respected, since then
    # and only then do the two blocker sets differ.
    if not respect_keep_out or not scenario.keep_out_zones:
        seen = motion
    elif obstacles:
        seen = _geodesic_costs(
            mesh_x, mesh_y, obstacles, index, targets, wanted, progress
        )
    else:
        seen = straight_costs()

    to_start, to_goal = motion[start], motion[goal]
    usable = np.isfinite(to_start) & np.isfinite(to_goal)
    for position in goal_positions:
        usable &= np.isfinite(seen[position])

    def band_and_detour(against):
        """Cells near the given blockers, and the detour bound for each.

        A clear cell is bounded by its own radius, since the segment from its
        centre to any of its points misses everything. A band cell takes the
        detour bound where its geometry allows it to be claimed, and nothing
        otherwise.
        """
        if not against:
            return (
                np.zeros(shape, dtype=bool),
                np.full(shape, radius),
            )
        band = _near_any_obstacle(mesh_x, mesh_y, against, radius) & usable
        allowed = cells_certified(mesh_x, mesh_y, against, radius)
        return band, np.where(
            band, np.where(allowed, BAND_DETOUR_FACTOR * radius, np.inf), radius
        )

    # Two different detours, because they bound two different things. The
    # belief is a function of the observer's cost-to-go, which is defined over
    # obstacles alone, so a keep-out zone cannot make the belief harder to
    # bound inside a cell. The reachability conditions are about where the
    # robot can be, so they answer to everything that blocks it.
    #
    # Using one array for both was a real error and not a tidiness point: it
    # made the safety-constrained bound come out above the unconstrained one
    # in `keep_out_shortcut`, because the keep-out boundary manufactured band
    # cells for a quantity it has no bearing on.
    near, detour = band_and_detour(obstacles)
    if blockers == tuple(obstacles):
        near_motion, motion_detour = near, detour
    else:
        near_motion, motion_detour = band_and_detour(blockers)
    certified = np.isfinite(detour) & np.isfinite(motion_detour)

    # The observer's own cost-to-go, which is the geodesic for the observer
    # who can see the room and the straight line for the one who cannot. The
    # reachability terms above are always geodesic, because they are about
    # where the robot can physically be rather than about what the watcher
    # believes.
    def observed(position):
        if observer.condition == "geodesic":
            return seen[position]
        return np.hypot(mesh_x - position[0], mesh_y - position[1])

    true_goal = scenario.true_goal
    true_position = scenario.true_goal_position
    own = baseline[true_goal] - observed(true_position)
    terms = []
    for g in scenario.goals:
        if g.id == true_goal:
            continue
        # Unusable points carry infinities on both sides, and their difference
        # is meaningless rather than large. They are zeroed here and masked
        # out below; nothing reads their belief.
        with np.errstate(invalid="ignore"):
            difference = (baseline[g.id] - observed(g.position)) - own
        difference = np.where(np.isfinite(difference), difference, 0.0)
        terms.append(math.log(prior[g.id] / prior[true_goal]) + observer.beta * difference)

    if terms:
        stacked = np.stack(terms)
        peak = stacked.max(axis=0)
        log_odds = peak + np.log(np.exp(stacked - peak).sum(axis=0))
    else:
        # A single goal: the observer believes in it with certainty and the
        # odds against it are zero, so the log odds are minus infinity.
        log_odds = np.full(shape, -np.inf)

    belief = np.where(usable, _sigmoid(-log_odds), 0.0)

    return Lattice(
        scenario_id=scenario.id,
        observer=observer.name,
        grid=grid,
        x=mesh_x,
        y=mesh_y,
        usable=usable,
        near_obstacle=near,
        belief=belief,
        log_odds=log_odds,
        detour=detour,
        motion_detour=motion_detour,
        geodesic_to_start=to_start,
        geodesic_to_goal=to_goal,
        euclidean_to_start=euclid_start,
        euclidean_to_goal=euclid_goal,
        beta=observer.beta,
        respect_keep_out=respect_keep_out,
    )


def _geodesic_costs(mesh_x, mesh_y, obstacles, index, nodes_from, wanted, progress):
    """Cost-to-go to every wanted target at every lattice point, in one sweep.

    A shortest path from a point to a target either runs straight there or
    turns first at an obstacle vertex, and that first hop is by definition a
    visible segment. So the cost is the smallest, over nodes visible from the
    point, of the hop plus the node's own distance to the target. That is the
    vendored index's own reasoning; what changes here is that the visibility
    test is answered for the whole lattice at once.

    The node-to-target distances come from the index's public interface. A
    node is visible from itself, so asking the index for the cost from a node
    returns exactly the distance it precomputed for it.
    """
    nodes, seen = [], set()
    for obstacle in obstacles:
        for vertex in obstacle.vertices:
            if vertex not in seen:
                seen.add(vertex)
                nodes.append(vertex)
    for target in nodes_from:
        if target not in seen:
            seen.add(target)
            nodes.append(target)

    from_node = {
        target: [index.cost_to(node, target) for node in nodes] for target in wanted
    }
    cost = {target: np.full(mesh_x.shape, np.inf) for target in wanted}

    for i, node in enumerate(nodes):
        if progress is not None:
            progress(i, len(nodes))
        seen_from = visibility.visible(
            mesh_x, mesh_y, node, obstacles, _reference
        ).visible
        hop = np.hypot(mesh_x - node[0], mesh_y - node[1])
        for target in wanted:
            remainder = from_node[target][i]
            if remainder == math.inf:
                continue
            np.minimum(
                cost[target], np.where(seen_from, hop + remainder, np.inf),
                out=cost[target],
            )
    return cost
