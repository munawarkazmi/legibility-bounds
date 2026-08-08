"""The generated documents agree with the records they are generated from.

Two documents quote figures from `results/`: the README and the plain-language
guide. Both have a `--check` mode that rebuilds their blocks in memory and
fails if the committed text differs. Nothing ran either of them, which is the
same gap one level up: a mechanism that prevents drift, and no one checking
that it did.

This is what makes the guide's markers worth having. Before them the guide's
numbers were typed, and a stale one sat in it long enough to hold a stale claim
on the site green, because the site's drift checker asks whether a number is
still findable in this repository rather than whether it is still true. Markers
alone would not have caught that either. A marker plus a test does.

Run as a subprocess rather than by import, because `--check` is the interface a
person or a hook would use, and testing the function behind it would leave the
argument handling and the exit status untested.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

GENERATORS = [
    ("README.md", "build_readme.py"),
    ("docs/explainer/explainer.tex", "build_explainer.py"),
]


@pytest.mark.parametrize("document, tool", GENERATORS)
def test_the_generated_document_matches_its_records(document, tool):
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / tool), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"{document} no longer matches the records it is built from. Run "
        f"tools/{tool} and commit the result.\n\n"
        f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    )


@pytest.mark.parametrize("document, tool", GENERATORS)
def test_every_block_the_generator_writes_has_a_marker(document, tool):
    """A generator writing a block the document has no marker for is silent.

    The check mode compares the filled text against the committed text, so a
    block whose marker was deleted would simply never be substituted and the
    comparison would still pass. Both generators raise instead, and this is
    what confirms they still do rather than trusting that they do.
    """
    text = (ROOT / document).read_text(encoding="utf-8")
    source = (ROOT / "tools" / tool).read_text(encoding="utf-8")

    # The block names each generator knows about, read off its own dict.
    start = source.index("blocks = {")
    end = source.index("}", start)
    names = [
        line.split('"')[1]
        for line in source[start:end].splitlines()
        if line.strip().startswith('"')
    ]
    assert names, f"could not read the block names out of {tool}"

    for name in names:
        assert f"generated:{name}" in text, (
            f"{tool} writes a block called {name!r} but {document} has no "
            f"marker for it, so the block would be dropped without complaint"
        )
