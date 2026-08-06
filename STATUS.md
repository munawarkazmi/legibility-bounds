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
- [x] A bound that constrains the trajectory to pass through somewhere, rather
  than letting every sample sit where it likes. `legibility_bounds/anchored.py`,
  eight tests. **It does not pay**, and the measurement is below. It is kept as
  evidence for that decision, not as a tool anything runs.
- [x] The lower bound as a construction rather than the best value a search
  happened to reach. `legibility_bounds/witness.py`, eleven tests. It beat the
  vendored optimiser in 12 of the suite's 32 world and ceiling pairs, by up to
  0.1485.
- [x] A bound for the safety-constrained problem, and with it a certified
  lower bound on what safety costs. `tools/safety_price.py`, six tests.

## The kill criterion, run 6 August 2026

The question was whether a crude upper bound sits so far above what the local
optimiser reaches that tightening it would need a different idea rather than
more cells. On `open_pair` at cost ceiling 1.25, under the geodesic observer,
against `legible-motion-bench` at `a376ab2`:

    achieved   0.8374   optimiser, 12 free waypoints tried, 4000 evaluations
    bound      0.8449   reachability, lattice 0.01
    gap        0.0075
    crude      1.0000   the bound that ignores reachability

Those two bound figures are as they stand today. When this was first run the
bound was 0.8470 and the gap 0.0096; the belief bound has been sharpened since
and the numbers below move with it.

The crude bound is the one the plan expected to be useless and it is: the
largest belief anywhere in the admissible ellipse is the belief at the goal
itself, and rounded to four places that is 1.0000. It says nothing.

The reachability bound is not useless. At normalised arc length `s` the robot
has spent `s L` of its path and must still reach the goal on what is left, so
it lies in the lens `d(S, x) <= s L` and `d(x, G) <= (1 - s) L`. Both radii
grow with `L`, so evaluating at the largest admissible length covers every
shorter one in a single pass and the bound does not have to range over path
lengths at all.

The gap is small enough to be suspicious, so the result was attacked rather
than reported.

- At a ceiling of exactly one the true optimum is known without searching: in
  a world with no obstacles the only path no longer than the optimal path is
  the straight line. Its legibility is exactly 0.6968 and the bound there is
  0.7219, so the bound is above the exact answer by 0.0251 in the one place
  the exact answer exists.
- Four optimiser configurations at 3, 5, 8 and 12 free waypoints, 4000
  evaluations each, reached 0.8353, 0.8372, 0.8374 and 0.8340. All four sit
  under the bound, and all four sit on the cost ceiling, so the constraint
  binds.
- 5333 admissible random polylines, drawn in the scratch probe rather than by
  the committed tool, reached 0.8349. Also under.

Nothing exceeded it.

The bound is not converged. Refining the lattice tightens it monotonically in
what has been run, 0.8503 at grid 0.04, 0.8468 at 0.02, and 0.8449 at 0.01,
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

`tools/suite_bounds.py` at lattice 0.0125, geodesic observer, search budget
500, written to `results/suite_bounds.json`. Eight worlds at four cost
ceilings, 32 pairs, and in every one of them the bound sits above what the
search reached. Nothing here is a trend: it is one lattice, one observer and
one search budget.

    world                obstacles   worst gap   best gap   worst band
    door_pair            yes            0.0270     0.0067         0.09
    fan_middle           no             0.0567     0.0144         0.00
    fan_outer            no             0.0282     0.0162         0.00
    keep_out_shortcut    no             0.0198     0.0067         0.00
    narrow_gap           yes            0.0462     0.0275         0.26
    open_pair            no             0.0198     0.0067         0.00
    pillar_aisle         yes            0.0184     0.0071         0.00
    wall_choice          yes            0.0144     0.0065         0.12

Over the four worlds with obstacles the gap runs 0.0065 to 0.0462, and over
the four without it runs 0.0067 to 0.0567. The widest gap in the suite is now
in a world with no obstacles at all. The `achieved` column is the better of
the vendored search and a witness built from the bound, and which of the two
produced it is recorded on every row; the witness won 13 of the 32.

