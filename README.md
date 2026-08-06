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
    door_pair            yes            0.0270     0.0067         0.09
    fan_middle           no             0.0567     0.0144         0.00
    fan_outer            no             0.0282     0.0162         0.00
    keep_out_shortcut    no             0.0198     0.0067         0.00
    narrow_gap           yes            0.0462     0.0275         0.26
    open_pair            no             0.0198     0.0067         0.00
    pillar_aisle         yes            0.0184     0.0071         0.00
    wall_choice          yes            0.0144     0.0065         0.12

The widest gap in the suite is now in a world with no obstacles at all.

What that licenses, taking `wall_choice` at a 25 per cent cost budget: the
bound is 0.6299, so no trajectory within that budget reaches legibility 0.63,
whatever search anyone runs. The local optimiser reached 0.6084 there, so the
statement is not vacuous either. The true optimum lies in an interval of width
0.0215 and both of its ends are stated.

`band` is the share of a bound decided by cells too close to an obstacle for
the straight-line argument, which are bounded more loosely. A high band share
means a weak bound, and the column exists so that weakness is located rather
than hidden.

Both ends of each interval are constructed rather than searched for. The lower
end is a **witness**: a trajectory threaded through the cells where the bound
itself found belief high and reachable, joined by exact geodesics so it cannot
walk through a wall, and scored by the vendored metric so what it claims is
what it measures. Against the vendored optimiser at 500 evaluations it wins 12
of the 32 pairs by up to 0.1485, and it is what brought the worst gap in the
suite down from 0.1553 to 0.0681. Where the search still wins, the search's
figure is used and the row says so.

## What safety costs, certifiably

A keep-out zone constrains the robot and not the watcher, so the same
machinery bounds the safety-constrained problem: how legible a trajectory can
be if it never enters a zone. Putting that bound beside an unconstrained
trajectory that exists gives a certified lower bound on the price of the
constraint. From `tools/safety_price.py`:

    world                ceiling   free ach   safe bound    price
    keep_out_shortcut       1.25     0.8353       0.8235   0.0119
    pillar_aisle            1.05     0.8022       0.7632   0.0389

Something is achievable within the budget, and nothing respecting the zone can
match it, so the constraint costs at least the difference. Comparing two
searches cannot establish that: a search that did worse under a constraint may
simply have been a worse search.

## What is not true yet

- **The certified price of safety exists only where it is positive.** Three
  of eight world and ceiling pairs certify that respecting a keep-out zone
  costs legibility; the other five certify nothing and are reported as
  nothing.
- **The witness is a construction, not an optimum.** It certifies what it
  scores and nothing more; it does not claim to be the best trajectory, and in
  `fan_middle` and at tight ceilings in `wall_choice` the vendored search
  beats it.
- The relaxation throws away every constraint linking one sample of a
  trajectory to the next. Putting one of them back, by requiring the
  trajectory to pass through an anchor, tightens the bound by at most 0.0068
  anywhere in the suite and costs more than refining the lattice would.
  `legibility_bounds/anchored.py` is kept as the evidence for that rather than
  as a tool anything runs.
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
- Nothing has been reported anywhere. The venue is IEEE Robotics and
  Automation Letters, decided 6 August 2026 from the current calls, but no
  paper exists and no format has been set up.

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

Sixty-two tests. Three are about the vendored geometry being the right one
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
