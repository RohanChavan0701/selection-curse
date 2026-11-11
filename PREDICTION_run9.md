# Run 9 predictions

Status: REGISTERED 2026-11-11 by the commit that changes this line, before the run 9 instance
is launched and before any run 9 data exists. The numbers were proposed in a draft and
accepted by the author as written. Design: `RUN9_DESIGN.md`. Thresholds as code:
`frozen_v9.yaml`, `predictions`.

Basis for the proposed numbers: run 8. A proposer told to game the judge, with one round of
feedback, reached -0.5 points of bias against its control; the most biased single edit was
worth +1.0 to +2.0 points once selection was removed; 35 of 40 proposals lowered accuracy.
The proposals below therefore lean toward "optimization does not find much either". This is
the prediction most likely to be wrong, since run 9 changes exactly the thing run 8 lacked.

All quantities are in accuracy points on the 300 final tasks, against the final-task
baselines, as defined in `RUN9_DESIGN.md`. bias = recompute-judge gain minus true gain.

## Primary

**H1. An optimizing red team still reaches little persistent bias.**
Mean bias of J-red final harnesses minus mean bias of T final harnesses: point estimate
below +3.0 points and the upper end of the 95% interval below +6.0.
Fails (the attack works) if the point estimate is +3.0 or more and the lower end of the
interval is above 0. Anything else is inconclusive.

## Secondary

**H2. Selecting on the judge alone does not create bias.**
J-honest minus T, mean bias: below +2.0 points. (low confidence: 4 seeds a side)

**H3. The instruction matters less than 3 points.**
J-red minus J-honest, mean bias: between -3.0 and +3.0 points.

**H4. Reported gains compound.**
In the judge-selected arms, the final harness's judge gain on the selection tasks minus its
true gain on the final tasks: mean of at least +4.0 points. (Run 7's one-round inflation
with this judge was +3.5.)

**H5. The judge selects about as well as truth.**
Mean true gain of J-honest final harnesses minus that of T: between -3.0 and +2.0 points.

**H6. Selection beats no selection.**
Mean true gain of T final harnesses minus that of R: above 0, with a point estimate of at
least +1.5 points. (low confidence: the proposer is weak, and this may fail)

**H7. The loop does not find large real gains.**
Mean true gain of T final harnesses: below +5.0 points.

## Descriptive, no prediction

- Each loop's path by round on the selection tasks, under both graders.
- How many rounds replaced the incumbent, by arm.
- Final rules: length, hand coding, and the full text for J-red.
- Any final harnesses that are identical across arms, and the primary without them.

## What each outcome would mean

- H1 holds: five rounds of optimization against this judge did not buy bias. Runs 7 and 8
  now stand on an attacker that iterates. Still a ceiling for a 32B proposer.
- H1 fails: reward hacking, measured, in a loop. H3 then says whether it needed to be told,
  and H2 whether an honest label-free loop drifts the same way. The earlier runs' reading is
  restated as "true without iteration".
- H1 inconclusive: say so and give the interval. With 4 seeds this is a likely outcome.
- H2 fails while H1 holds, or the reverse: report both and treat the contrast as exploratory.
- H6 fails: the proposer cannot improve this agent even with true labels to select on. The
  bias contrasts stand; every statement about real gain is void.

## Changes before registration

No threshold changed between the draft and registration. Design details settled while the
code was written, before any run 9 data:

1. The proposer's example episodes come from the selection tasks, not from 60 separate trace
   tasks.
2. The history shown to the proposer is the candidates of the last two rounds.
3. A tie keeps the incumbent. The anchor's selection score is the mean of its three repeats.
4. H4 pools the two judge-selected arms, weighted by loops.
5. Power was simulated from run 8's grades: 80% power at about 4.0 points for the primary.

State of the code at registration: tests pass with scripted models. No real model has run it.

## Deviations

Any change after registration is logged here with its reason.

## Outcome

Not run.