What this buys is the statement the sibling benchmark could not make about
its own worlds. In `wall_choice` at a 25 per cent cost budget the bound is
0.6299, so no trajectory within that budget reaches legibility 0.63, whatever
search anyone runs. The local optimiser reached 0.6084 there, so the property
is not vacuous either: the true optimum lies in an interval of width 0.0215,
and both of its ends are now stated rather than one.

## Building the lower end instead of searching for it, 6 August 2026

`legibility_bounds/witness.py`. The upper bound already knows, for every
fraction of the way along, which reachable cells hold a high belief. A witness
takes the best of those as anchors and threads a trajectory through them.

Two properties make the result trustworthy without any argument about the
construction. The anchors are joined by exact geodesics, so the trajectory
cannot pass through an obstacle however badly they are placed. And the result
is scored by the vendored metric, so the number is a measurement of a real
trajectory rather than an estimate of one. Anchors that overshoot the budget
are pulled back towards the shortest path until it holds, which is a search on
one scalar rather than an optimisation over waypoints.

Against the vendored optimiser at 500 evaluations, over the suite's 32 world
and ceiling pairs, the witness won 12 of them by up to 0.1485. The largest
single case is `wall_choice` at ceiling 1.50, where the search reached 0.6519
and the witness reaches 0.8004 against a bound of 0.8072.

It does not always win, and it is not meant to: in `fan_middle` and at tight
ceilings in `wall_choice` the search is better. Both are reported and the
larger is taken, with `achieved_source` recording which produced it.

The effect on the interval is the point. The worst gap anywhere in the suite
falls from 0.1553 to 0.0681, and every pair where the bound was previously
limited by the search has closed:

    world             ceiling   search   witness    bound   was     now
    wall_choice          1.50   0.6519    0.8004   0.8072  0.1553  0.0068
    narrow_gap           1.50   0.6989    0.7584   0.8048  0.1059  0.0464
    door_pair            1.50   0.8221    0.8507   0.8777  0.0556  0.0270
    door_pair            1.25   0.8062    0.8505   0.8572  0.0510  0.0067

## A catch-all that turned a bug into a finding

Worth recording because it is the pattern this project inherited from next
door. The first version of the pullback search wrapped its geodesic join in
`except Exception`, meaning to treat a waypoint landing inside an obstacle as
a fact about the geometry.

`_point_at` returned numpy scalars, which the vendored exact predicate cannot
take: it branches on comparisons and builds a sign by subtracting them, and a
numpy boolean refuses subtraction. So every attempt raised `TypeError`, the
catch-all swallowed it, and the tool reported that no admissible trajectory
could be built in any world with an obstacle. A defect, presenting as a
geometric fact about five worlds.

The catch is now narrowed to the geometry error alone, and
`test_a_geometry_failure_is_not_read_as_infeasibility` drives a foreign
exception through the same path and requires it to escape.

## At loose ceilings the weak end was the search, and that is what was fixed

Recorded because it is what motivated the witness, and because the diagnosis
came from the table rather than from a hunch.

Before the witness existed, two rows did not fit the pattern. `wall_choice` at
ceiling 1.50 had a gap of 0.1553 where the same world at 1.25 had 0.0215, and
`narrow_gap` at 1.50 had 0.1059 against 0.0681 at 1.25. The upper bound rises
with the ceiling because it must, a looser budget admitting more trajectories.
What failed to rise with it was the achieved value: between ceilings 1.25 and
1.50 in `wall_choice` the search gained 0.0435 while the bound gained 0.1773.
The interval was widening at the bottom.

So at tight ceilings the certificate limited the result and at loose ones the
search did. Building the lower end rather than searching for it closed exactly
those rows: `wall_choice` at 1.50 is now 0.0068 and `narrow_gap` at 1.50 is
0.0464.

What remains is the reverse. The widest gap left is `narrow_gap` at 1.25,
0.0681, where the witness does worse than the search and the band decides 0.37
of the bound. That one is the upper end again.

## Where the tool spends its time, and the flag that fixes it

Almost all of it goes on 32 searches at 500 evaluations, not on bounds. The
optimiser never sees the lattice, so re-running at a new lattice cannot change
a single achieved value, and repeating those searches to confirm that took
half an hour of the day.

