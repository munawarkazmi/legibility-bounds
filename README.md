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

## What is not true yet

Everything below is the plan, not the state. Nothing here is a claim.

- No bound of any kind is computed by this repository yet.
- Nothing has been shown about worlds containing obstacles. The argument
  sketched below relies on cost-to-go being 1-Lipschitz in the geodesic
  metric, and near an obstacle two points a millimetre apart in the plane can
  be far apart geodesically. Cells touching obstacles need their own
  treatment and have not had it.
- There is no cell decomposition, no branch and bound, and no lower bound
  construction.
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

Five tests. Three of them are about the vendored geometry being the right
one and behaving as the bounding argument assumes, rather than about anything
this repository computes.
