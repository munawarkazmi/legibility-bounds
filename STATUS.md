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
    keep_out_shortcut       1.05     0.7870     0.7509       0.7911     none
    keep_out_shortcut       1.10     0.8079     0.7737       0.8009   0.0070
    keep_out_shortcut       1.25     0.8353     0.7890       0.8225   0.0128
    keep_out_shortcut       1.50     0.8594     0.8170       0.8661     none
    pillar_aisle            1.05     0.8022     0.7274       0.7558   0.0464
    pillar_aisle            1.10     0.8208     0.7407       0.8370     none
    pillar_aisle            1.25     0.8456     0.8446       0.8572     none
    pillar_aisle            1.50     0.8682     0.8663       0.8772     none

Two of those columns are of different kinds and putting them together is the
point. `free ach` is a trajectory that exists, scored by the vendored metric,
which may cross a keep-out zone. `safe bound` is an upper bound no trajectory
within the budget can pass if it never enters one. Where the first exceeds the
second, the difference is a certified lower bound on what the constraint
costs: something is achievable and nothing safe can match it.

Three of the eight pairs certify a positive price, the largest 0.0464 in
`pillar_aisle` at ceiling 1.05. The rest certify nothing and say so rather
than reporting a negative number as though it were a finding.

`keep_out_shortcut` at ceiling 1.25 is the case worked in full in the paper,
because that world was built to ask exactly this question. Its cheapest route
scores 0.6968 and is already safe, so the constraint costs nothing to a robot
that does not try to be understood. A trajectory scoring 0.8353 exists within
the budget and crosses the zone, and nothing within the budget that stays out
of it reaches 0.8225. So being understood there costs at least 0.0128.

Reported the other way round, as the difference between two searches, the same
world would have appeared to cost 0.8353 against 0.7890, a larger number with
nothing behind it.

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

## Building the paper

From the TeX distribution, which on this machine is the one inside WSL:

    cd paper && make
    cd paper && make check

The distribution is TeX Live 2025 on Debian and it does not ship `IEEEtran`,
the same problem the sibling project has with the ACM class and solved the
same way. `texlive-publishers` would supply it through apt but needs root and
is a machine-wide change, and `tlmgr --usermode` would put it in `~/texmf` but
would leave a fresh clone unable to build. So both files are vendored beside
the paper, taken from CTAN on 6 August 2026:

    IEEEtran.cls   281957 bytes   version V1.8b, 2015/08/26
      sha256 da751920a317ed318b7b5cd7fa585a6cc7d28502d457856382e9be24b10a3bd7
    IEEEtran.bst    57748 bytes
      sha256 314f0ece704568faf827011bac498650691b2b5ee06320720830e782416d5a5f

`make check` fails on the two things that otherwise pass silently and matter
at submission. An undefined reference, which a build reports and then carries
on from. And a Type 3 font, which IEEE refuses and which matplotlib writes
into a PDF unless told not to; the sibling project shipped one without
noticing and caught it only by running `pdffonts`. As of 6 August 2026 the
skeleton builds to one page with no undefined references and five fonts, all
Type 1, embedded and subset.

The document carries no number by hand. `tools/build_paper_tables.py` writes
everything under `paper/generated/` from the committed results: the suite
table, the safety price table, and a file of macros for the quantities that
appear in prose, so that a sentence quoting the worst gap writes
`\suiteWorstGap` and cannot disagree with the record it came from. The
Makefile rebuilds them whenever a results file is newer, so a paper cannot be
built from a table older than the numbers it reports.

Two refusals are built into that tool rather than left to care. It will not
write anything if the records were produced against a different geometry from
the one this repository is pinned to, because a paper built from a table
describing another version of the world is wrong in a way proofreading cannot
catch. And it will not write anything if the suite records any bound
violation.

As of 6 August 2026 the skeleton builds to two pages with no undefined
references, seven fonts all Type 1 and embedded, and four font warnings. The
warnings are all `OT1/ptm/m/scit`, the small caps italic that IEEEtran asks
for and the Nimbus clone of Times does not carry. They are cosmetic and are
recorded here so they are not rediscovered later.

The suite table is folded to one row per world: the ceiling where that world's
interval is widest, with both ends of it, and the world's narrowest gap over
all four ceilings. The full eight by four grid is still written, to
`generated/suite_full.tex`, and is simply not part of a six page paper.

Three checks were wrong when first written and all three would have been worse
than having none.

- Searching the log for `undefined` also matches `Font shape ... undefined`,
  a benign substitution, so the check failed on a clean build. A check that
  cries wolf gets ignored, and then misses the real thing.
- Counting `Font shape` counted 44 where only 4 were warnings, the rest being
  routine bold-extended substitution in Times.
- The overfull box check was added last and immediately found a real one, 12.94
  points, which took four wrong guesses to place. It was not the cmidrules, not
  the running head, and not the font size: IEEEtran already sets table bodies in
  `\footnotesize` and sets the size itself around the caption, so asking for a
  smaller size before the caption did nothing at all and asking again after it
  did nothing either. The cause was the world names being set in typewriter,
  which is wider. They are set in the body font now and the table fits at the
  class's own size, which is a better fix than shrinking the type.

