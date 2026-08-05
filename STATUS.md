# Status

A living document, written as the work happens. Every tick below is
verifiable from this repository; nothing is marked done that cannot be
inspected.

## Current status

- [x] The geometry is vendored rather than copied. `legible-motion-bench` is
  a git submodule under `vendor/`, pinned to `a376ab2`, and
  `legibility_bounds/vendored.py` is the only module that knows where it is.
  Five tests, three of which hold the two facts about the objective that the
  bounding argument rests on.
- [x] A first upper bound, from reachability alone, in worlds with no
  obstacles. `legibility_bounds/reachability.py`, eight tests, reproduced by
  `tools/open_pair_probe.py` into `results/open_pair_probe.json`. It is the
  loosest useful member of the family and it is here because it decides
  whether the idea is alive. It is not the instrument the project is for.
- [x] Worlds with obstacles. `legibility_bounds/lattice.py`, seven tests. The
  exact geodesic comes from the vendored visibility-graph index, and cells
  too close to an obstacle for that argument to cover are handled separately
  and their cost is reported rather than argued. All eight worlds of the
  suite now carry a bound at four ceilings.
- [ ] Cell decomposition, and a bound that constrains consecutive samples
  rather than letting the path jump between them. Not started, and this is
  what would tighten the gaps below.
- [ ] The lower bound as a construction that certifies what it claims,
  rather than the best value a search happened to reach. Not started.
- [ ] A bound for the safety-constrained problem. Not started. See the note
  on `keep_out_shortcut` below, which is the reason it is now obvious.

## The kill criterion, run 6 August 2026

The question was whether a crude upper bound sits so far above what the local
optimiser reaches that tightening it would need a different idea rather than
more cells. On `open_pair` at cost ceiling 1.25, under the geodesic observer,
against `legible-motion-bench` at `a376ab2`:

    achieved   0.8374   optimiser, 12 free waypoints tried, 4000 evaluations
    bound      0.8470   reachability, lattice 0.01
    gap        0.0096
    crude      1.0000   the bound that ignores reachability

The crude bound is the one the plan expected to be useless and it is: the
largest belief anywhere in the admissible ellipse is the belief at the goal
itself, and rounded to four places that is 1.0000. It says nothing.

The reachability bound is not useless. At normalised arc length `s` the robot
has spent `s L` of its path and must still reach the goal on what is left, so
it lies in the lens `d(S, x) <= s L` and `d(x, G) <= (1 - s) L`. Both radii
grow with `L`, so evaluating at the largest admissible length covers every
shorter one in a single pass and the bound does not have to range over path
lengths at all.

The gap of 0.0096 is small enough to be suspicious, so the result was
attacked rather than reported.

- At a ceiling of exactly one the true optimum is known without searching: in
  a world with no obstacles the only path no longer than the optimal path is
  the straight line. Its legibility is exactly 0.6968 and the bound there is
  0.7279, so the bound is above the exact answer by 0.0311 in the one place
  the exact answer exists.
- Four optimiser configurations at 3, 5, 8 and 12 free waypoints, 4000
  evaluations each, reached 0.8353, 0.8372, 0.8374 and 0.8340. All four sit
  under the bound, and all four sit on the cost ceiling, so the constraint
  binds.
- 5333 admissible random polylines, drawn in the scratch probe rather than by
  the committed tool, reached 0.8349. Also under.

Nothing exceeded it.

The bound is not converged. Refining the lattice tightens it monotonically in
what has been run, 0.8576 at grid 0.04, 0.8507 at 0.02, and 0.8470 at 0.01,
which is the tool's default and the figure quoted above. The remaining
looseness is therefore partly the lattice and partly the relaxation, and the
two have not been separated.

What this does not establish. `open_pair` is the easiest world in the suite:
no obstacles, two goals placed symmetrically, and a belief field whose
maximisers over successive lenses happen to trace something a path can very
nearly follow. The relaxation throws away every constraint linking one sample
to the next, so a world where those maximisers jump would loosen it, and
nothing here says how much. One world, one ceiling, one observer.

## The whole suite, 6 August 2026

`tools/suite_bounds.py` at lattice 0.05, geodesic observer, search budget 500,
written to `results/suite_bounds.json`. Eight worlds at four cost ceilings,
32 pairs, and in every one of them the bound sits above what the search
reached. Nothing here is a trend: it is one lattice, one observer and one
search budget.

    world                obstacles   worst gap   best gap   worst band
    door_pair            yes            0.0717     0.0654         0.23
    fan_middle           no             0.0717     0.0290         0.00
    fan_outer            no             0.0470     0.0374         0.00
    keep_out_shortcut    no             0.0377     0.0213         0.00
    narrow_gap           yes            0.1527     0.1256         0.51
    open_pair            no             0.0377     0.0213         0.00
    pillar_aisle         yes            0.0493     0.0282         0.28
    wall_choice          yes            0.1804     0.1331         0.46

