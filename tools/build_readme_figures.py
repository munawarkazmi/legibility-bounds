"""Figures for the README, drawn from the committed results.

    python tools/build_readme_figures.py

The paper's figure is a PDF for print. These are PNGs for a web page, and one
of them has no counterpart in the paper: a view of every certified interval at
once, which is the thing a visitor should understand before reading a word.

Design notes, since these are read on a screen by someone who has not decided
to care yet.

The intervals chart is a range, not a bar. A bar would encode the achieved
value as length from zero, which is not what matters; what matters is the pair
of endpoints and the distance between them. Marks are thin, the axis is a
hairline, and identity comes from shape and position rather than from colour
alone, so the figure survives being printed or read by someone who cannot
separate the hues.

A white background is deliberate. GitHub renders these on both light and dark
themes, and a transparent background puts dark ink on a dark page.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "DejaVu Sans"

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DEFAULT_OUTPUT = ROOT / "docs" / "img"

INK = "#1b1b1b"
MUTED = "#6b6b6b"
FAINT = "#d8d8d8"
ACCENT = "#1f4e79"
WARM = "#b45309"


def intervals(record: dict, output: Path) -> Path:
    """Every world's certified interval, at the ceiling where it is widest."""
    rows = record["rows"]
    worlds = sorted({r["scenario"] for r in rows})
    widest = [
        max((r for r in rows if r["scenario"] == w), key=lambda r: r["gap"])
        for w in worlds
    ]
    widest.sort(key=lambda r: r["achieved"])

    figure, axes = plt.subplots(figsize=(9.0, 4.4))
    for i, row in enumerate(widest):
        low, high = row["achieved"], row["bound"]
        axes.plot([low, high], [i, i], color=ACCENT, linewidth=6.0,
                  solid_capstyle="butt", alpha=0.22, zorder=2)
        axes.plot([low, high], [i, i], color=ACCENT, linewidth=1.2, zorder=3)
        axes.plot(row["shortest_path_legibility"], i, marker="|", markersize=11,
                  markeredgewidth=1.4, color=MUTED, zorder=4)
        axes.plot(low, i, marker="o", markersize=7, color=ACCENT,
                  markeredgecolor="white", markeredgewidth=1.2, zorder=5)
        axes.plot(high, i, marker="D", markersize=6.5, color=WARM,
                  markeredgecolor="white", markeredgewidth=1.2, zorder=5)
        axes.annotate(
            f"{row['gap']:.4f}", (high, i), textcoords="offset points",
            xytext=(12, -3), fontsize=8.5, color=MUTED,
        )

    axes.set_yticks(range(len(widest)))
    axes.set_yticklabels(
        [f"{r['scenario']}   c={r['ceiling']:.2f}" for r in widest],
        fontsize=9.5,
    )
    axes.tick_params(axis="y", length=0)
    axes.tick_params(axis="x", labelsize=9, width=0.6, length=3, color=MUTED)
    axes.set_xlabel("legibility", fontsize=10, color=INK)
    axes.set_xlim(0.35, 1.0)
    axes.grid(axis="x", color=FAINT, linewidth=0.6)
    axes.set_axisbelow(True)
    for side in ("top", "right", "left"):
        axes.spines[side].set_visible(False)
    axes.spines["bottom"].set_color(MUTED)
    axes.spines["bottom"].set_linewidth(0.6)

    handles = [
        plt.Line2D([], [], marker="|", color=MUTED, linestyle="none",
                   markersize=11, markeredgewidth=1.4,
                   label="shortest path"),
        plt.Line2D([], [], marker="o", color=ACCENT, linestyle="none",
                   markersize=7, label="achieved (a trajectory exists)"),
        plt.Line2D([], [], marker="D", color=WARM, linestyle="none",
                   markersize=6.5, label="bound (nothing exceeds this)"),
    ]
    axes.legend(handles=handles, loc="lower right", fontsize=9, frameon=False,
                handletextpad=0.4)
    axes.set_title(
        "The optimum lies inside every band. No bound is violated.",
        fontsize=11, color=INK, loc="left", pad=12,
    )

    path = output / "intervals.png"
    figure.savefig(path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return path


def refinement(record: dict, output: Path) -> Path:
    """Gap against lattice spacing: where the residual width lives."""
    rows = record["rows"]
    worlds = sorted({r["scenario"] for r in rows})
    grids = sorted({r["grid"] for r in rows}, reverse=True)

    figure, axes = plt.subplots(figsize=(6.6, 3.8))
    styles = [("o", "solid"), ("s", (0, (5, 2))), ("^", (0, (1, 1.6)))]
    for (marker, dashes), world in zip(styles, worlds):
        gaps = [
            next(r for r in rows if r["scenario"] == world and r["grid"] == g)["gap"]
            for g in grids
        ]
        axes.plot(range(len(grids)), gaps, marker=marker, linestyle=dashes,
                  color=ACCENT, linewidth=1.4, markersize=6,
                  markeredgecolor="white", markeredgewidth=1.0, label=world)

    axes.set_xticks(range(len(grids)))
    axes.set_xticklabels([f"{g:g}" for g in grids], fontsize=9)
    axes.set_xlabel("lattice spacing (world units)", fontsize=10, color=INK)
    axes.set_ylabel("gap", fontsize=10, color=INK)
    axes.set_ylim(bottom=0)
    axes.tick_params(labelsize=9, width=0.6, length=3, color=MUTED)
    axes.grid(axis="y", color=FAINT, linewidth=0.6)
    axes.set_axisbelow(True)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("bottom", "left"):
        axes.spines[side].set_color(MUTED)
        axes.spines[side].set_linewidth(0.6)
    axes.legend(fontsize=9, frameon=False)
    axes.set_title(
        "Refining the lattice closes most of the gap.",
        fontsize=11, color=INK, loc="left", pad=10,
    )

    path = output / "refinement.png"
    figure.savefig(path, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    suite = json.loads((RESULTS / "suite_bounds.json").read_text(encoding="utf-8"))
    refine = json.loads((RESULTS / "refinement.json").read_text(encoding="utf-8"))

    for path in (intervals(suite, output), refinement(refine, output)):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
