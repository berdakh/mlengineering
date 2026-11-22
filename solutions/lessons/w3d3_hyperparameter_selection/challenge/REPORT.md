# Challenge report (w3d3) - reference

All numbers are from the shipped SYNTHETIC table (`challenge/trials.csv`, generator seed 2026) and
from runs of `selection_rule.py` and `optimism.py` in this directory.

## Procedure

One-standard-error rule: take the trial with the highest mean over the five recorded folds
(trial 54, mean 0.7495), compute the standard error of *its* fold scores, and among all trials
whose mean lies within one standard error of that best mean choose the one with the fewest
parameters. The rule fits this table because the 60 dev means are packed into a few hundredths
while a single mean has a standard error of roughly 0.01-0.02: most of the ordering among the top
trials is noise, so the tie is broken by something that is not noise (model size). On this table the
rule happened to return the top trial itself, trial 54: no simpler trial was inside the band.

## What I expect on test, before looking

**0.736.** Computed without the test scores: for each fold k the whole rule was rerun on the other
four folds and the trial it selected was read off on fold k; the five readings were averaged. The
chosen trial's own dev mean (0.7495) is not used, because that number is the reason the trial was
chosen: it is the largest (or near-largest) of 60 noisy numbers and is too high on average.
Over 200 generated tables this nested estimate is off by +0.0006 on average for the reference
procedure, the chosen trial's own dev mean by +0.0155, and the top trial's dev mean by +0.0257.

## The one look

Trial 54, test score **0.7083**: 0.027 below the estimate and 0.041 below its dev mean. That is a
large miss for one table but not an implausible one. The nested estimate averages five fold
readings and so inherits the shared fold effects of these particular folds (s.d. about 0.02 per
fold in the generator, about 0.009 after averaging) plus trial noise; the test score has its own
sampling error (about 0.012). An honest estimator is unbiased over many tables, not accurate on
each. The log (`test_looks.json`) shows one look. I did not look at any other trial, and I am not
changing the choice.

## Optimism simulation

Expectation written first: the optimism grows like sqrt(log K), so going from 5 to 200 candidates
should roughly double it, not multiply it by 40; and correlation rho between the candidates' errors
should shrink it by sqrt(1 - rho), because the shared part of the error moves all candidates
together and cannot change which one is on top.

| K | rho = 0 | rho = 0.5 | rho = 0.9 | sigma*sqrt(2 ln K) |
|---|---|---|---|---|
| 5 | 0.0233 | 0.0165 | 0.0074 | 0.0359 |
| 20 | 0.0374 | 0.0264 | 0.0119 | 0.0490 |
| 60 | 0.0464 | 0.0328 | 0.0147 | 0.0572 |
| 200 | 0.0549 | 0.0388 | 0.0174 | 0.0651 |

(sigma = 0.02, 40,000 repetitions, seed 0.) Both expectations hold: 0.0549 / 0.0233 = 2.4, and the
ratios to the independent column are 0.71 and 0.32 against sqrt(0.5) = 0.71 and sqrt(0.1) = 0.32.
The bound is never reached at these K.

## What I would not conclude

* That the one-SE rule is "better" than taking the maximum. On the 200 generated tables the two pick
  trials of nearly the same true quality (0.7183 against 0.7177); the gain is in the honesty of the
  accompanying number and in model size, and it depends on the generator's assumption that complex
  trials are noisier.
* Anything from a single table. One look gave a miss of 0.027; that neither confirms nor refutes the
  procedure.
* That real search results behave like this generator. Real trials are correlated through shared
  folds, shared hyperparameters and shared bugs, and their true scores are not exchangeable.