`--reuse` takes achieved values from a previous results file, which brings a
re-run down to about three minutes. It refuses unless the geometry commit,
observer, search budget and waypoint count all match, re-checks every reused
row against a freshly computed shortest path in that world, and records
`achieved_source` on each row with `reused_from` and `reused_rows` on the
file. The committed record above was produced without it, so it stands alone;
the flag exists for the iteration in between.

## The lattice is 450 times faster, 6 August 2026

`legibility_bounds/visibility.py`. Building a lattice used to ask the vendored
predicate one call at a time: 40.9 seconds for `pillar_aisle` at grid 0.05 and
49.8 for `wall_choice`. Both are now 0.12 seconds, and the bounds are
unchanged at 0.8781 and 0.7559.

The fast path is floating point and does not trust itself. Every decision is
taken with a tolerance scaled to the magnitudes in it, and any point whose
decision falls inside that tolerance is handed to the vendored predicate.
`tests/test_visibility.py` compares the two at every point of a lattice over
three worlds with obstacles, against the fully rational implementation rather
than the guarded one, so a defect in the guard could not hide behind it.
Cost-to-go agrees with the vendored index to 1.776e-15 over sampled points.

Two things had to be got right and only one was obvious.

The clip is degenerate when the segment ends on a vertex of the polygon being
tested, which is the common case, since most nodes of the visibility graph are
obstacle corners: the segment touches the boundary at t = 1 and floating point
cannot say which side it arrived from. Two thirds of points fell back on the
first attempt. That case needs no clip at all. The polygon is convex, so if
the query point lies in the closed outer half plane of either edge meeting the
node, the whole segment lies in that half plane and never reaches the
interior; and if it lies strictly inside both, the points just before the
corner are interior. The two adjacent edges settle it.

The first version of that shortcut fired on the wrong condition and was caught
by the differential test, with 4205 disagreements in `narrow_gap`. It keyed on
the node lying on an edge's *line*, which a node can do while sitting far
outside the polygon, and in `narrow_gap` a corner of one obstacle is exactly
collinear with an edge of the other. The argument needs the node on the
boundary itself.

## The band, bounded properly, 6 August 2026

The cells too close to an obstacle to cover with the straight-line argument
were capped at a belief of one. That cap was the dominant looseness in every
world with obstacles, and refining the lattice did not touch it: an earlier
run of `tools/refinement.py` moved the bound in `wall_choice` by 0.0127 across
an eightfold refinement while the band's share stayed at 0.37. The reason was
structural. A slice is decided by the band whenever its reachable set touches
an obstacle at all, and a thinner band is still touched, so more cells could
never help while each band cell was worth nothing.

The cap was standing in for the wrong quantity. Written as odds against the
true goal,

    b = 1 / (1 + sum over the other goals of
                  (p_G / p_A) exp(beta[(C_G - g_G) - (C_A - g_A)]))

bounding the belief from above needs a lower bound on the difference between
two cost-to-go values, not an upper bound on either. That matters because an
obstacle makes the second impossible and leaves the first available. Every
cost-to-go is 1-Lipschitz in the geodesic metric, so moving a distance D
inside a cell shifts the difference by at most 2D, and

    b(x) <= 1 / (1 + odds(p) exp(-2 beta D))

holds over the whole cell. The obstacle problem is then one scalar per cell:
the largest geodesic distance between two of its points.

**No universal D exists, and none is claimed.** A wall thinner than a cell
puts two neighbouring points a wall's length apart geodesically. What exists
is a bound under a precondition that can be checked: if no obstacle is thinner
than a cell and no two obstacles are closer together than a cell, then a
cell's free part is in one piece and meets at most one obstacle. Under that,
a path between two free points of a cell runs inside the cell, going straight
where it can and following the obstacle boundary where it cannot, which costs
at most 2r of straight travel plus a convex arc inside a disc of radius r, so

    D <= 2 (1 + pi) r

`minimum_width` and `minimum_separation` compute the precondition per
scenario, and it is reported as `detour_certified` rather than assumed. Where
it fails the detour is infinite and everything falls back to what holds
unconditionally, which is the cap of one.

The geometric claim is not left as an argument.
`test_the_detour_bound_holds_against_real_geodesics` samples point pairs
inside real band cells and measures the true geodesic with the vendored
implementation, and `test_the_precondition_is_reported_and_can_fail` builds a
deliberately too-coarse lattice and checks that it refuses to certify.

