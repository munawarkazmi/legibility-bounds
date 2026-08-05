"""Visibility from every lattice point to one node, computed all at once.

Building a lattice means asking, for each of tens of thousands of points and
each obstacle vertex, whether the segment between them passes through an
obstacle. The vendored implementation answers that one call at a time with a
guarded exact predicate, which is correct and far too slow at this scale.

This module answers the same question for a whole array of points in one go,
in floating point, and it does not trust itself. Every decision is taken with
a tolerance, and any point whose decision falls inside that tolerance is
handed to the vendored predicate instead. So the fast path decides only the
cases where floating point has room to spare, and the exact path decides the
rest. `uncertain_fraction` reports how often that happened, because a fast
path that quietly fell back on everything would otherwise look like a
speed-up.

The convention being reproduced is the vendored one, and it matters: a
segment that grazes an edge or touches a vertex does not enter the interior
and so does not block visibility. Shortest paths turn at obstacle corners and
run flush along obstacle edges, so any stricter convention would make the
geodesic wrong.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .vendored import orientation

# How much room floating point must have before its answer is taken. The
# comparisons below are on cross products of world coordinates, so the
# tolerance is scaled by the magnitudes that went into each one rather than
# being an absolute number.
RELATIVE_TOLERANCE = 1e-9


@dataclass(frozen=True)
class Visibility:
    visible: np.ndarray
    uncertain: np.ndarray

    @property
    def uncertain_fraction(self) -> float:
        return float(self.uncertain.mean()) if self.uncertain.size else 0.0


def _edge_arrays(polygon):
    edges = list(polygon.edges())
    v = np.array([e[0] for e in edges], dtype=float)
    w = np.array([e[1] for e in edges], dtype=float)
    return v, w - v


def _enters_interior(px, py, node, polygon):
    """Vectorised form of ConvexPolygon.segment_enters_interior.

    Returns the decision and a mask of the points where floating point was
    not given enough room to be trusted with it.
    """
    v, e = _edge_arrays(polygon)
    n_edges = len(v)
    shape = px.shape

    bx, by = float(node[0]), float(node[1])
    # The node side is exact: there is one value per edge, not one per
    # lattice point, so the vendored predicate can afford to decide it.
    # Python floats, not numpy scalars: the vendored predicate branches on
    # comparisons and returns an int built from them, and numpy booleans do
    # not support the subtraction it uses to make a sign.
    side_b = np.array(
        [
            orientation(
                (float(v[i][0]), float(v[i][1])),
                (float(v[i][0] + e[i][0]), float(v[i][1] + e[i][1])),
                (bx, by),
            )
            for i in range(n_edges)
        ],
        dtype=int,
    )

    dx = bx - px
    dy = by - py

    c0 = np.empty((n_edges,) + shape)
    tolerance = np.empty((n_edges,) + shape)
    for i in range(n_edges):
        ex, ey = e[i]
        vx, vy = v[i]
        c0[i] = ex * (py - vy) - ey * (px - vx)
        tolerance[i] = RELATIVE_TOLERANCE * (abs(ex) + abs(ey)) * (
            np.abs(px - vx) + np.abs(py - vy) + abs(bx - vx) + abs(by - vy) + 1.0
        )

    # The node sits on this polygon's boundary, which is the common case:
    # most nodes of the visibility graph are obstacle corners. The parametric
    # clip is degenerate here, because the segment ends exactly on the
    # boundary at t = 1 and floating point cannot say which side of it the
    # segment arrived from. The two edges meeting at the node settle it
    # without a clip: the polygon is convex, so if the query point lies in the
    # closed outer half plane of either of them, the whole segment lies in
    # that half plane and never reaches the interior. If it lies strictly
    # inside both, the segment arrives at the corner from within the wedge
    # and the points just before it are interior.
    # `side_b == 0` alone is not enough: it says the node lies on an edge's
    # line, which it can do while sitting far outside the polygon, and in
    # narrow_gap a corner of one obstacle is collinear with an edge of the
    # other. The argument needs the node to be on the boundary itself, which
    # `contains_closed` decides with the exact predicate.
    on_boundary = polygon.contains_closed((bx, by))
    touching = [i for i in range(n_edges) if side_b[i] == 0] if on_boundary else []
    if touching:
        inside = np.ones(shape, dtype=bool)
        uncertain = np.zeros(shape, dtype=bool)
        for i in touching:
            inside &= c0[i] > tolerance[i]
            uncertain |= np.abs(c0[i]) <= tolerance[i]
        return inside, uncertain

    # Otherwise the clip decides. It is correct on its own for any input, so
    # the cheap tests below are shortcuts that add certainty rather than
    # answers the clip would not give.
    cd = np.empty((n_edges,) + shape)
    for i in range(n_edges):
        ex, ey = e[i]
        cd[i] = ex * dy - ey * dx

    rule_one = np.zeros(shape, dtype=bool)
    for i in range(n_edges):
        # Both ends in the closed outer half plane of one edge: certain, and
        # it needs only a sign that floating point had room for.
        if side_b[i] <= 0:
            rule_one |= c0[i] < -tolerance[i]

    tol_d = RELATIVE_TOLERANCE * np.maximum(np.abs(cd).max(axis=0), 1.0)
    parallel = np.abs(cd) <= tol_d

    lo = np.zeros(shape)
    hi = np.ones(shape)
    dead = np.zeros(shape, dtype=bool)
    with np.errstate(invalid="ignore", divide="ignore"):
        for i in range(n_edges):
            safe = np.where(parallel[i], 1.0, cd[i])
            t = np.where(parallel[i], 0.0, -c0[i] / safe)
            lo = np.where((~parallel[i]) & (cd[i] > 0), np.maximum(lo, t), lo)
            hi = np.where((~parallel[i]) & (cd[i] < 0), np.minimum(hi, t), hi)
            dead |= parallel[i] & (c0[i] <= 0)

    clip = (~dead) & (lo < hi)
    enters = np.where(rule_one, False, clip)
    # Only the points the clip had to decide can be in doubt about it.
    uncertain = (~rule_one) & (
        parallel.any(axis=0) | (np.abs(lo - hi) <= RELATIVE_TOLERANCE)
    )
    return enters.astype(bool), uncertain


def visible(px, py, node, obstacles, reference) -> Visibility:
    """Whether `node` is visible from each point, exactly.

    `reference` is the vendored per-call test, used wherever the vectorised
    decision was not taken with room to spare. It is passed in rather than
    imported so that the differential test can hand in the exact-only
    implementation and compare.
    """
    px = np.asarray(px, dtype=float)
    py = np.asarray(py, dtype=float)
    blocked = np.zeros(px.shape, dtype=bool)
    uncertain = np.zeros(px.shape, dtype=bool)

    for polygon in obstacles:
        enters, unsure = _enters_interior(px, py, node, polygon)
        blocked |= enters & ~unsure
        uncertain |= unsure

    if uncertain.any():
        rows, cols = np.nonzero(uncertain)
        for row, col in zip(rows, cols):
            point = (float(px[row, col]), float(py[row, col]))
            blocked[row, col] = any(
                reference(polygon, point, node) for polygon in obstacles
            )

    return Visibility(visible=~blocked, uncertain=uncertain)
