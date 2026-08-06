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

## Miura and Zilberstein, UAI 2021

**Bibliographic details, checked 6 August 2026.** "A Unifying Framework for
Observer-Aware Planning and its Complexity", Shuwa Miura and Shlomo
Zilberstein, Proceedings of the Thirty-Seventh Conference on Uncertainty in
Artificial Intelligence, Proceedings of Machine Learning Research volume 161,
pages 610 to 620, 2021. Confirmed from the PMLR record, which publishes its
own BibTeX.

**Body read 6 August 2026**, from the PMLR copy. This paper changed the
framing of the whole section and of the introduction, which is the reason to
run a survey rather than write from memory.

- Observer-aware behaviours, legibility among them, are unified as MDPs in
  which the property is a choice of reward over the observer's belief. The
  paper's own summary of legibility cites Dragan and Srinivasa alongside
  others, so this is the same notion rather than a different one.
- The complexity is established rather than assumed. In the paper's words,
  the problem is "PSPACE-complete (Theorem 1 and 2)" for a Bayesian observer
  and "remains NP-hard even when restricted to stationary policies or
  deterministic environments (Theorem 3)", which "confirms the intractability
  of the problem".

**What this changed.** The draft had said that the field optimises and that
nobody decides, which reads as though computing the optimum had simply not
been attempted. That is wrong and a reviewer in this area would know it. The
optimum is intractable, and that is precisely why a two-sided bound is worth
having. Both the introduction and the related work were rewritten around the
hardness result rather than around an absence.

It also bounds what this paper may claim. Optimality is computable in
discretised stochastic formulations up to the discretisation, so the claim
here is specifically about the continuous trajectory setting with exact
cost-to-go and a stated path cost budget, and is written that way.

## Lepers, Thomas and Buffet, AAMAS 2025

**Bibliographic details, checked 6 August 2026.** "Observer-Aware
Probabilistic Planning under Partial Observability", Salom{\'e} Lepers,
Vincent Thomas and Olivier Buffet. The arXiv record 2502.10568, version 2 of
20 November 2025, describes itself as the complete version of an AAMAS 2025
extended abstract, and a paper of that title appears in the AAMAS 2025
proceedings.

**Body read 6 August 2026.** Cited only as a partially observable extension of
the observer-aware line. No finding is attributed to it beyond that it extends
observer-aware MDPs to partial observability, which its abstract and body both
state. Its solution method computes approximately optimal policies for a
discretised problem, which is consistent with the framing above.

## Bastarache, Nielsen and Smith, ICRA 2023

**Bibliographic details, checked 6 August 2026.** "On Legible and Predictable
Robot Navigation in Multi-Agent Environments", Jean-Luc Bastarache,
Christopher Nielsen and Stephen L. Smith, Proceedings of the IEEE
International Conference on Robotics and Automation, London, 2023, pages 5508
to 5514, DOI 10.1109/ICRA48891.2023.10160572. Confirmed against the authors'
institutional copy and the IEEE record.

**Body read 6 August 2026**, from the copy at
`ece.uwaterloo.ca/~sl2smith/papers/2023ICRA-Legible_and_Predictable.pdf`. This
one narrowed a claim, which is why it was sought out.

- Legibility is planned for among moving agents, with interactions modelled as
  dynamic goal regions rather than as static goal points.
- Safety quantities are reported alongside legibility. The paper reports the
  minimum distance to other agents, and in its own words, "As a proxy for
  legibility and safety, we also report the minimum time-to-collision (TTC)."

**What this changed.** The draft implied that safety goes unreported beside
legibility, resting on the observation in the HRI paper that the interaction is
identified and not measured. That was true of the founding paper and false of
the literature, and a reviewer working on social navigation would have known
it immediately.

The claim is now stated as the narrower thing it is. What is new here is that
the safety quantity is satisfaction of a stated static constraint rather than
proximity to a moving agent, that it is bounded over all admissible
trajectories rather than measured on the ones a planner produced, and that the
two together give a price that is certified rather than compared. All three
survive this paper; the unqualified version did not.

