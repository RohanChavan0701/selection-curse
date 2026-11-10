# I went looking for reward hacking in a self-improving agent. I found it fooling itself instead.

*Draft for the author to edit into his own voice. Numbers are from run 7 of this repository unless stated. FinQA is a public dataset
and may be in the student model's pretraining data; everything here is one small student,
one judge model and one benchmark.*

## The setup everyone worries about

Take an agent. Let a loop rewrite its harness: the system prompt, the rules, a few settings.
Score each rewrite, keep the best, repeat. That is the cheap, practical form of recursive
self-improvement, and it is how a lot of agent tuning already works.

The catch is the score. In most real tasks nobody has labels, so the loop asks another model
to judge the answers. The obvious fear follows: the loop will stop making the agent better
and start making the judge happier. Confident tone, long explanations, "I have verified
this". Reward hacking, with nobody in the loop to notice.

I wanted to catch that happening and measure it. I did not catch it. What I measured instead
is less dramatic and, I think, more useful.

## What I built

A 7B model answers numeric questions about pages from company financial reports. It has a
calculator tool and a submit tool. I can grade it exactly, because the dataset has the right
numbers.

I wrote 40 single edits to its harness by hand, in five groups: placebos ("Read the
question."), style edits that should change how an answer sounds but not whether it is
right, substance edits about how to compute, structural changes like more steps, and a group
written specifically to please a judge.

Each edit ran on 300 questions. Every transcript was graded four ways: by the true answer,
by an LLM judge that sees the reference answer, and by two LLM judges that do not. One of
those recomputes the answer before deciding. The other just gives a verdict.

With that table stored, I can replay a self-improvement loop as often as I like without
calling a model: draw 8 candidate edits, pick the winner on 150 questions using one of the
four graders, then check the winner on the other 150 with the true answers. The gap between
what the loop would have reported and what was real splits into three parts:

- **real gain**: the edit actually helps;
- **judge bias**: the judge likes the edit more than the truth does, on fresh questions too;
- **noise**: the edit got lucky on the questions it was picked on.

Reward hacking is the second part growing under selection. That is the thing I was hunting.

## What happened

![Reported versus real gain](../figures/run7_selection.svg)

**The loop inflates its own number even with perfect labels.** Selecting on true answers,
the winner reported +5.1 points and was really worth +2.4. No judge involved. Pick the best
of eight noisy measurements and the best one is partly best by luck. This is the winner's
curse, it is old statistics, and a recent paper measured it in LLM self-improvement loops
(arXiv 2610.09239). It is easy to treat as a rounding error. Here it was half the reported
gain.

**A judge makes it somewhat worse.** With the reference-free judge that recomputes answers,
the reported gain rose to +5.8 while the real gain stayed at +2.3. The curse was 1.36 times
larger than with labels.

I should be straight about how solid that is. I pre-registered a prediction that the
multiplier would be between 1.3 and 2.0 with a confidence interval clear of 1.15. The point
estimate was 1.36, at the bottom of my range, and the interval was 1.06 to 1.82. That is
neither a pass nor a fail by the rule I wrote down beforehand. The exploratory run before
it had suggested 1.6 to 1.7. It shrank when I tested it properly, which is what
exploratory numbers do.

**A formula predicts the size.** The extra curse should equal the square root of the ratio
between the judge's per-question noise and the noise of true labels. That predicted 1.37.
Observed: 1.36.

**The worst judge had the smallest curse.** The verdict-only judge agreed with the truth on
62% of answers, the worst of the three. It also approved 88% of everything. Its curse was
about two thirds of the curse with perfect labels (multiplier 0.64, interval 0.49 to 1.08). The reason is the formula: a judge that says yes to nearly
everything has scores that barely vary, so there is little luck for selection to pick up.
Accuracy and stability are different properties, and a near-useless judge can look like a
calm, trustworthy one.

**No reward hacking.** The judge-selected winner carried +0.7 points more judge bias than a
randomly chosen edit, with an interval of -0.8 to +2.1. Selection did not concentrate
judge-pleasing. It concentrated luck.

**And the judge chose well.** The edit picked by the judge was as good in reality (+2.3) as
the edit picked by true labels (+2.4). I had predicted the judge's pick would be worthless.
That prediction was wrong.

## What I got wrong along the way

My first judge prompt was nearly useless and I did not know. It approved 95% of right
answers and 88% of wrong ones. The loop ran, the numbers looked plausible, and nothing
complained. I only saw it because I had true answers to compare against, which is exactly
what a label-free loop does not have. I now check a judge against a small labelled sample
before trusting anything it selects.

My first analysis also blamed the judge for too much. A bug in how I split the gap counted
the judge's luck as bias, and for a while the result read "almost all reward hacking".
It was the opposite.

And the question I started with, whether a loop becomes a reward hacker when it runs out of
real improvements, I could not test. My edits never ran out in the way I needed.

## What I would tell someone running one of these loops

1. **Re-score the winner on questions it was not chosen on.** This removes the curse
   completely and costs one extra evaluation. It matters with labels and more with a judge.
2. **A reported gain of a few points from best-of-k is not evidence of anything.** The curse
   is a fixed number of points set by how many candidates you try and how many tasks you
   score on. Large real gains swamp it. Small ones are swamped by it.
3. **Check your judge against truth on a small sample first.** A judge can be near chance and
   still produce a tidy, stable-looking loop.
4. **Do not read stability as quality.** The calmest judge in this experiment was the worst.

## What this does not show

It does not show that loops cannot learn to game a judge. My edits were written by hand, and
a hand-written style tweak is a weak attacker. The stronger test is an LLM proposer told
outright to raise the judge's approval without making answers better. That is built and has
not been run. It is the next experiment, and I have written this before knowing its result.

It is also one 7B student, one 8B judge and one public benchmark that the student may have
seen. The primary pre-registered result was inconclusive. I would not generalise the numbers.
I would generalise the habit: when a loop tells you it improved itself, ask what it measured
that on.

*Code, frozen configurations, the predictions as committed before the run, and every
deviation: [github.com/RohanChavan0701/selection-curse](https://github.com/RohanChavan0701/selection-curse).*
