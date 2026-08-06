"""Draw the paper's figure from the committed geometry.

    python tools/build_paper_figures.py

Nothing here is illustrative. The belief field, the reachable sets and the
witness are the same objects the bound is computed from, drawn rather than
redrawn, so the figure and the tables cannot disagree.

Design notes, since a figure in a paper has constraints a screen figure does
not.

The belief is a magnitude, so it takes a single hue running light to dark and
carries a scale legend. A multi-hue ramp would encode magnitude in a channel
that does not order.

Identity never rests on colour. IEEE is read in print and in greyscale as
often as on a screen, so the three overlaid curves are separated by line style
and weight first, and would remain distinguishable with every colour removed.

Fonts are embedded as TrueType, not Type 3. Matplotlib writes Type 3 into a
PDF unless told otherwise and publishers commonly refuse it; `make check` in
paper/ fails on a Type 3 font for that reason.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legibility_bounds import lattice as lattice_module  # noqa: E402
from legibility_bounds import vendored  # noqa: E402
from legibility_bounds import witness as witness_module  # noqa: E402
from legibility_bounds.reachability import reachability_bound  # noqa: E402

from legible_motion_bench.planners.shortest import ShortestPathPlanner  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "paper" / "generated" / "mechanism.pdf"

# One column of IEEE's two-column layout, in inches.
COLUMN_WIDTH = 3.5


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="wall_choice")
    parser.add_argument("--ceiling", type=float, default=1.5)
    parser.add_argument("--grid", type=float, default=0.02)
    parser.add_argument("--observer", default="geodesic")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    scenario = vendored.scenario(args.scenario)
    observer = vendored.Observer(condition=args.observer)
    built = lattice_module.build(scenario, observer, args.grid)
    result = reachability_bound(
        scenario, observer, args.ceiling, grid=args.grid, built=built
    )
    found = witness_module.best_witness(scenario, observer, args.ceiling, built)
    if found is None:
        raise SystemExit(
            f"no witness could be built for {scenario.id} at ceiling "
            f"{args.ceiling}, so there is nothing to draw"
        )
    shortest = ShortestPathPlanner().plan(scenario)

    bounds = scenario.bounds
    span_x = bounds.xmax - bounds.xmin
    span_y = bounds.ymax - bounds.ymin
    figure, axes = plt.subplots(
        figsize=(COLUMN_WIDTH, COLUMN_WIDTH * span_y / span_x + 0.45)
    )

    # The belief field: one hue, light to dark, with a scale legend below.
    field = np.where(built.usable, built.belief, np.nan)
    shown = axes.imshow(
        field,
        origin="lower",
        extent=(bounds.xmin, bounds.xmax, bounds.ymin, bounds.ymax),
        cmap="Blues",
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
    )

    # Obstacles, in a flat neutral that cannot be mistaken for a value on the
    # ramp.
    for obstacle in scenario.obstacles:
        axes.add_patch(
            plt.Polygon(
                obstacle.vertices, closed=True,
                facecolor="0.45", edgecolor="0.25", linewidth=0.6, zorder=3,
            )
        )

    # One reachable set, at the half way point. Three of them were drawn at
    # first and read as overlapping circles: the shape of a single lens is the
    # thing worth seeing, and three of them hid it.
    optimal = vendored.geodesic_cost(
        scenario.start, scenario.true_goal_position, scenario.obstacles
    )
    length = args.ceiling * optimal
    reachable = built.reachable(0.5 * length, 0.5 * length)
    axes.contour(
        built.x, built.y, reachable.astype(float), levels=[0.5],
        # A list, because a contour set takes one style per level and a bare
        # dash tuple is read as a sequence of styles.
        colors="0.1", linewidths=1.1, linestyles=[(0, (5, 2))], zorder=4,
    )
    # Named in the legend through a proxy, since a contour set does not
    # produce a legend handle of its own.
    axes.plot(
        [], [], color="0.1", linewidth=1.1, linestyle=(0, (5, 2)),
        label="reachable at half way",
    )

    shortest_points = np.array(shortest.points)
    axes.plot(
        shortest_points[:, 0], shortest_points[:, 1],
        color="0.15", linewidth=1.0, linestyle=(0, (1, 1.6)), zorder=5,
        label="shortest path",
    )
    witness_points = np.array(found.points)
    axes.plot(
        witness_points[:, 0], witness_points[:, 1],
        color="black", linewidth=1.8, linestyle="solid", zorder=6,
        label="witness",
    )

    # The witness at its own half way point, which is what ties the outlined
    # region to the curve. Without it the trajectory reads as escaping the
    # region, when in fact the region constrains only where it may be at that
    # one moment.
    #
    # It is also a check. The witness is an admissible trajectory, so this
    # point has to lie inside the set drawn, and if it ever does not then the
    # figure has caught something the tables would not have.
    middle = witness_module._point_at(found.points, 0.5)
    row = int(np.argmin(np.abs(built.y[:, 0] - middle[1])))
    column = int(np.argmin(np.abs(built.x[0, :] - middle[0])))
    if not reachable[row, column]:
        raise SystemExit(
            f"the witness in {scenario.id} at ceiling {args.ceiling} is at "
            f"{middle} half way along, which is outside the set reachable at "
            f"half way. One of the bound and the witness is wrong."
        )
    axes.plot(
        *middle, marker="o", color="white", markersize=5.5,
        markeredgecolor="black", markeredgewidth=1.2, zorder=7,
    )
    axes.annotate(
        "half way", middle, textcoords="offset points", xytext=(8, 7),
        fontsize=7,
    )

    # Start and goals are named where they sit rather than in the legend,
    # which keeps the legend to the two things that need comparing.
    axes.plot(*scenario.start, marker="o", color="black", markersize=4.5,
              markeredgecolor="white", markeredgewidth=0.8, zorder=7)
    axes.annotate("S", scenario.start, textcoords="offset points",
                  xytext=(5, 4), fontsize=8)
    for goal in scenario.goals:
        marker = "*" if goal.id == scenario.true_goal else "s"
        size = 9 if goal.id == scenario.true_goal else 4.5
        axes.plot(*goal.position, marker=marker, color="black",
                  markersize=size, markeredgecolor="white",
                  markeredgewidth=0.8, zorder=7)
        axes.annotate(goal.id, goal.position, textcoords="offset points",
                      xytext=(5, 4), fontsize=8)

    axes.set_xlim(bounds.xmin, bounds.xmax)
    axes.set_ylim(bounds.ymin, bounds.ymax)
    axes.set_aspect("equal")
    axes.set_xticks([])
    axes.set_yticks([])
    for side in axes.spines.values():
        side.set_linewidth(0.5)
        side.set_color("0.6")

    # Below the plot rather than inside it. Every corner of this world is
    # either field worth reading or trajectory, and a box in the lower left
    # sat directly on the witness.
    legend = axes.legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.02), ncols=3, fontsize=7,
        frameon=False, borderpad=0.2, handlelength=2.4, columnspacing=1.2,
        handletextpad=0.5,
    )
    bar = figure.colorbar(
        shown, ax=axes, orientation="horizontal", fraction=0.045, pad=0.14
    )
    bar.set_label("belief in the true goal", fontsize=7)
    bar.ax.tick_params(labelsize=7, width=0.5, length=2)
    bar.outline.set_linewidth(0.4)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight", pad_inches=0.02)
    plt.close(figure)

    print(f"wrote {output}")
    print(
        f"{scenario.id} at ceiling {args.ceiling}: witness "
        f"{found.legibility:.4f} at cost ratio {found.cost_ratio:.4f}, "
        f"bound {result.bound:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