This claim came into the project from a sibling repository's notes, which had
recorded the same narrowing. It is verified here independently rather than
inherited.

## Amirian, Abrini and Chetouani, RO-MAN 2024

**Bibliographic details, checked 6 August 2026.** "Legibot: Generating Legible
Motions for Service Robots Using Cost-Based Local Planners", Javad Amirian,
Mouad Abrini and Mohamed Chetouani, IEEE International Conference on Robot and
Human Interactive Communication, Pasadena, 2024. Also arXiv:2404.05100.

**Body read 6 August 2026.** Cited for one thing only, which the paper states
plainly: legibility is incorporated into cost-based local motion planning so
that a mobile robot can generate legible motion in real time. It is evidence
that the continuous setting still reaches for local optimisers, which is the
right instrument for driving a robot and not one that can decide a negative
statement about a world. No other finding is attributed to it.

## Liu, Pan, Zeng, Ma and Doshi, arXiv 2024

**Bibliographic details, checked 6 August 2026.** "Active Legibility in
Multiagent Reinforcement Learning", arXiv:2410.20954v1, submitted 28 October
2024. The arXiv record lists no journal reference, so it is cited as a
preprint rather than as a published paper.

**Body read 6 August 2026.** Cited for one thing, which it states in its own
contributions and devotes a section to: it gives a convergence and
completeness analysis for its multi-agent legibility algorithm.

**What this changed.** The paper had said nothing about guarantees existing
elsewhere in this literature, which left the word "certified" sounding like a
claim that nothing in legibility is guaranteed. That is false. What is true is
narrower and is now stated: a convergence result is a guarantee about an
algorithm reaching what it converges to, and this paper's bound is a guarantee
about what any trajectory could achieve. Two different objects, and the paper
now says which one it means.

The same paper refers to PoLMDP, an extension of legibility to sequential
decision tasks under uncertainty. That work is behind a paywall and its body
was not read, so no finding is attributed to it and it is not cited. A
second-hand account of a paper is not a check of it.

## Shi, Grislain, Sigaud and Chetouani, arXiv 2025

**Bibliographic details, checked 6 August 2026.** "Controlling Intent
Expressiveness in Robot Motion with Diffusion Models", arXiv:2510.12370v1,
submitted 14 October 2025. No journal reference listed; cited as a preprint.

**Body read 6 August 2026.** Cited for two things it states plainly: existing
approaches usually produce a single most legible trajectory, whereas it
generates motion across a controllable range of intent expressiveness; and it
scores legibility with an Information Potential Field of its own construction
rather than with the formulation bounded here.

**What this changed.** The second point matters more than the first. There is
no single legibility in this literature, and a bound on one formulation says
nothing about another. The paper now states that it bounds the objective of
Dragan et al. and nothing else, which is a scoping the draft had left implicit.

## What has not been checked

Eight papers have been read in the body: the two founding papers, two on
observer-aware planning, one on legibility beside safety, one recent
continuous-setting planner, one learning-based treatment and one generative
one. That covers the founding formulation, the line that establishes the
problem's complexity, the state of continuous-setting planning, the closest
prior treatment of legibility beside safety, and the two families the earlier
draft admitted to ignoring.

Specifically not read, and therefore not cited: PoLMDP and the wider
sequential-decision legibility line, which is paywalled. A scoping review of
motion intent communication was fetched and not used, because it covers
signalling modalities such as projection and light rather than the motion
objective bounded here, and citing it would have implied a survey of a
literature this paper does not engage with.

Four of the eight changed a claim rather than supporting one: the hardness
result reframed the contribution, the safety paper narrowed it, the
learning-based paper forced the word "certified" to be qualified, and the
generative paper forced the objective to be scoped. That is the argument for
reading bodies rather than abstracts, and for doing it before the prose rather
than after.
