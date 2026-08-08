"""Fill the README's numbers from the committed results.

    python tools/build_readme.py
    python tools/build_readme.py --check

Prose lives in README.md and is edited there by hand. Numbers do not: every
table and figure between a pair of markers

    <!-- generated:name -->
    ...
    <!-- /generated:name -->

is rewritten from `results/` on each run. Anything typed inside a marked block
is lost, which is the point. The README has already gone stale once, when a
results file was regenerated and three tables in it silently kept the old
figures.

`--check` rewrites nothing and exits non-zero if the file is out of date, so
it can be run before a commit or in CI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legibility_bounds import vendored  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
README = ROOT / "README.md"


class RecordError(RuntimeError):
    """Raised when the records cannot be used to fill a README."""


def _load(name: str) -> dict:
    path = RESULTS / name
    if not path.is_file():
        raise RecordError(f"{path} does not exist; run the tool that writes it")
    record = json.loads(path.read_text(encoding="utf-8"))
    commit = record.get("geometry_commit")
    if commit != vendored.PINNED_COMMIT:
        raise RecordError(
            f"{name} was produced against geometry {commit!r} but this "
            f"repository is pinned to {vendored.PINNED_COMMIT!r}"
        )
    return record


def _table(header: list[str], rows: list[list[str]], align: str = "") -> str:
    align = align or "l" + "r" * (len(header) - 1)
    bar = {"l": ":---", "r": "---:"}
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(bar[a] for a in align) + " |",
    ]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def suite_block(suite: dict) -> str:
    rows = suite["rows"]
    worlds = sorted({r["scenario"] for r in rows})
    out = []
    for world in worlds:
        here = [r for r in rows if r["scenario"] == world]
        widest = max(here, key=lambda r: r["gap"])
        narrowest = min(here, key=lambda r: r["gap"])
        out.append([
            f"`{world}`",
            "yes" if widest["has_obstacles"] else "no",
            f"{widest['ceiling']:.2f}",
            f"{widest['achieved']:.4f}",
            f"{widest['bound']:.4f}",
            f"**{widest['gap']:.4f}**",
            f"{narrowest['gap']:.4f}",
        ])
    table = _table(
        ["world", "obstacles", "c", "achieved", "bound", "widest gap",
         "narrowest gap"],
        out,
        align="llrrrrr",
    )
    return (
        f"{table}\n\n"
        f"All {len(rows)} world and ceiling pairs, {suite['violations']} "
        f"violations. Each row is the world at the ceiling where its interval "
        f"is widest, with its narrowest gap over all "
        f"{len({r['ceiling'] for r in rows})} ceilings alongside. Lattice "
        f"{suite['grid']:g}, search budget {suite['search_budget']}."
    )


def safety_block(safety: dict) -> str:
    rows = [r for r in safety["rows"] if r["certified_price"] is not None]
    out = [
        [
            f"`{r['scenario']}`",
            f"{r['ceiling']:.2f}",
            f"{r['free_achieved']:.4f}",
            f"{r['safe_bound']:.4f}",
            f"**{r['certified_price']:.4f}**",
        ]
        for r in sorted(rows, key=lambda r: -r["certified_price"])
    ]
    table = _table(
        ["world", "c", "achievable", "safe bound", "price of safety"], out
    )
    return (
        f"{table}\n\n"
        f"{len(rows)} of {len(safety['rows'])} pairs certify a positive price. "
        f"The rest certify nothing and are reported as nothing."
    )


def example_block(suite: dict, world: str, ceiling: float) -> str:
    row = next(
        (r for r in suite["rows"]
         if r["scenario"] == world and abs(r["ceiling"] - ceiling) < 1e-9),
        None,
    )
    if row is None:
        raise RecordError(f"no suite row for {world!r} at ceiling {ceiling!r}")
    import math
    threshold = math.ceil(row["bound"] * 100.0) / 100.0
    if threshold <= row["bound"]:
        threshold += 0.01
    percent = round((ceiling - 1.0) * 100)
    return (
        f"> No trajectory from the start to the true goal in `{world}`, "
        f"spending at most {percent} per cent more path than the shortest "
        f"one, attains a legibility of **{threshold:.2f} or above** under this "
        f"observer.\n>\n"
        f"> One attaining **{row['achieved']:.4f}** exists.\n\n"
        f"The shortest path there scores {row['shortest_path_legibility']:.4f}, "
        f"so the budget does buy clarity. The two ends are "
        f"{row['gap']:.4f} apart, so any threshold outside that band is "
        f"decided: above it, unreachable; at or below the achieved value, "
        f"reached."
    )


def refinement_block(refine: dict) -> str:
    rows = refine["rows"]
    grids = sorted({r["grid"] for r in rows}, reverse=True)
    worlds = sorted({r["scenario"] for r in rows})
    out = []
    shares = []
    for world in worlds:
        cells = [f"`{world}`"]
        gaps = []
        for grid in grids:
            row = next(r for r in rows if r["scenario"] == world and r["grid"] == grid)
            gaps.append(row["gap"])
            cells.append(f"{row['gap']:.4f}")
        shares.append((gaps[0] - gaps[-1]) / gaps[0])
        out.append(cells)
    table = _table(["world"] + [f"{g:g}" for g in grids], out)
    return (
        f"{table}\n\n"
        f"Refining from {grids[0]:g} to {grids[-1]:g} closes between "
        f"{round(min(shares) * 100)} and {round(max(shares) * 100)} per cent "
        f"of the gap, so the numbers above are conservative by roughly that "
        f"margin."
    )


def slack_block(slack: dict) -> str:
    return (
        f"The argument gives `D <= (3 + pi) r`, about "
        f"{slack['claimed_in_cell_radii']:.2f} cell radii. Sampling real points "
        f"in real cells beside obstacle corners, and measuring to each point's "
        f"own lattice point, which is the quantity the bound actually uses, "
        f"finds a worst detour of "
        f"{slack['worst_measured_in_cell_radii']:.2f}, so the constant is "
        f"loose by a factor of about {slack['looseness_ratio']:.1f}. A bound "
        f"must hold in the worst case and the worst case is rarely met, so "
        f"this is not an error.\n\n"
        f"It is also not the prize it was once described as here. Halving this "
        f"constant, from `(3 + 2pi)` to `(3 + pi)`, closed 1.6 per cent of the "
        f"suite's total interval width: twenty of the thirty two pairs have no "
        f"band weight at all and cannot move however tight it becomes. "
        f"Refining the lattice, which closes 55 to 79 per cent, is worth "
        f"roughly forty times as much. An earlier version of this file called a "
        f"sharper constant the highest-leverage improvement outstanding, which "
        f"the measurement does not support.\n\n"
        f"Two further corrections went with it. The looseness used to be "
        f"reported as a factor of 3.7, measured between two arbitrary points of "
        f"a cell rather than from a point to its own centre. That is a harder "
        f"quantity than the bound claims, and using it flattered the constant. "
        f"The sampling also drew offsets from the cell radius, which is the "
        f"half diagonal, and so covered a box wider than the cell. Corrected "
        f"for both, no sampled point in any tested world is separated from its "
        f"own lattice point at all, and the wrapping argument is never needed."
    )


def witness_block(suite: dict) -> str:
    rows = suite["rows"]
    won = [
        r for r in rows
        if r["witness_achieved"] is not None
        and r["witness_achieved"] > r["search_achieved"]
    ]
    margin = max(r["witness_achieved"] - r["search_achieved"] for r in won)
    return (
        f"Against the vendored local search at {suite['search_budget']} "
        f"evaluations, the witness produces the better trajectory in "
        f"**{len(won)} of {len(rows)}** cases, by up to **{margin:.4f}**. "
        f"Where the search wins, the search's value is used and the row records "
        f"which produced it."
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    suite = _load("suite_bounds.json")
    safety = _load("safety_price.json")
    refine = _load("refinement.json")
    slack = _load("detour_slack.json")

    blocks = {
        "suite": suite_block(suite),
        "safety": safety_block(safety),
        "example": example_block(suite, "wall_choice", 1.5),
        "refinement": refinement_block(refine),
        "slack": slack_block(slack),
        "witness": witness_block(suite),
        "commit": f"Pinned geometry: `{vendored.PINNED_COMMIT[:7]}`.",
    }

    text = README.read_text(encoding="utf-8")
    missing = [
        name for name in blocks
        if f"<!-- generated:{name} -->" not in text
    ]
    if missing:
        raise RecordError(f"README has no marker for: {', '.join(missing)}")

    filled = text
    for name, body in blocks.items():
        pattern = re.compile(
            rf"(<!-- generated:{name} -->\n).*?(\n<!-- /generated:{name} -->)",
            re.DOTALL,
        )
        filled = pattern.sub(lambda m: m.group(1) + body + m.group(2), filled)

    if args.check:
        if filled != text:
            print("README is out of date; run tools/build_readme.py")
            return 1
        print("README is up to date")
        return 0

    if filled != text:
        README.write_text(filled, encoding="utf-8")
        print(f"rewrote {len(blocks)} blocks in {README}")
    else:
        print("README already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
