"""Every number in the plain-language guide, written from the records.

    python tools/build_explainer.py           rewrite the generated blocks
    python tools/build_explainer.py --check    fail if any block is out of date

The guide is the one document here whose figures used to be typed by hand, and
it went stale exactly as you would expect. It was still quoting a narrowest gap
of 0.0065 after the results had moved to 0.0064, and because the site's drift
checker asks whether a number is still findable in this repository rather than
whether it is still correct, that stale sentence kept a stale claim on the site
green. The check only went red once this file was fixed. So the fix is not a
test that watches the typing, it is to stop typing.

This is `build_readme.py` for LaTeX. The markers are comments,

    % generated:name
    ...
    % /generated:name

and everything between them is replaced. Prose outside a marker is written by
hand and is never touched, which is most of the document: only the sentences
that quote a figure are generated, and they are the same sentences as before,
with the figures interpolated rather than typed.

Numbers are formatted for a reader rather than for a referee. The guide says
"about 6.14" where the paper says the macro, and it spells small counts as
words, because that is its register. Nothing is rounded in a direction that
flatters a result.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from legibility_bounds import vendored  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
EXPLAINER = ROOT / "docs" / "explainer" / "explainer.tex"

WORDS = {
    1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six",
    7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven",
    12: "Twelve", 20: "Twenty", 30: "Thirty", 32: "Thirty-two",
    40: "Forty", 50: "Fifty", 60: "Sixty", 70: "Seventy", 80: "Eighty",
    90: "Ninety", 100: "A hundred",
}


class RecordError(RuntimeError):
    """Raised when the records cannot be used to fill the guide."""


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


def _word(n: int, capital: bool = True) -> str:
    w = WORDS.get(n, str(n))
    return w if capital else w.lower()


def _room(name: str) -> str:
    return "\\code{" + name.replace("_", "\\_") + "}"


def example_block(suite: dict, world: str, ceiling: float) -> str:
    row = next(
        (r for r in suite["rows"]
         if r["scenario"] == world and abs(r["ceiling"] - ceiling) < 1e-9),
        None,
    )
    if row is None:
        raise RecordError(f"no suite row for {world!r} at ceiling {ceiling!r}")
    threshold = math.ceil(row["bound"] * 100.0) / 100.0
    if threshold <= row["bound"]:
        threshold += 0.01
    percent = round((ceiling - 1.0) * 100)
    return (
        "\\begin{quotebox}\n"
        "\\textit{No trajectory from the start to the true goal in the} "
        f"{_room(world)} \\textit{{room, spending at most {percent} per cent "
        "more distance than the shortest route, attains a legibility of "
        f"\\textbf{{{threshold:.2f} or above}} under this observer.}}"
        "\\\\[4pt]\n"
        f"\\textit{{One attaining \\textbf{{{row['achieved']:.4f}}} exists.}}\n"
        "\\end{quotebox}\n"
        "\n"
        "The shortest route in that room scores "
        f"{row['shortest_path_legibility']:.4f}, so the extra distance "
        f"genuinely buys clarity. And the two ends sit {row['gap']:.4f} apart, "
        "which means any target outside that narrow band is now settled: above "
        "it, provably unreachable; at or below the achieved value, definitely "
        "reached."
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
        "This turns out to work better than searching, too. Against the "
        "reference local search, the constructed trajectory is the better of "
        f"the two in \\textbf{{{len(won)} of {len(rows)}}} cases, by as much as "
        f"{margin:.4f}. Where the search wins, the search's number is used and "
        "the record says which produced it."
    )


def range_block(suite: dict) -> str:
    rows = suite["rows"]
    worlds = len({r["scenario"] for r in rows})
    ceilings = len({r["ceiling"] for r in rows})
    narrowest = min(r["gap"] for r in rows)
    widest = max(r["gap"] for r in rows)
    violations = suite["violations"]
    held = (
        "\\textbf{Every one holds, with no violations.}" if violations == 0
        else f"\\textbf{{{violations} of them are violated.}}"
    )
    return (
        f"{_word(worlds)} rooms, {_word(ceilings, capital=False)} distance "
        f"budgets each, so {len(rows)} combinations in total. {held} The "
        f"intervals range from {narrowest:.4f} apart at the tightest to "
        f"{widest:.4f} at the widest."
    )


def safety_block(safety: dict) -> str:
    priced = [r for r in safety["rows"] if r["certified_price"] is not None]
    lines = [
        "\\begin{center}",
        "\\small",
        "\\begin{tabular}{lrrrr}",
        "\\toprule",
        "room & budget & achievable & safe ceiling & certified price \\\\",
        "\\midrule",
    ]
    for r in sorted(priced, key=lambda r: -r["certified_price"]):
        lines.append(
            f"{_room(r['scenario'])} & {r['ceiling']:.2f} & "
            f"{r['free_achieved']:.4f} & {r['safe_bound']:.4f} & "
            f"\\textbf{{{r['certified_price']:.4f}}} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{center}", ""]
    total = len(safety["rows"])
    silent = total - len(priced)
    lines.append(
        f"{_word(len(priced))} of the {_word(total, capital=False)} cases "
        f"certify a positive price. The other {_word(silent, capital=False)} "
        "certify nothing, and are reported as nothing rather than as zero."
    )
    return "\n".join(lines)


def refinement_block(refine: dict) -> str:
    rows = refine["rows"]
    grids = sorted({r["grid"] for r in rows}, reverse=True)
    shares = []
    for world in sorted({r["scenario"] for r in rows}):
        gaps = [
            next(r for r in rows if r["scenario"] == world and r["grid"] == g)["gap"]
            for g in grids
        ]
        shares.append((gaps[0] - gaps[-1]) / gaps[0])
    return (
        "Most of the remaining width comes from the resolution of the grid the "
        "room is divided into. Refining that grid closes between "
        f"{round(min(shares) * 100)} and {round(max(shares) * 100)} per cent of "
        "the gap, which means the published numbers are conservative by roughly "
        "that margin."
    )


def slack_block(slack: dict, superseded: float, closed_percent: float,
                refine: dict) -> str:
    shares = []
    rows = refine["rows"]
    grids = sorted({r["grid"] for r in rows}, reverse=True)
    for world in sorted({r["scenario"] for r in rows}):
        gaps = [
            next(r for r in rows if r["scenario"] == world and r["grid"] == g)["gap"]
            for g in grids
        ]
        shares.append((gaps[0] - gaps[-1]) / gaps[0])
    least, most = round(min(shares) * 100), round(max(shares) * 100)
    claimed = slack["claimed_in_cell_radii"]
    worst = slack["worst_measured_in_cell_radii"]
    ratio = slack["looseness_ratio"]
    times = round(((least + most) / 2.0) / closed_percent / 10.0) * 10
    return (
        "What survives even that is a single constant in the obstacle argument. "
        f"The proof guarantees a detour of no more than about {claimed:.2f} "
        "cell-widths near a corner; measuring actual points beside actual "
        "corners, each to its own grid point, finds the worst real detour is "
        f"{worst:.2f}. So the constant is loose by a factor of about "
        f"{ratio:.1f}.\n"
        "\n"
        "\\begin{quotebox}\n"
        "That is not an error, because a proof must hold in the worst case and "
        "the worst case is rarely met. What it is not is the prize this section "
        "used to call it.\n"
        "\\end{quotebox}\n"
        "\n"
        "An earlier version of this page said something stronger and less true, "
        "so it is worth setting out what changed. The constant used to be about "
        f"{superseded:.2f}, and a sharper argument brought it to {claimed:.2f}. "
        "That was expected to matter and it did not. It closed "
        f"{closed_percent:.1f} per cent of the total width, because most of the "
        "rooms draw nothing from the obstacle argument at all and cannot move "
        f"however tight it becomes. Refining the grid, at {least} to {most} per "
        f"cent, is worth some {_word(times, capital=False)} times as much.\n"
        "\n"
        "The looseness was also being measured in a way that flattered the "
        "constant. It compared two arbitrary points of a cell, which is a harder "
        "distance than the proof ever claims, and it drew those points from a "
        "box wider than the cell itself. Measured correctly, no sampled point in "
        "any room tested is cut off from its own grid point at all, and the "
        "detour argument never actually binds."
    )


def recoverable_block(slack: dict, lower: dict) -> str:
    if not lower["cell_certifies_the_precondition"]:
        raise RecordError(
            "detour_lower_bound.json records a configuration whose cell does "
            "not certify the precondition. It bounds nothing, and no guide is "
            "built from it."
        )
    ratio = slack["looseness_ratio"]
    claimed = slack["claimed_in_cell_radii"]
    bound = lower["geodesic_in_cell_radii"]
    recoverable = lower["recoverable_ratio"]
    return (
        f"The figure of {ratio:.1f} answers a narrower question than it appears "
        "to. It says how much slack there is in \\emph{these} rooms. It says "
        "nothing about how much of that slack a better proof could ever take "
        "back, and those are different questions with different answers.\n"
        "\n"
        "Answering the second one means putting the measuring tape away and "
        "building a room on purpose. Place a single obstacle beside a grid "
        "point, arranged as awkwardly as the rules still allow, and ask how far "
        "a nearby point genuinely is from that grid point once you are forced "
        f"to walk around the obstacle rather than through it. The answer is "
        f"{bound:.2f} cell-widths. That room is legal, so no proof is allowed "
        f"to promise anything smaller than {bound:.2f}, however clever it is.\n"
        "\n"
        "\\begin{quotebox}\n"
        "So the gap splits in two. A sharper argument could bring the guarantee "
        f"from {claimed:.2f} down to about {bound:.2f}, a factor of "
        f"{recoverable:.2f}, and there it stops. The rest is not slack in the "
        "proof at all.\n"
        "\\end{quotebox}\n"
        "\n"
        "What is left over is the distance between the rooms in this suite and "
        "the nastiest room the rules permit. No amount of cleverness recovers "
        "it, because there is nothing there to recover: the proof has to "
        "survive the nasty room, and these rooms simply are not it. That is "
        "worth separating out, because \"the guarantee is "
        f"{ratio:.1f} times larger than anything we measured\" sounds like "
        f"{ratio:.1f} times of improvement waiting to be collected, and only a "
        "fraction of it is.\n"
        "\n"
        "The obstacle in that awkward room is "
        f"{lower['obstacle_minimum_width']:.2f} cell-widths across at its "
        "narrowest, so it is narrower than a single cell. That sounds like "
        "cheating and is the opposite. An earlier version of the rules required "
        "every obstacle to be wider than a cell, and that requirement was "
        "withdrawn, because width is a property of a whole shape and a long "
        "thin triangle can be broad overall while its tip is thinner than a "
        "cell and slips straight through one. The rule in force is checked cell "
        "by cell instead. The awkward room obeys the rule that is actually in "
        "force, which is exactly why it constrains the constant actually in "
        "use.\n"
        "\n"
        f"One thing this does not settle. {bound:.2f} is the worst room anyone "
        "has built, not a proof that no worse room exists. The true answer lies "
        f"somewhere between {bound:.2f} and {claimed:.2f}, and finding it is an "
        "open question rather than a finished one."
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--example-scenario", default="wall_choice")
    parser.add_argument("--example-ceiling", type=float, default=1.5)
    # The constant this one replaced. Recorded here rather than in the prose so
    # that the retraction keeps naming the right number if it happens again.
    parser.add_argument("--superseded-constant", type=float,
                        default=3.0 + 2.0 * math.pi)
    # Measured once, in the commit that changed the constant, by re-running the
    # suite at the same lattice and geometry with nothing else altered.
    parser.add_argument("--closed-percent", type=float, default=1.6)
    args = parser.parse_args(argv)

    suite = _load("suite_bounds.json")
    safety = _load("safety_price.json")
    refine = _load("refinement.json")
    slack = _load("detour_slack.json")
    lower = _load("detour_lower_bound.json")

    if suite["violations"]:
        raise RecordError(
            f"suite_bounds.json records {suite['violations']} violations. A "
            f"bound below an achieved value is wrong, and no guide is built "
            f"from it."
        )

    blocks = {
        "example": example_block(
            suite, args.example_scenario, args.example_ceiling
        ),
        "witness": witness_block(suite),
        "range": range_block(suite),
        "safety": safety_block(safety),
        "refinement": refinement_block(refine),
        "slack": slack_block(
            slack, args.superseded_constant, args.closed_percent, refine
        ),
        "recoverable": recoverable_block(slack, lower),
    }

    text = EXPLAINER.read_text(encoding="utf-8")
    missing = [n for n in blocks if f"% generated:{n}\n" not in text]
    if missing:
        raise RecordError(
            f"the guide has no marker for: {', '.join(missing)}"
        )

    filled = text
    for name, body in blocks.items():
        pattern = re.compile(
            rf"(% generated:{name}\n).*?(\n% /generated:{name})",
            re.DOTALL,
        )
        if not pattern.search(filled):
            raise RecordError(f"the {name} block is not closed by its marker")
        filled = pattern.sub(
            lambda m: m.group(1) + body + m.group(2), filled, count=1
        )

    if args.check:
        if filled != text:
            print("the guide is out of date; run tools/build_explainer.py")
            return 1
        print("the guide is up to date")
        return 0

    if filled == text:
        print(f"no change to {EXPLAINER}")
        return 0
    EXPLAINER.write_text(filled, encoding="utf-8")
    print(f"rewrote {len(blocks)} blocks in {EXPLAINER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
