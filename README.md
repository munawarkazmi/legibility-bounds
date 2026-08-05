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

Every world in the sibling suite carries an upper bound at four cost
ceilings, worlds with obstacles included. 32 pairs, and in all of them the
bound sits above what a search reached. From `tools/suite_bounds.py`, written
to `results/suite_bounds.json`:

    world                obstacles   worst gap   best gap   worst band
    door_pair            yes            0.0556     0.0322         0.18
    fan_middle           no             0.0567     0.0144         0.00
    fan_outer            no             0.0282     0.0210         0.00
    keep_out_shortcut    no             0.0198     0.0075         0.00
    narrow_gap           yes            0.1059     0.0389         0.37
    open_pair            no             0.0198     0.0075         0.00
    pillar_aisle         yes            0.0184     0.0072         0.00
    wall_choice          yes            0.1553     0.0213         0.34

What that licenses, taking `wall_choice` at a 25 per cent cost budget: the
bound is 0.6299, so no trajectory within that budget reaches legibility 0.63,
whatever search anyone runs. The local optimiser reached 0.6084 there, so the
statement is not vacuous either. The true optimum lies in an interval of width
0.0215 and both of its ends are stated.

`band` is the share of a bound decided by cells too close to an obstacle for
the straight-line argument, which are bounded more loosely. A high band share
means a weak bound, and the column exists so that weakness is located rather
than hidden.

At the loosest ceiling the wide gaps are the search's doing rather than the
bound's: between ceilings 1.25 and 1.50 in `wall_choice` the optimiser gains
0.0435 while the bound gains 0.1759.

## What is not true yet

- **The bound is blind to safety.** It bounds legibility alone, so
  `open_pair` and `keep_out_shortcut`, which differ only by a keep-out zone,
  receive identical bounds. Bounding the safety-constrained problem is not
  done.
- **The lower bound is not certified.** The achieved figure is what a local
  search reached, which is a valid lower bound on the optimum but carries no
  argument of its own.
- There is no cell decomposition and no branch and bound. The relaxation
  throws away every constraint linking one sample of a trajectory to the
  next.
- **The bound near obstacles rests on a precondition, checked cell by cell.**
  Cells too close to an obstacle for the straight-line argument are bounded
  through the geodesic distance from a cell point to the cell's centre, which
  can only be bounded where the obstacle does not pass clean through the cell
  and no second obstacle touches it. `cells_certified` decides that for each
  cell by counting boundary crossings of the cell's circle; a cell that fails
  falls back to a belief of one and is counted in `uncertified_cells`. No
  claim is made that the precondition holds in general.
- **The constant in that bound is loose.** The worst detour measured anywhere
  is about 2.2 cell radii against a claimed 9.28. Closing it needs a real
  bound on how far a convex boundary can wrap inside a disc.
- One lattice, one observer, one search budget. Nothing here may be read as a
  trend.
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

Thirty-five tests. Three are about the vendored geometry being the right one
and behaving as the bounding argument assumes. Several try to make the bound
fail, including against the one case where the exact optimum is known without
searching: at a ceiling of exactly one in a world with no obstacles, the only
admissible trajectory is the straight line, so the optimum is its legibility
and no search is involved.

To reproduce the table above, and the single-world probe it grew out of:

```bash
.venv/Scripts/python.exe tools/suite_bounds.py
```

```bash
.venv/Scripts/python.exe tools/open_pair_probe.py
```