Two rule breaches of mine were in the generator and are fixed there. A missing
value was written as `--`, which LaTeX renders as an en dash, and an absent
safety price as `\textemdash`. Both now write the word `none`. The rule against
dashes applies to generated output as much as to prose.

## The draft, 6 August 2026

A first draft builds to three pages against a limit of six, with no undefined
references and no overfull boxes. It is a draft in the sense that every
section carries real content and real numbers, not in the sense that it is
finished.

What the paper is, decided 6 August 2026: the instrument and the certificate.
The safety price gets half a page as a results subsection. The witness is a
subsection of the bound rather than a section of its own, since it exists to
make the interval two-sided rather than as a contribution in itself.

## The literature pass, 6 August 2026

Both founding papers were read in the body, not the abstract, and
`paper/verification_log.md` records what was checked and what each check
changed. Seven claims across the two, all seven supported, with the wording
quoted in the log.

What it settles, and each of these had been asserted somewhere in this project
before it was checked:

- The legibility functional is equation (9) of the HRI paper, averaging the
  posterior under a weight favouring early motion and dividing by that
  weight's integral. `f(t) = T - t` is that paper's own example.
- Legibility cannot be driven to one with more than one goal, in the paper's
  own words, so a value near one is not a proportion of anything attainable.
- The cost bound is theirs. The HRI paper adds a regulariser immediately after
  that sentence, to stop the robot departing too far from expectation, and the
  RSS paper makes it a hard constraint and calls it a trust region.
- "The legibility model can only be trusted inside this trust region" is a
  direct quotation. Reporting only at stated ceilings is their requirement
  rather than our caution.
- Legibility carries motion towards obstacles. The HRI paper identifies it,
  captions a figure "Legibility is not obstacle avoidance", and does not
  measure it. That is the gap the safety-constrained bound fills.
- Observers do form a belief that the robot is pursuing none of the declared
  goals, once motion becomes strange enough, and the RSS follow-up study
  measures it directly.

That last one matters procedurally. It was carried into this project from the
sibling repository's notes and was written into a draft here before it had
been checked. It holds, but the order was wrong, and the log says so.

## Read end to end, 6 August 2026

The draft had been written in pieces over a day and never read as a whole.
Doing that found six things, none of which any check would have caught, since
all of them were correct sentences in the wrong relation to each other.

- The header comment still said the literature pass had not happened. It had,
  twice over.
- The largest certified safety price was stated twice in one subsection, three
  paragraphs apart, in nearly the same words.
- The word "anchor" carried two meanings. In the witness subsection it is a
  waypoint the constructed trajectory passes through; in the limitations it
  was a constraint point in a tightened bound. Different ideas, same word, one
  page apart. The limitations paragraph now describes the thing rather than
  naming it.
- "Two further findings bear directly on sections below" was followed by three
  paragraphs, because a citation to subsequent work had been inserted between
  them without adjusting the sentence that counted them.
- The abstract still opened with "Legible motion is optimised, not decided",
  which the introduction now immediately qualifies: it is optimised because
  the optimum is intractable. A reader meeting the abstract and then the
  introduction would have seen the paper correct itself in the first column.
- **There was no conclusion.** The paper ended on its limitations and went
  straight to the bibliography, which left it stopping on its weakest note and
  never restating what the reader had been shown.

The last one is the one that mattered. The other five are the kind of drift a
document accumulates when it is edited in place and never read from the top.

The paper's whole point was left implicit in a table: a reader had to work out
for themselves what a row licensed. Section V-A now states it in words for one
world, as a displayed quotation, and separates the three things that make it
worth having. It is negative and quantifies over every trajectory, so no
further searching can overturn it. It is not vacuous, since the two ends sit
0.0065 apart and a threshold anywhere outside that band is decided. And it is
conditional on the observer, the coefficient and the ceiling, which have to
travel with it.

Every figure in that subsection is a macro from the results, including the
quotable threshold. That last one is computed rather than chosen: the bound
says nothing exceeds it, so any strictly larger value may be stated as
unreachable, and the tool rounds up to two places and then checks the result
is strictly above the bound. A threshold equal to the bound would claim more
than is proved.

The worked example and the figure were on different ceilings, 1.25 against
1.50, which would have put the same world's different numbers a page apart.
They are both 1.50 now, which is also the tightest interval in the suite and
the case where the witness beats the search by the largest margin.

## Sections III and IV rewritten, 6 August 2026

Both described the objective and the bound in words without stating either,
which for a paper whose contribution is the bound is the wrong way round. The
objective is now equation (2), the reachability conditions are (3), and the
bound itself is (4), so a reader can check the argument rather than take it.

Three things that were asserted are now shown. The cancellation of duration is
visible in the second equality of (2) rather than claimed in a sentence. The
detour argument, which was one sentence carrying a four step proof, is broken
into the three facts that compose. And the reason the precondition is decided
per cell rather than per world is given as the failure it prevents, that a
polygon with a sharp vertex can be many cells wide overall while its tip is
thinner than one, so a whole-world test would certify cells the argument does
not cover.