Over the four worlds with obstacles the gap runs 0.0282 to 0.1804, and over
the four without it runs 0.0213 to 0.0717.

What this buys is the statement the sibling benchmark could not make about
its own worlds. In `wall_choice` at a 25 per cent cost budget the bound is
0.7559, so no trajectory within that budget reaches legibility 0.76, whatever
search anyone runs. The local optimiser reached 0.6084 there, so the property
is not vacuous either: the true optimum lies somewhere in between, and both
ends of that interval are now stated rather than one.

## Where the bound is weak, stated in its own column

Every bound reports `weight_from_band`, the share of the result decided by
cells too close to an obstacle for the straight-line argument to cover. Those
cells are capped at a belief of one, which is true and nearly useless, so a
world with a high band share has a weak bound and the column says so.

It reaches 0.51 in `narrow_gap` at ceiling 1.5 and 0.46 in `wall_choice` at
the same ceiling, and it is zero in every world without obstacles. The two
worlds with the largest gaps are exactly the two with the largest band
shares, which is what the column is for: the looseness is located rather than
merely present. Refining the lattice narrows the band, since its width is
half a cell diagonal, and that has not been run yet at a finer lattice
because a lattice build is currently tens of seconds per world.

## Two worlds return identical numbers, and it is not a defect

`open_pair` and `keep_out_shortcut` agree to four decimals in all four rows,
which is the shape of a bug rather than a result and was checked before being
reported. The two scenarios have the same bounds, the same start at (1, 5),
the same goals at (11, 8) and (11, 2), and both declare no obstacles.
`keep_out_shortcut` is `open_pair` with a keep-out zone added.

Keep-out zones do not block motion, by the sibling project's explicit
decision, so they enter neither the geodesic cost, nor the belief, nor this
bound. The unconstrained optimiser ignores them too. Identical numbers are
therefore forced rather than surprising.

The consequence is a limitation that has to be stated wherever this is
reported. **This bound is blind to safety.** It bounds legibility alone, so
two worlds differing only in a safety constraint receive the same bound.
It also points straight at the next piece: marking keep-out cells unusable in
the lattice would bound the safety-constrained problem, which is a different
and lower quantity, and that is the frontier the sibling project exists to
measure.

## What the bound throws away, and what would tighten it

The relaxation bounds a trajectory that need not be a trajectory: the point
may jump anywhere inside the next lens. Adding the constraint that
consecutive samples lie within `L / N` of each other turns the problem into a
resource-constrained shortest path over position and path spent, which is a
dynamic program rather than a per-slice maximum. That is the obvious next
piece, and it is also where a certified lower bound would come from, since
any path the dynamic program returns is realisable. It is not built.

## Decisions taken

- 6 August 2026. The exact geometry is imported from `legible-motion-bench`
  as a pinned submodule rather than copied into this repository. The whole
  claim rests on the cost-to-go being exact, and two copies of that code
  would be two things to keep correct. A bound is only worth stating about
  the objective it is actually bounding, so the bound and the benchmark
  share one implementation and cannot drift apart. The pin is recorded in
  `vendored.PINNED_COMMIT` as well as in the git index, and a test fails if
  the submodule is moved to another commit.

## Two facts about the objective, checked before anything was built

Both were read out of the vendored implementation and then asserted against
it in `tests/test_vendored.py`. Neither is obvious from the definition of
legibility, and the whole approach depends on both.

**The observer's belief is a static field over the plane.** The posterior
scores each goal by `C*(S -> G) - C(travelled) - C*(x -> G)`. The travelled
term is identical for every goal, so it cancels when the scores are
normalised. Belief therefore depends only on where the robot is, not on how
it got there. Over 200 random point-and-detour pairs the largest difference
was 4.441e-16.

This is what makes legibility a weighted average of a fixed scalar field
along a path, and it is what any per-point bound needs.

**Legibility does not depend on duration.** The weights are `f(t) = T - t`
with `t_i = T i / N`, so they are `T(1 - i/N)`, and they are divided by their
own sum. `T` cancels exactly. The same path scored at speed 1.0 and speed 3.7
returns bit-identical `0.8070692299607565`.

This matters because the normalisation was expected to be the hardest part:
the objective divides by the trajectory's own duration, so it looked as
though a bound would have to range over the whole interval of durations the
cost budget allows. It does not. What survives is that the path's length
still sets the sample count `N`, and the weighting is over normalised arc
length rather than absolute time.

One consequence for the write-up, and it is a limitation rather than a
convenience. Weighting by normalised arc length means "early" stretches with
the trajectory: a path twice as long spreads the same weight over twice the
distance. The sibling repository already records this tension, and says that
a claim about a fixed hesitation window has to be made with time to
confidence and not with legibility. That still holds here.

## What is deliberately not in this repository

No copy of the cost-to-go, the observer, the metrics or the scenarios. They
are imported. A test asserts that the vendored cost-to-go reproduces the
optimal cost that `open_pair` carries as a machine-checked property, so the
import path itself is checked rather than assumed.
