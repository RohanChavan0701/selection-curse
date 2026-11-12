# Run 9 replay: does re-measuring the incumbent unfreeze the loop?

Status: PREDICTIONS COMMITTED 2026-11-12, before the replay code was run. Exploratory: this
uses run 9's data after its outcome and its post hoc stall analysis were known, so it is not a
confirmatory test. No GPU, no new model calls.

## Question

Run 9's red-team loops stopped after round 1. The post hoc reading (`PREDICTION_run9.md`,
"Post hoc") is that a lucky round 1 winner set a bar its descendants could not reach. If so,
an acceptance rule that compares the round's best candidate with the incumbent on data
neither was picked on should replace more often and keep better harnesses.

## Data

The per-task grades already on disk for run 9: the anchor (3 repeats, averaged per task) and
every scored candidate of the 12 selected loops (J-red, J-honest, T; 5 rounds, 5 candidates),
on the 150 selection tasks. The random arm's candidates were never run and are not used.

## Replay

1,000 random splits of the 150 selection tasks into three disjoint parts: A (60 tasks, used
to pick the round's best candidate), C (40 tasks, used to confirm) and B (50 tasks, used only
to evaluate). Each loop is replayed round by round on its realized candidates, with its arm's
selector (judge approval for J-red and J-honest, accuracy for T). The incumbent starts at the
anchor. Three acceptance rules:

- **REG** (as run 9): pick the best candidate on A; replace if its A score beats the
  incumbent's A score. A tie keeps the incumbent.
- **CONFIRM**: pick the best candidate on A; replace if its C score beats the incumbent's C
  score. A tie keeps the incumbent.
- **POOLED**: pick the best candidate on A and C together (100 tasks); replace if it beats the
  incumbent on A and C together. Same data as CONFIRM, without the hold-out.

Per loop and split, for the harness each rule ends with:

- held-out gain: its accuracy on B minus the anchor's accuracy on B;
- reported gain: its selector score minus the anchor's, on the data the rule last accepted it
  on (A for REG, C for CONFIRM, A and C for POOLED);
- inflation: reported minus held-out gain (both in the selector's own units for T; for the
  judge arms reported is in approval and held-out in accuracy, so inflation there also
  contains judge bias);
- replacements in rounds 2 to 5.

Results are means over splits, per arm, and pooled over the 8 judge-selected loops.

## Predictions (exploratory, low confidence)

- **P1.** In the judge-selected loops, CONFIRM ends with a higher held-out gain than REG, by at
  least 0.5 points.
- **P2.** In the T arm, CONFIRM's inflation is smaller than REG's, and within 1 point of zero.
- **P3.** CONFIRM's held-out gain is within 1 point of POOLED's in every arm: holding out data
  for confirmation costs little.
- **P4.** Under REG, judge-selected loops replace less often in rounds 2 to 5 than T loops do
  (the task-split replay reproduces the shape of the stall).

## Limits, stated before running

- Decision-level replay, not a re-run. The candidates of round r were written as edits of
  the incumbent run 9 actually had. Under a different rule the loop would have had a
  different incumbent and the proposer would have written different candidates.
- The noise here is task sampling (which 60 tasks are in A). The stall in run 9 came at
  least partly from run-to-run noise (the same harness on the same tasks), which cannot be
  replayed: no candidate was run twice.
- 50 evaluation tasks give a single harness a standard error of about 7 points; the means
  over 1,000 splits and 4 or 8 loops are much steadier, but splits share tasks, so no
  interval from them is reported as if independent.
- 4 loops per arm.
