"""Tightening the bound by making the trajectory pass through somewhere.

The reachability bound lets every sample of the trajectory sit wherever its
own lens allows, independently of every other sample. It bounds a trajectory
that need not be a trajectory, and that is where most of its remaining
looseness lives.

This adds back one piece of what was thrown away: the trajectory passes
through a single point at a stated fraction of the way along. For an anchor
`y` at fraction `f`, every sample at fraction `s` obeys

    d(y, x) <= |s - f| L

because arc length is at least distance. The trajectory's own anchor is not
known, so the bound is the largest value over every anchor it could have had,
which is still a bound over all trajectories and is at most the unanchored one
because it only ever adds constraints.

Why it is affordable
--------------------

Evaluating one candidate anchor costs as much as the whole unanchored bound,
and there are as many candidates as lattice points. But the value at every
candidate at once, for one slice, is the maximum of that slice's field over a
disc around each point, which is a dilation. So one dilation per slice gives
every candidate together rather than one at a time.

Two relaxations keep that cheap and both are in the safe direction. A square
window contains the disc it stands for, so using a square only loosens the
bound, and a square maximum filter is separable and runs in time independent
of its width by repeated doubling. And the window is rounded up to a power of
two, which loosens it again by less than a factor of two in width.

The anchor distances are Euclidean rather than geodesic. That is sound for the
same reason it was sound in the band: a path avoiding obstacles is at least as
long as the straight line, so a Euclidean test can never exclude a point the
trajectory could have reached.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from .lattice import Lattice
from .reachability import BoundError
from .vendored import Observer, Scenario, geodesic_cost, metrics


@dataclass(frozen=True)
class AnchoredBound:
    scenario_id: str
    observer: str
    respect_keep_out: bool
    ceiling: float
    fraction: float
    grid: float
    samples: int
    bound: float
    unanchored: float
    anchor: tuple | None

    @property
    def tightening(self) -> float:
        return self.unanchored - self.bound

    def as_record(self) -> dict:
        record = asdict(self)
        record["anchor"] = None if self.anchor is None else list(self.anchor)
        record["tightening"] = self.tightening
        return record


def _along(axis: int, start, stop):
    """A slice tuple picking `start:stop` along one axis of a 2D array."""
    return (slice(start, stop), slice(None)) if axis == 0 else (
        slice(None), slice(start, stop)
    )


def _sweep_max(values: np.ndarray, half: int, axis: int) -> np.ndarray:
    """Maximum over exactly the window [i - half, i + half] along one axis.

    Exact rather than rounded. A first version rounded the window up to a
    power of two, which is sound but can nearly double it, and that is the one
    thing this module must not do carelessly: a window twice as wide weakens
    the very constraint being measured, so a loose implementation would report
    "the anchor buys nothing" whether or not it was true.

    The window is covered by two overlapping power-of-two blocks, which is the
    standard sparse-table identity and costs log(half) passes. The array is
    padded with -inf first, so that a window overhanging the world contributes
    nothing for the part that is outside it rather than running off the front
    and returning -inf for the whole window, which is what a first version did.
    """
    if half <= 0:
        return values
    width = 2 * half + 1
    level = 1
    while level * 2 <= width:
        level *= 2

    pad = [(0, 0), (0, 0)]
    pad[axis] = (half, half)
    block = np.pad(values, pad, constant_values=-np.inf)

    step = 1
    while step < level:
        ahead = np.full_like(block, -np.inf)
        length = block.shape[axis] - step
        ahead[_along(axis, 0, length)] = block[_along(axis, step, None)]
        block = np.maximum(block, ahead)
        step *= 2

    # block[i] is the maximum over padded positions [i, i + level - 1], and
    # original position j occupies padded [j, j + 2 half].
    count = values.shape[axis]
    offset = 2 * half - level + 1
    return np.maximum(
        block[_along(axis, 0, count)],
        block[_along(axis, offset, offset + count)],
    )


def _dilate(values: np.ndarray, radius: float, grid: float) -> np.ndarray:
    """Maximum over a square window standing in for a disc of that radius."""
    width = int(math.ceil(radius / grid))
    if width <= 0:
        return values
    return _sweep_max(_sweep_max(values, width, 0), width, 1)


def anchored_bound(
    scenario: Scenario,
    observer: Observer,
    ceiling: float,
    built: Lattice,
    fraction: float = 0.5,
    spacing: float = metrics.DEFAULT_SAMPLE_SPACING,
    respect_keep_out: bool = False,
) -> AnchoredBound:
    """Upper bound over trajectories, tightened by one anchor point."""
    if not 0.0 < fraction < 1.0:
        raise BoundError(
            f"an anchor sits strictly between the ends of the trajectory, "
            f"so its fraction must lie in (0, 1), found {fraction!r}"
        )
    if built.respect_keep_out != respect_keep_out:
        raise BoundError(
            "the lattice given describes the other problem; an anchored bound "
            "needs a lattice built for the same one"
        )

    optimal = geodesic_cost(
        scenario.start, scenario.true_goal_position, scenario.obstacles
    )
    length = ceiling * optimal
    steps = max(1, math.ceil(length / spacing))
    ceiling_on_belief = built.belief_bound()

    # The anchor stands for a point the trajectory really passed through, and
    # it is read off at a lattice point rather than at that point, so every
    # anchor distance is relaxed by one cell radius.
    slack = built.cell_radius
    world = math.hypot(
        scenario.bounds.xmax - scenario.bounds.xmin,
        scenario.bounds.ymax - scenario.bounds.ymin,
    )

    weight_total = 0.0
    per_anchor = np.zeros(built.belief.shape)
    # An anchor with no reachable sample at some fraction is not an anchor
    # whose value is unknown, it is an anchor no trajectory has. Scoring such
    # a candidate at one and keeping it would let impossible anchors decide a
    # bound taken as a maximum over anchors, which is what a first version did
    # and it inflated the result rather than tightening it.
    feasible = np.ones(built.belief.shape, dtype=bool)
    unanchored = 0.0
    for i in range(steps + 1):
        s = i / steps
        weight = 1.0 - s
        weight_total += weight
        reachable = built.reachable(s * length, (1.0 - s) * length)
        field = np.where(reachable, ceiling_on_belief, -np.inf)
        plain = float(field.max()) if reachable.any() else 1.0
        unanchored += min(1.0, plain) * weight

        radius = abs(s - fraction) * length + slack
        if radius >= world or not reachable.any():
            # The anchor constrains nothing at this distance, so every
            # candidate sees the same value and no dilation is needed.
            per_anchor += min(1.0, plain) * weight
            continue
        reach = _dilate(field, radius, built.grid)
        empty = ~np.isfinite(reach)
        feasible &= ~empty
        per_anchor += np.minimum(1.0, np.where(empty, 0.0, reach)) * weight

    # The anchor itself has to be somewhere the trajectory could be at that
    # fraction of the way along.
    admissible = built.reachable(
        fraction * length, (1.0 - fraction) * length
    ) & feasible
    if not admissible.any():
        raise BoundError(
            f"no lattice cell is reachable at fraction {fraction!r} in "
            f"{scenario.id!r} at ceiling {ceiling!r}, so no trajectory of that "
            f"length exists and there is nothing to bound"
        )

    scores = np.where(admissible, per_anchor, -np.inf)
    row, col = np.unravel_index(int(np.argmax(scores)), scores.shape)
    return AnchoredBound(
        scenario_id=scenario.id,
        observer=observer.name,
        respect_keep_out=respect_keep_out,
        ceiling=ceiling,
        fraction=fraction,
        grid=built.grid,
        samples=steps + 1,
        bound=float(scores[row, col]) / weight_total,
        unanchored=unanchored / weight_total,
        anchor=(float(built.x[row, col]), float(built.y[row, col])),
    )
