# Citation verification log

Every citation's bibliographic details are confirmed against public records,
and every finding attributed to a paper is checked against that paper's body
rather than its abstract. Both checks are dated here. A claim that could not
be checked is not made in the paper.

## Dragan, Lee and Srinivasa, HRI 2013

**Bibliographic details, checked 6 August 2026.** "Legibility and
Predictability of Robot Motion", Anca D. Dragan, Kenton C. T. Lee and
Siddhartha S. Srinivasa, Proceedings of the 8th ACM/IEEE International
Conference on Human-Robot Interaction, 2013, pages 301 to 308. Confirmed
against the ACM Digital Library record and the authors' institutional
repository.

**Body read 6 August 2026**, from the copy at
`publications.ri.cmu.edu/storage/publications/pub_files/2013/3/legiilitypredictabilityIEEE.pdf`.
Four claims checked, all four supported.

- The legibility functional. Equation (9) averages the observer's posterior in
  the true goal along the trajectory under a weight `f(t)`, divided by the
  integral of that weight. The paper gives `f(t) = T - t` as its example, with
  `T` the duration, and states the purpose as "more weight being given to the
  earlier parts of the trajectory". This is the objective this work bounds,
  unchanged.
- Legibility cannot reach one. In the paper's own words, "In situations with
  multiple possible goals, a robot can make trajectory more and more legible,
  never reaching a score of 1, and increasing the cost w.r.t. to C more and
  more." A score near one is therefore not a proportion of an attainable
  ideal, and must never be worded as one.
- A bound on cost is theirs, not ours. Immediately after the sentence above,
  the paper adds a regulariser, equation (10), `L = legibility - lambda C`,
  with the stated reason "To prevent the robot from going too far away from
  what the observer expects". Our cost ceiling is the same idea in hard form
  and is cited as such.
- Legibility moves motion towards obstacles. Figure 8 is captioned "Legibility
  is not obstacle avoidance", and the body states that a legible trajectory
  "still exaggerates motion away from the other candidate objects even in if
  it means getting closer to a static obstacle like a counter or a wall". The
  phenomenon is identified there and not measured. That is what makes the
  safety-constrained bound worth stating.

## Dragan and Srinivasa, RSS 2013

**Bibliographic details, checked 6 August 2026.** "Generating Legible Motion",
Anca Dragan and Siddhartha Srinivasa, Proceedings of Robotics: Science and
Systems IX, Berlin, Germany, June 2013, DOI 10.15607/RSS.2013.IX.024.
Confirmed from the official proceedings entry, which publishes the BibTeX
record directly.

**Body read 6 August 2026**, from `roboticsproceedings.org/rss09/p24.pdf`.
Three claims checked, all three supported.

- The trust region is a hard constraint on cost. Equation (13) maximises
  legibility subject to `C[xi] <= beta`, described as "constraining the
  trajectory to stay below a maximum cost in C during the optimization".
- The model has a stated domain of validity. The paper says in as many words:
  "The legibility model can only be trusted inside this trust region." This is
  why no result here is reported without a ceiling, and why an unbounded
  figure is a diagnostic rather than a result.
- The observer's belief set is known to be incomplete. The paper states that
  observers "might get confused by the robot's behavior and stop reasoning
  about the robot's possible goals the way the model assumes they would", and
  "might start believing that the robot is malfunctioning or that it is not
  pursuing any of the goals", adding that this is supported by their user
  studies. Their follow-up study measures a quantity labelled "Belief in
  Neither Goal" directly. Our observer cannot represent that belief, since its
  posterior sums to one over the declared goals however strange the motion
  becomes, and the limitations section says so.

This claim was carried into this project from a sibling repository's notes and
was repeated in a draft before it had been checked here. It is checked now and
it holds, but the order was the wrong way round.

## What has not been checked

The related work covers the founding formulation and nothing else. No survey
of subsequent legibility work has been done, and no claim is made in the paper
about what that work does or does not establish beyond the two papers above.
Any sentence positioning this work against a broader literature is therefore
still to be written, and is not to be written from memory.