Same tool, same three worlds, after the change:

    world           grid 0.05 to 0.00625      bound moved   band moved
    wall_choice     0.6540 to 0.6180               0.0360       0.0777
    narrow_gap      0.7855 to 0.7228               0.0627       0.0232
    pillar_aisle    0.8614 to 0.8540               0.0074       0.0000

Two things changed together. The bounds are much lower: `wall_choice` at grid
0.05 falls from 0.7559 to 0.6969, and at the finest lattice to 0.6220 against
an achieved 0.6084, so a gap of 0.1475 becomes 0.0136. And refinement now
works, moving the bound six times as far as it did before, because D scales
with the lattice. In `pillar_aisle` the band no longer decides a single slice.

The earlier conclusion, that refining cannot fix the band, was true of the cap
and is not true of the bound that replaced it. It is recorded here rather than
removed, because the reasoning that led to it is what produced this.

## Three versions of the constant, and a precondition that was not sufficient

The constant went through three forms in one day and the history is kept
because two of them were wrong in different ways.

`2(1 + pi) r` was **not a bound**. It counted one diameter of straight travel
where the construction needs two, and was twenty-four per cent too small.

`(4 + 2 pi) r` was sound but answered a harder question than anything here
asks: the distance between two arbitrary points of a cell. What the belief
bound and the reachability test both need is only the distance from a cell
point to the lattice point at its centre, and the centre being free shortens
the argument. From a point outside a convex body, the ray heading directly
away from that body's nearest point never re-enters it, so the centre reaches
the circle in exactly `r` and any other cell point in at most `2r`; the free
part of the circle is a single arc, so the two arrivals join along it in at
most `2 pi r`. Hence

    D <= r + 2r + 2 pi r = (3 + 2 pi) r

which is what the code now uses. The correction is worth little on its own:
`wall_choice` at grid 0.05 moved from 0.6998 to 0.6969.

**The precondition was the real defect.** It tested
`minimum_width(obstacle) > 2r` once per world. Minimum width is a global
property, and a convex polygon with a sharp vertex can be far wider than a
cell overall while its tip is thinner than one and passes clean through a
cell, splitting its free part in two and putting the halves an obstacle apart
rather than a cell apart. That is precisely the case the precondition exists
to exclude and it did not exclude it.

`cells_certified` now decides it per cell, by counting where each obstacle's
boundary crosses the cell's circle: four crossings means the obstacle passes
through. It also refuses a cell that two obstacles touch, since the argument
follows one boundary. Deciding per cell is better as well as correct, because
a failing cell loses the bound instead of the whole world losing it.

Every obstacle in the vendored suite is a rectangle, so no committed number
ever depended on the difference. The condition was stated as though general
and was not, which is the part that mattered.
`test_a_sharp_vertex_defeats_the_global_width_test_but_not_this_one` holds it
with a long acute triangle a global test would wave through.

Neither error was found by a failing test. The test that should have caught
the first sampled point pairs in one world with one seed and asserted only
that nothing exceeded the claim, which a too-small constant passes, because
random pairs inside a cell are almost never separated by an obstacle. It now
runs over four worlds, deliberately samples cells beside obstacle corners,
counts the pairs the obstacle actually separated, and fails if there are none.
Across `wall_choice`, `narrow_gap`, `pillar_aisle` and `door_pair` it measures
5, 16, 11 and 21 separated pairs.

Those same measurements say the constant is still loose. The worst detour
observed anywhere is about 2.2 cell radii against a claimed 9.28. It is not
tuned to that and must not be, since a bound fitted to samples is not a bound.

## The constant was not what needed fixing, 6 August 2026

Sharpening it turned out to be the wrong target. Almost no band cell wraps at
all.

Take a band cell the obstacle does not pass through, which is already checked.
If it also holds no obstacle vertex, then the obstacle's boundary inside it
lies within a single edge: two edges of a convex polygon meet at a vertex, so
a cell crossed by two of them without their shared vertex would cross the
cell's circle four times and be refused. A single straight boundary cuts the
cell with a half plane, leaving a convex free part, so the segment from the
centre to any free point of the cell is itself free and

    D = |x - p| <= r