Still four pages. The sections got clearer rather than longer, which is what
was wanted, and the two pages that remain are for whatever a reader turns out
to need rather than for filling.

## The figure, 6 August 2026

`tools/build_paper_figures.py`, written to `paper/generated/mechanism.pdf`.
`wall_choice` at ceiling 1.5, drawn from the same lattice, the same reachable
sets and the same witness the bound is computed from, so the figure and the
tables cannot disagree.

It shows the belief field as shading, the reachable set at the half way point
as an outline, the shortest path, and the witness. The set has two parts,
because the wall can be passed on either side, and that turned out to be the
most informative thing in the picture: the shortest path takes the upper one
and reads ambiguously for most of its length, while the witness takes the
lower one.

Three decisions worth recording, since a figure has constraints prose does
not.

- The belief is a magnitude, so it takes one hue running light to dark with a
  scale legend. A multi-hue ramp would put magnitude in a channel that does
  not order.
- Identity never rests on colour. IEEE is read in print and in greyscale as
  often as on a screen, so the three curves separate by line style and weight
  first and survive with every colour removed.
- Fonts are embedded as TrueType. Matplotlib writes Type 3 into a PDF unless
  told otherwise and publishers commonly refuse it, which is why `make check`
  fails on a Type 3 font.

**The figure carries a check.** The witness is an admissible trajectory, so
its own half way point has to lie inside the set drawn as reachable at half
way. The tool computes that point, tests it against the set, and refuses to
draw anything if it fails. A figure that would have shown the witness escaping
its own bound now stops the build instead.

That marker was added because the first version looked wrong. The witness
leaves the outlined region for most of its length, which is correct, since the
region constrains only where a trajectory may be at one moment. Drawn without
the marker it read as a contradiction. Two earlier versions were worse: three
reachable sets at once, which rendered as overlapping circles with no legible
shape, and a legend sitting directly on top of the witness.

## The survey changed the paper's claim, 6 August 2026

Four papers read in the body, four in the log. The one that mattered is Miura
and Zilberstein, UAI 2021, which unifies legibility with explicability and
predictability as observer-aware MDPs and establishes the complexity of the
result: PSPACE-complete for a Bayesian observer, and NP-hard even restricted
to stationary policies or deterministic environments.

The draft had argued that the field optimises and nobody decides, which reads
as though computing the optimum had not been attempted. That is wrong, and a
reviewer in this area would know it on sight. The optimum is intractable, and
that is exactly why a two-sided bound is worth having. The introduction and
the related work were rewritten around the hardness result rather than around
an absence, and the paper is stronger for it: the contribution is no longer
"nobody tried" but "the optimum is out of reach, so bracket it".

It also narrows what may be claimed. Optimality is computable in discretised
stochastic formulations, up to the discretisation, so the claim here is
specifically about the continuous trajectory setting with exact cost-to-go and
a stated path cost budget. The paper now says that.

This is the second time today that a search for prior work changed a claim
rather than decorating it, and it is the argument for doing the reading before
the writing rather than after.

## The survey narrowed the safety claim too, 6 August 2026

Two more bodies read, six in total, and the second of them corrected the other
headline claim.

**Bastarache, Nielsen and Smith, ICRA 2023.** They plan for legibility among
moving agents and report minimum pairwise distance alongside it, plus minimum
time-to-collision, which in their own words they use "as a proxy for legibility
and safety". The draft had implied that safety goes unreported beside
legibility, resting on the founding paper's observation that the interaction is
identified and not measured. True of that paper, false of the literature, and a
reviewer working on social navigation would have spotted it at once.

The claim is now the narrower thing it actually is, and all three parts of it
survive: the safety quantity here is satisfaction of a stated static constraint
rather than proximity to a moving agent, it is bounded over all admissible
trajectories rather than measured on the ones a planner produced, and the two
together give a price that is certified rather than compared.

That narrowing was recorded in the sibling repository's notes and has now been
verified here independently rather than inherited, which is the second time
today that order has mattered.

**Amirian, Abrini and Chetouani, RO-MAN 2024.** Cited for one thing: legibility
built into cost-based local motion planning for real-time use. It is evidence
that the continuous setting still reaches for local optimisers, which is the
right instrument for driving a robot and not one that can decide a negative
statement about a world.

**Two of the six papers changed a claim rather than supporting one.** That is
the whole argument for reading bodies before writing prose rather than after.

**What is still not covered**, and the paper says so in its own text:
learning-based legibility, recent generative methods, and legibility in
sequential decision tasks beyond the observer-aware line. A scoping review of
motion intent communication was fetched and deliberately not cited, since it
covers signalling modalities such as projection and light rather than the
motion objective bounded here.

**One dash survives and it needs a decision.** `references.bib` carries the
page range `301--308`, which is the BibTeX convention and which `IEEEtran.bst`
typesets as an en dash. It is the only one left anywhere in `paper/` or in the
generating tool. The standing rule against dashes is unambiguous, and IEEE's
own style expects a range dash in a bibliography, so the two are in conflict
in exactly one place. It is left as the convention until decided, and it is
recorded here rather than passed over.

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
