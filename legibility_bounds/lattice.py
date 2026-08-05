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

# The constant in the detour bound above, applied to the cell radius.
#
#   the free part of a cell has boundary at most 2 pi r from the disc plus
#   2 pi r from the obstacle, since a convex arc inside a disc of radius r is
#   no longer than the disc's own perimeter;
#   reaching that boundary costs at most 2r from each of the two points;
#   and travelling the shorter way round a closed curve of length L costs at
#   most L / 2.
#
#   so  D <= 2r + 2 pi r + 2r = (4 + 2 pi) r
#
# The first version of this said 2(1 + pi), having counted one diameter of
# straight travel where there are two. That is 24 per cent too small, which
# would have made the bound not a bound. `tests/test_lattice.py` samples real
# point pairs in real band cells across four worlds and measures the true
# geodesic against this, and reports the headroom rather than only passing.
BAND_DETOUR_FACTOR = 4.0 + 2.0 * math.pi


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


def certifies_detour(obstacles, radius: float) -> bool:
    """Whether a cell of this radius is small enough for the detour bound.

    Two things have to hold. No obstacle may pass clean through a cell, which
    would split its free part in two and put the two halves a whole obstacle
    apart; that is ruled out when every obstacle is wider than the cell. And
    no cell may meet two obstacles at once, since the argument follows a
    single boundary; that is ruled out when obstacles are further apart than a
    cell.
    """
    if not obstacles:
        return True
    span = 2.0 * radius
    if any(minimum_width(ob) <= span for ob in obstacles):
        return False
    return minimum_separation(obstacles) > span


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
    geodesic_to_start: np.ndarray
    geodesic_to_goal: np.ndarray
    euclidean_to_start: np.ndarray
    euclidean_to_goal: np.ndarray
    beta: float
    detour_certified: bool

    @property
    def cell_radius(self) -> float:
        """Half the diagonal: the furthest a point can be from its lattice point."""
        return self.grid * math.sqrt(2) / 2.0

    @property
    def band_detour(self) -> float:
        return BAND_DETOUR_FACTOR * self.cell_radius

    @property
    def uncertified_cells(self) -> int:
        return int(((~np.isfinite(self.detour)) & self.usable).sum())

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
            geodesic = (self.geodesic_to_start <= spent + self.detour) & (
                self.geodesic_to_goal <= remaining + self.detour
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
) -> Lattice:
    """Evaluate the exact geometry at every point of a lattice of this world."""
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

    targets = list(goal_positions)
    if start not in targets:
        targets.append(start)
    index = CostToGoIndex(obstacles, targets) if obstacles else None

    baseline = observer.baseline(scenario, index)
    prior = observer.prior_for(scenario)
    radius = grid * math.sqrt(2) / 2.0

    euclid_start = np.hypot(mesh_x - start[0], mesh_y - start[1])
    euclid_goal = np.hypot(mesh_x - goal[0], mesh_y - goal[1])

    if obstacles:
        cost = _geodesic_costs(
            mesh_x, mesh_y, obstacles, index, targets,
            list(dict.fromkeys([start, goal, *goal_positions])), progress,
        )
        to_start, to_goal = cost[start], cost[goal]
        usable = np.isfinite(to_start) & np.isfinite(to_goal)
        for position in goal_positions:
            usable &= np.isfinite(cost[position])
        near = _near_any_obstacle(mesh_x, mesh_y, obstacles, radius) & usable
        certified = certifies_detour(obstacles, radius)
    else:
        # The geodesic is the straight line everywhere and no cell is near an
        # obstacle, so the whole lattice is exact and nothing needs a sweep.
        cost = {
            position: np.hypot(mesh_x - position[0], mesh_y - position[1])
            for position in dict.fromkeys([start, goal, *goal_positions])
        }
        to_start, to_goal = cost[start], cost[goal]
        usable = np.ones(shape, dtype=bool)
        near = np.zeros(shape, dtype=bool)
        certified = True

    detour = np.where(near, BAND_DETOUR_FACTOR * radius, radius)
    if not certified:
        detour = np.where(near, np.inf, detour)

    # The observer's own cost-to-go, which is the geodesic for the observer
    # who can see the room and the straight line for the one who cannot. The
    # reachability terms above are always geodesic, because they are about
    # where the robot can physically be rather than about what the watcher
    # believes.
    def observed(position):
        if observer.condition == "geodesic":
            return cost[position]
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
        geodesic_to_start=to_start,
        geodesic_to_goal=to_goal,
        euclidean_to_start=euclid_start,
        euclidean_to_goal=euclid_goal,
        beta=observer.beta,
        detour_certified=certified,
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