exactly as for a cell nowhere near an obstacle. Corners are O(1) per obstacle
while boundary cells are O(1/h) of them, so this covers all but a handful.

    world           band share      bound at grid 0.0125
    wall_choice     0.34 to 0.11    0.6299 to 0.6218
    narrow_gap      0.37 to 0.26    0.7579 to 0.7271
    pillar_aisle    0.00 to 0.00    0.8551 to 0.8551

Across the suite the worst gap fell from 0.0681 to 0.0567, and the widest one
is now in `fan_middle`, which has no obstacles at all. `narrow_gap` keeps a
band share of 0.26 because its two obstacles put four corners either side of a
gap the admissible corridor runs straight through, so its corner cells sit
exactly where the trajectory has to go. Sharpening the constant would pay off
there and almost nowhere else.

Two tests hold the claim. One requires every cell still wrapping to have a
corner within its own radius, and plain band cells to outnumber them. The
other samples points inside plain band cells and checks the true geodesic to
the centre never exceeds the straight line, which is what convexity asserts.

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

## The certified price of safety, 6 August 2026

`tools/safety_price.py` at lattice 0.025, written to
`results/safety_price.json`. Two worlds in the suite carry keep-out zones.

    world                ceiling   free ach   safe ach   safe bound    price
    keep_out_shortcut       1.05     0.7870     0.7509       0.7915     none
    keep_out_shortcut       1.10     0.8079     0.7737       0.8013   0.0066
    keep_out_shortcut       1.25     0.8353     0.7890       0.8235   0.0119
    keep_out_shortcut       1.50     0.8594     0.8170       0.8661     none
    pillar_aisle            1.05     0.8022     0.7274       0.7632   0.0389
    pillar_aisle            1.10     0.8208     0.7407       0.8370     none
    pillar_aisle            1.25     0.8456     0.8446       0.8572     none
    pillar_aisle            1.50     0.8682     0.8663       0.8772     none

Two of those columns are of different kinds and putting them together is the
point. `free ach` is a trajectory that exists, scored by the vendored metric,
which may cross a keep-out zone. `safe bound` is an upper bound no trajectory
within the budget can pass if it never enters one. Where the first exceeds the
second, the difference is a certified lower bound on what the constraint
costs: something is achievable and nothing safe can match it.

Three of the eight pairs certify a positive price, the largest 0.0389 in
`pillar_aisle` at ceiling 1.05. The rest certify nothing and say so rather
than reporting a negative number as though it were a finding.

This is the statement the sibling benchmark cannot make. Comparing two
searches cannot show a constraint costs anything, because a search that did
worse under a constraint may simply have been a worse search. Comparing an
achieved trajectory against a bound over all trajectories can.

The jump in `pillar_aisle` between ceilings 1.05 and 1.10, where the safe
bound moves from 0.7632 to 0.8370, was checked rather than reported. It agrees
with what the sibling's own status file records about that world, that its
interesting structure sits between those two ceilings, so it corroborates
rather than surprises.

## Two detours, because they bound two different things

Building the constrained lattice turned up an error that had been latent in
the unconstrained one. The first version treated keep-out zones as ordinary
blockers throughout, and the constrained bound in `keep_out_shortcut` came out
**above** the unconstrained one, 0.8551 against 0.8519, with the band's share
of the result jumping to 0.58.

A smaller feasible set cannot admit a more legible trajectory, so the number
was impossible as a bound on the constrained optimum and had to be a defect.
It was: a keep-out zone constrains the robot and not the watcher. The belief
is a function of the observer's cost-to-go, which is defined over obstacles
alone, so a keep-out boundary cannot make the belief harder to bound inside a
cell. Treating it as a blocker manufactured band cells for a quantity it has
no bearing on.

The lattice now carries two detours: one against obstacles, which bounds how
much the belief can move inside a cell, and one against everything that blocks
the robot, which bounds how much its cost-to-go can. They are the same array
whenever keep-out zones are not being respected.
`test_the_observer_does_not_see_the_keep_out_zone` holds the belief field
identical between the two lattices while requiring the reachability side to
have moved.

## Anchoring the trajectory does not pay, 6 August 2026

