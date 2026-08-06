"""Write the paper's tables and quoted numbers from the committed results.

    python tools/build_paper_tables.py

Nothing under `paper/generated/` is edited by hand and nothing in the paper is
typed from a terminal. Tables come from here, and so do the individual numbers
that appear in prose, as macros: a sentence saying the worst gap in the suite
is some value writes `\\suiteWorstGap` and cannot drift from the record it
came from.

The tool refuses to write anything if the records were produced against a
different geometry from the one this repository is pinned to. A paper built
from a table that describes another version of the world would be wrong in a
way no proofreading would catch.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legibility_bounds import vendored  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DEFAULT_OUTPUT = ROOT / "paper" / "generated"

BANNER = (
    "% Written by tools/build_paper_tables.py from the committed results.\n"
    "% Do not edit. Any change here is lost on the next build, and a number\n"
    "% typed by hand is a number that can disagree with the code.\n"
)


class RecordError(RuntimeError):
    """Raised when the records cannot be used to build a paper."""


def _load(name: str) -> dict:
    path = RESULTS / name
    if not path.is_file():
        raise RecordError(
            f"{path} does not exist. Run the tool that writes it before "
            f"building the paper."
        )
    record = json.loads(path.read_text(encoding="utf-8"))
    commit = record.get("geometry_commit")
    if commit != vendored.PINNED_COMMIT:
        raise RecordError(
            f"{name} was produced against geometry {commit!r} but this "
            f"repository is pinned to {vendored.PINNED_COMMIT!r}. Regenerate "
            f"the results rather than building a paper from a table that "
            f"describes a different world."
        )
    return record


def _world(name: str) -> str:
    """A world's name as it should appear in LaTeX."""
    return r"\texttt{" + name.replace("_", r"\_") + "}"


def _number(value, places: int = 4) -> str:
    return "--" if value is None else f"{value:.{places}f}"


def suite_table(record: dict) -> str:
    rows = record["rows"]
    ceilings = sorted({r["ceiling"] for r in rows})
    worlds = sorted({r["scenario"] for r in rows})
    indexed = {(r["scenario"], r["ceiling"]): r for r in rows}

    columns = "l" + "rr" * len(ceilings)
    lines = [
        BANNER,
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Achievable legibility and the bound on it, over the "
        r"scenario suite at four cost ceilings. \emph{ach} is the better of a "
        r"local search and a witness built from the bound; \emph{bnd} is the "
        r"upper bound no trajectory within the budget can exceed. Every "
        r"interval is two-sided and no bound is violated.}",
        r"\label{tab:suite}",
        rf"\begin{{tabular}}{{{columns}}}",
        r"\toprule",
    ]
    header = ["world"]
    for ceiling in ceilings:
        header.append(rf"\multicolumn{{2}}{{c}}{{$c = {ceiling:.2f}$}}")
    lines.append(" & ".join(header) + r" \\")
    spans = " ".join(
        rf"\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}" for i in range(len(ceilings))
    )
    lines.append(spans)
    lines.append(
        " & ".join([""] + ["ach & bnd"] * len(ceilings)) + r" \\"
    )
    lines.append(r"\midrule")

    for world in worlds:
        cells = [_world(world)]
        for ceiling in ceilings:
            row = indexed[(world, ceiling)]
            cells.append(_number(row["achieved"]))
            cells.append(_number(row["bound"]))
        lines.append(" & ".join(cells) + r" \\")

    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def safety_table(record: dict) -> str:
    rows = record["rows"]
    lines = [
        BANNER,
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{What respecting a keep-out zone certifiably costs. "
        r"\emph{free} is a trajectory that exists within the budget and may "
        r"cross a zone; \emph{safe bnd} is a bound no trajectory that avoids "
        r"one can exceed. Where the first is larger, the difference is a "
        r"certified lower bound on the price of the constraint.}",
        r"\label{tab:safety}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"world & $c$ & free & safe bnd & price \\",
        r"\midrule",
    ]
    for row in rows:
        price = row["certified_price"]
        lines.append(
            " & ".join([
                _world(row["scenario"]),
                f"{row['ceiling']:.2f}",
                _number(row["free_achieved"]),
                _number(row["safe_bound"]),
                r"\textemdash" if price is None else _number(price),
            ]) + r" \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def facts(suite: dict, safety: dict) -> str:
    """Macros for the numbers that appear in prose rather than in a table."""
    rows = suite["rows"]
    worst = max(rows, key=lambda r: r["gap"])
    best = min(rows, key=lambda r: r["gap"])
    won = [
        r for r in rows
        if r["witness_achieved"] is not None
        and r["witness_achieved"] > r["search_achieved"]
    ]
    priced = [r for r in safety["rows"] if r["certified_price"] is not None]

    values = {
        "geometryCommit": vendored.PINNED_COMMIT[:7],
        "suiteWorlds": str(len({r["scenario"] for r in rows})),
        "suiteCeilings": str(len({r["ceiling"] for r in rows})),
        "suitePairs": str(len(rows)),
        "suiteViolations": str(suite["violations"]),
        "suiteLattice": f"{suite['grid']:g}",
        "searchBudget": str(suite["search_budget"]),
        "suiteWorstGap": _number(worst["gap"]),
        "suiteWorstGapWorld": _world(worst["scenario"]),
        "suiteWorstGapCeiling": f"{worst['ceiling']:.2f}",
        "suiteBestGap": _number(best["gap"]),
        "witnessWins": str(len(won)),
        "witnessBestMargin": _number(
            max((r["witness_achieved"] - r["search_achieved"] for r in won),
                default=0.0)
        ),
        "safetyPairs": str(len(safety["rows"])),
        "safetyPriced": str(len(priced)),
        "safetyLattice": f"{safety['grid']:g}",
    }
    if priced:
        largest = max(priced, key=lambda r: r["certified_price"])
        values["safetyLargestPrice"] = _number(largest["certified_price"])
        values["safetyLargestWorld"] = _world(largest["scenario"])
        values["safetyLargestCeiling"] = f"{largest['ceiling']:.2f}"

    lines = [BANNER]
    for name, value in values.items():
        lines.append(rf"\newcommand{{\{name}}}{{{value}}}")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    suite = _load("suite_bounds.json")
    safety = _load("safety_price.json")

    if suite["violations"]:
        raise RecordError(
            f"suite_bounds.json records {suite['violations']} bound "
            f"violations. A bound below an achieved value is wrong, and no "
            f"paper is built from it."
        )

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    written = {
        "suite.tex": suite_table(suite),
        "safety.tex": safety_table(safety),
        "facts.tex": facts(suite, safety),
    }
    for name, text in written.items():
        (output / name).write_text(text, encoding="utf-8")
        print(f"wrote {output / name}")

    print(
        f"\nsuite: {len(suite['rows'])} pairs at lattice {suite['grid']:g}, "
        f"{suite['violations']} violations"
    )
    print(
        f"safety: {len(safety['rows'])} pairs, "
        f"{sum(1 for r in safety['rows'] if r['certified_price'] is not None)} "
        f"certifying a price"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
