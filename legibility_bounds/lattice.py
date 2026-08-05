"""A lattice over a world, carrying exact geodesic quantities at each point.

The bound needs three things at every point of the plane: the belief the
observer would hold there, the optimal cost to get there from the start, and
the optimal cost to reach the goal from it. All three are exact and come from
the vendored visibility-graph implementation. What a lattice adds is a finite
set of places to evaluate them, and the job of this module is to make a
lattice maximum into a real maximum rather than a sample of one.

Cells near an obstacle
----------------------

Away from obstacles this is routine: within a cell that no obstacle comes
near, the geodesic between two points is the straight segment between them,
so every quantity varies by at most half the cell diagonal and the Lipschitz
slack covers it.

Near an obstacle it is not routine, and the difference is the thing that has
to be got right rather than glossed. Two points a millimetre apart on
opposite sides of a wall are a wall's length apart geodesically, so no small
bound on the variation of cost-to-go is available inside such a cell.

The way out does not need a bound on that variation. Euclidean distance is a
lower bound on geodesic distance, always and everywhere, because a path that
avoids obstacles is at least as long as the straight line. So a cell can
still be ruled out of a reachable set whenever its Euclidean distance already
exceeds the budget, which is sound whatever the geodesic does inside it. What
such a cell cannot supply is a useful bound on the belief, so it is given the
only bound that always holds, namely one.

Cells like that form a band of width one cell around each obstacle, so there
are O(1/h) of them against O(1/h^2) elsewhere. Whether they dominate the
result is a question about a particular world rather than something to
assume, so `Lattice` reports how much of a bound came from them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .vendored import CostToGoIndex, Observer, Scenario, straight_line_cost


class LatticeError(ValueError):
    """Raised when a lattice cannot be built for the inputs given."""


@dataclass(frozen=True)
class Lattice:
    """Exact geodesic quantities at every usable point of a square lattice.

    Every array below has the shape of the lattice. `usable` is false where a
    point lies inside an obstacle, which no trajectory may do, and the other
    arrays carry no meaning there.

    `near_obstacle` marks the cells whose interior the straight-line argument
    does not cover. `belief` is exact at the point itself in every usable
    cell; it is the bound over the cell that differs, and `belief_bound`
    applies that difference.
    """

    scenario_id: str
    observer: str
    grid: float
    x: np.ndarray
    y: np.ndarray
    usable: np.ndarray
    near_obstacle: np.ndarray
    belief: np.ndarray
    geodesic_to_start: np.ndarray
    geodesic_to_goal: np.ndarray
    euclidean_to_start: np.ndarray
    euclidean_to_goal: np.ndarray
    lipschitz: float

    @property
    def cell_radius(self) -> float:
        """Half the diagonal: the furthest a point can be from its lattice point."""
        return self.grid * math.sqrt(2) / 2.0

    @property
    def slack(self) -> float:
        return self.lipschitz * self.cell_radius

    def belief_bound(self) -> np.ndarray:
        """An upper bound on the belief anywhere in each cell.

        Away from obstacles this is the value at the lattice point plus the
        Lipschitz slack. In the band it is one, which is the only bound that
        holds without knowing how the geodesic behaves inside the cell.
        """
        bound = np.where(self.near_obstacle, 1.0, self.belief + self.slack)
        return np.clip(bound, 0.0, 1.0)

    def reachable(self, spent: float, remaining: float) -> np.ndarray:
        """Cells that may hold a path point with `spent` arc behind it.

        A point on a trajectory that has travelled `spent` and must still
        reach the goal within `remaining` satisfies both geodesic conditions,
        since arc length is at least geodesic distance. Away from obstacles
        the test is made on the exact geodesic, dilated by a whole cell so
        that no admissible point loses its lattice point. In the band the
        same test is made on Euclidean distance, which is a lower bound on
        the geodesic and therefore cannot exclude a cell that should be in.
        """
        exact = (
            (self.geodesic_to_start <= spent + self.grid)
            & (self.geodesic_to_goal <= remaining + self.grid)
        )
        loose = (
            (self.euclidean_to_start <= spent + self.grid)
            & (self.euclidean_to_goal <= remaining + self.grid)
        )
        return self.usable & np.where(self.near_obstacle, loose, exact)


def lipschitz_constant(observer: Observer) -> float:
    """A bound on the gradient of the belief, in the observer's own metric.

    The belief is a softmax whose terms are cost-to-go multiplied by beta, and
    cost-to-go has unit gradient, so

        |grad b| <= beta * [ b (1 - b) + b * sum of the other beliefs ]
                  = 2 beta b (1 - b)
                  <= beta / 2

    for any number of goals. Nothing here assumes there are two.
    """
    return observer.beta / 2.0


def build(
    scenario: Scenario,
    observer: Observer,
    grid: float,
    progress=None,
) -> Lattice:
    """Evaluate the exact geometry at every point of a lattice of this world.

    This is the expensive step. A cost-to-go query is one visibility test per
    obstacle vertex, so the work is the lattice size times the vertex count,
    and it is done once per world, observer and lattice.
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

    # One index covers every cost-to-go this module needs: to each goal for
    # the belief, and to the start for the reachability condition. Geodesic
    # distance is symmetric, so the cost from a point to the start is the
    # cost from the start to that point.
    targets = [g.position for g in scenario.goals]
    if start not in targets:
        targets.append(start)
    index = CostToGoIndex(obstacles, targets) if obstacles else None

    baseline = observer.baseline(scenario, index)
    prior = observer.prior_for(scenario)
    radius = grid * math.sqrt(2) / 2.0

    usable = np.ones(shape, dtype=bool)
    near = np.zeros(shape, dtype=bool)
    belief = np.zeros(shape)
    to_start = np.full(shape, np.inf)
    to_goal = np.full(shape, np.inf)

    euclid_start = np.hypot(mesh_x - start[0], mesh_y - start[1])
    euclid_goal = np.hypot(mesh_x - goal[0], mesh_y - goal[1])

    if not obstacles:
        # The geodesic is the straight line everywhere and no cell is near an
        # obstacle, so the whole lattice is exact and nothing needs a loop.
        to_start = euclid_start
        to_goal = euclid_goal
        exponents = {
            g.id: observer.beta
            * (
                baseline[g.id]
                - np.hypot(mesh_x - g.position[0], mesh_y - g.position[1])
            )
            for g in scenario.goals
        }
        shift = np.maximum.reduce(list(exponents.values()))
        weights = {
            gid: prior[gid] * np.exp(value - shift)
            for gid, value in exponents.items()
        }
        belief = weights[scenario.true_goal] / sum(weights.values())
        return Lattice(
            scenario_id=scenario.id,
            observer=observer.name,
            grid=grid,
            x=mesh_x,
            y=mesh_y,
            usable=usable,
            near_obstacle=near,
            belief=belief,
            geodesic_to_start=to_start,
            geodesic_to_goal=to_goal,
            euclidean_to_start=euclid_start,
            euclidean_to_goal=euclid_goal,
            lipschitz=lipschitz_constant(observer),
        )

    total = shape[0] * shape[1]
    done = 0
    for row in range(shape[0]):
        for col in range(shape[1]):
            point = (float(mesh_x[row, col]), float(mesh_y[row, col]))
            done += 1
            if progress is not None and done % 20000 == 0:
                progress(done, total)

            if any(ob.contains_interior(point) for ob in obstacles):
                usable[row, col] = False
                continue
            if any(ob.distance_to_point(point) <= radius for ob in obstacles):
                near[row, col] = True

            to_start[row, col] = index.cost_to(point, start)
            to_goal[row, col] = index.cost_to(point, goal)

            # The observer's own cost-to-go, which is the geodesic for the
            # observer who can see the room and the straight line for the one
            # who cannot. The reachability terms above are always geodesic,
            # because they are about where the robot can physically be rather
            # than about what the watcher believes.
            exponents = {
                g.id: observer.beta
                * (
                    baseline[g.id]
                    - (
                        index.cost_to(point, g.position)
                        if observer.condition == "geodesic"
                        else straight_line_cost(point, g.position)
                    )
                )
                for g in scenario.goals
            }
            shift = max(exponents.values())
            weights = {
                gid: prior[gid] * math.exp(value - shift)
                for gid, value in exponents.items()
            }
            belief[row, col] = weights[scenario.true_goal] / sum(weights.values())

    return Lattice(
        scenario_id=scenario.id,
        observer=observer.name,
        grid=grid,
        x=mesh_x,
        y=mesh_y,
        usable=usable,
        near_obstacle=near,
        belief=belief,
        geodesic_to_start=to_start,
        geodesic_to_goal=to_goal,
        euclidean_to_start=euclid_start,
        euclidean_to_goal=euclid_goal,
        lipschitz=lipschitz_constant(observer),
    )