The relaxation lets every sample sit wherever its own lens allows,
independently of every other sample, and the standing assumption here was that
this discarded coupling held most of the remaining looseness. Adding one
anchor puts a piece of it back: the trajectory passes through a point at a
stated fraction of the way along, so every sample at fraction `s` obeys
`d(y, x) <= |s - f| L`. The anchor is unknown, so the bound is the largest
value over every anchor it could have had.

Evaluating one candidate anchor costs as much as the whole plain bound, and
there are as many candidates as lattice points. What makes it affordable is
that the value at every candidate at once, for one slice, is a maximum over a
window around each point, so one sweep per slice serves every candidate.

At the lattice the suite reports:

    world           ceiling    plain   anchored   tighter   anchor cost
    narrow_gap         1.25   0.7271     0.7202    0.0068          136s
    wall_choice        1.25   0.6218     0.6217    0.0001           94s
    door_pair          1.50   0.8777     0.8762    0.0014          293s

Set against the alternative, refining the lattice from 0.025 to 0.0125
tightens `narrow_gap` by 0.026 and costs 5.5 seconds, where one anchor at
0.0125 tightens it by 0.0068 and costs 136. Refinement buys roughly twenty
times more per second, so the multi-anchor version was not built: it would
cost a full dynamic program over anchor placements to beat a baseline a
lattice refinement already beats.

The standing assumption is therefore wrong at one anchor. Whatever is left in
these gaps, it is not mostly the coupling between samples.

Three things were checked before believing that, because a negative result
caused by slack in its own instrument is worth nothing.

- The window was rounded up to a power of two, which is sound but can nearly
  double it, and a window twice as wide weakens exactly the constraint being
  measured. Making it exact roughly doubled the measured tightening.
- A candidate anchor with no reachable sample at some fraction was being
  scored at one, as though its value were unknown. It is not unknown, it is
  infeasible, and scoring it at one let impossible anchors win a maximum taken
  over anchors. `test_an_anchor_can_only_tighten` is the regression.
- The exact window maximum is held to brute force over 40 random cases,
  including at the edges, where an earlier version returned minus infinity for
  every window overhanging one.

## What the bound throws away, and what would tighten it

The relaxation bounds a trajectory that need not be a trajectory: the point
may jump anywhere inside the next lens. Adding the constraint that
consecutive samples lie within `L / N` of each other turns the problem into a
resource-constrained shortest path over position and path spent, which is a
dynamic program rather than a per-slice maximum. That is the obvious next
piece, and it is also where a certified lower bound would come from, since
any path the dynamic program returns is realisable. It is not built.

## Target venue, decided 6 August 2026

IEEE Robotics and Automation Letters. Terms read from the calls on 6 August
2026 rather than assumed, because the handoff carried RA-L as a working guess
and one of the two candidates turned out to be closed.

- Rolling submission, no deadline. A final decision within six months of
  submission, and about four months from submission to early access.
- Six pages, with at most two more at an overlength charge.
- Double-anonymous review, which matters for an author with no affiliation.
- An accepted paper may be presented at a RAS conference within 270 days of
  acceptance.

**WAFR is closed and was the better fit for the algorithmic framing.** The
17th symposium ran 15 to 17 June 2026 in Oulu, and its submission deadline was
1 February 2026, extended from 15 January. Its site still looks live because
camera-ready is due 17 August 2026. WAFR is biennial, so the next edition is
most likely 2028 and no call exists for it. That removes it from the decision
for about two years rather than making it a choice.

**The ICRA 2027 transfer is not being chased.** ICRA 2027 is in Seoul, 24 to
28 May 2027. An accepted RA-L paper can be transferred into it until 31
December 2026, but that requires acceptance by then, which in turn requires
clearing review with no substantive revision from a submission made now. A
first-round accept is not the normal outcome and planning around one would
mean writing to a deadline that probably does not pay out. The presentation
route stays open later through IROS 2027 or ICRA 2028.

Direct submission to ICRA 2027 by 15 September 2026, at eight pages, was the
alternative and was declined. It buys a hard date in exchange for a venue that
suits an instrument paper less well, and a rejection in January would cost
four and a half months with nothing archival.

Nothing about the format has been set up yet. The sibling project's LaTeX
notes do not transfer: it vendors the ACM `acmart` class because its
distribution does not ship it, and RA-L wants IEEE's, which is a different
problem with different gotchas.

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
