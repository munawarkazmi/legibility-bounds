# legibility-bounds

Two-sided bounds on how legible a robot trajectory can be under a path cost
budget, in a 2D polygonal world with a finite goal set.

For a world, a cost ceiling and a stated observer, the instrument is meant to
produce two numbers: a trajectory that achieves legibility `L_low`, and an
argument that no trajectory inside the budget exceeds `L_high`. The gap
between them is part of the result, because a bound whose gap is not stated
says nothing about how much room is left.

## Why

The sibling project [legible-motion-bench](https://github.com/munawarkazmi/legible-motion-bench)
measures legible motion with an optimiser. Its own status document records
the limit that this project exists to remove:

> The optimiser is a local search. It cannot prove that no trajectory exists,
> only that it did not find one, and the two are not the same claim.

Because of that, its scenario suite could not carry the one property its
specification asked for: that no trajectory inside a stated cost budget
clears a legibility threshold in a given world. A local search cannot decide
it. The legibility literature optimises with local trajectory methods and
reports what the search found.

## Where it has got to

One upper bound exists, in worlds with no obstacles, and it has been checked
against the only case where the true answer is known without searching. On
`open_pair` at cost ceiling 1.25, from `tools/open_pair_probe.py`:

    achieved   0.8374   best legibility any search here reached
    bound      0.8470   no trajectory within the budget exceeds this
    gap        0.0096
    crude      1.0000   the same bound with reachability ignored

## What is not true yet

- **Worlds with obstacles are refused, not bounded.** The bound uses
  Euclidean distance for both the belief field and the reachability
  condition, and neither is the geodesic once something stands in the way.
  Near an obstacle two points a millimetre apart in the plane can be far
  apart geodesically. This is the hardest part and none of it is done.
- **The lower bound is not certified.** The achieved figure is what a local
  search reached, which is a valid lower bound on the optimum but carries no
  argument of its own.
- There is no cell decomposition and no branch and bound.
- The bound is not converged: refining the lattice tightens it, and how much
  of the remaining gap is the lattice rather than the relaxation has not been
  separated.
- One world, one ceiling, one observer. Nothing here may be read as a trend.
- No result has been reported anywhere, and no venue has been chosen.

## The objective is not defined here

Legibility, the observer, the cost ratio and the arrival tolerance are those
of `legible-motion-bench`, which implements the formulation of Dragan, Lee
and Srinivasa (HRI 2013). That repository is vendored as a git submodule
under `vendor/` and pinned to a commit, and `legibility_bounds.vendored` is
the only place that knows where it lives. This project bounds that objective.
It does not redefine it.

Two consequences of that formulation are worth stating in the same breath as
any number:

- Legibility cannot reach 1 when there is more than one goal, by the founding
  paper's own statement. A value of 0.93 is not ninety-three per cent of the
  way to perfect.
- The cost ceiling is not an idea of ours. It is the trust region of Dragan
  and Srinivasa expressed as a ratio, and it is cited as such.

## Getting a working copy

The geometry comes in as a submodule, so a fresh clone needs it:

```bash
git clone --recursive https://github.com/munawarkazmi/legibility-bounds.git
```

If the clone was made without `--recursive`:

```bash
git submodule update --init
```

Then, on Windows:

```bash
python -m venv .venv && .venv/Scripts/python.exe -m pip install -e ".[dev]"
```

## Tests

```bash
.venv/Scripts/python.exe -m pytest -q
```

Thirteen tests. Three of them are about the vendored geometry being the right
one and behaving as the bounding argument assumes. Four of them try to make
the bound fail, including against the one case where the exact optimum is
known without searching.

To reproduce the numbers above:

```bash
.venv/Scripts/python.exe tools/open_pair_probe.py
```
