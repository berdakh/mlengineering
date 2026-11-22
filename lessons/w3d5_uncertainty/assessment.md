# W3D5 assessment

Write answers before opening `solutions/lessons/w3d5_uncertainty/assessment_answers.md`.
Two to five sentences each unless stated.

## Reasoning questions

**Q1.** A test set has 12,000 rows from 10 experiments. A colleague bootstraps rows and reports
"F1 = 0.812 ± 0.006". Without rerunning anything, what is wrong, in which direction, and what is the
smallest change to the procedure?

**Q2.** Your cluster-bootstrap interval for recall on 7 clusters is [0.71, 0.93]. Give two separate
reasons why the true 95% interval is probably wider, and one reason an interval of any width could
still mislead.

**Q3.** Model A: PR-AUC 0.83 [0.76, 0.90]. Model B: 0.80 [0.73, 0.87]. Same 30 test experiments.
A reviewer says "the intervals overlap, so there is no difference". Respond, and name the one extra
number that would settle it.

**Q4.** Eight of eight held-out fault events were detected. A stakeholder wants to write "100%
detection". What do you write instead, and how do you explain it in one sentence to a non-statistician?

**Q5.** You train a small neural detector with five seeds and get test PR-AUC 0.84, 0.86, 0.81,
0.87, 0.85. The deterministic baseline scores 0.84. Which statements are supported: (a) the neural
model is better; (b) the neural model is at least as good; (c) a seed can be found that beats the
baseline; (d) none without more analysis? What would you run next?

**Q6.** You compare six candidate detectors against the baseline, each with a paired test at
α = 0.05, and one comes out at p = 0.03. How strong is this evidence? Give the probability of at
least one such result if none of the six is truly better (assume independence), and one remedy.

## Design-choice explanation

**Q7.** (8-10 sentences.) In the lab the unit of resampling for SKAB was the *overlap group* and the
test-set threshold was *frozen* inside the bootstrap. Defend both choices to a sceptical colleague.
For each, describe what quantity you would be estimating if you did the opposite, and whether that
quantity is ever the one you want.

## Rubric (Q7 and open answers)

| Criterion | Not yet | Adequate | Strong |
|---|---|---|---|
| Unit of independence | Says "experiments" without reason | Explains shared rows / dependence | Connects to the sampling process being imitated and to what a new deployment would draw |
| Frozen threshold | Not addressed or "for speed" | Threshold is part of the model being evaluated | Also names the alternative estimand (procedure-level variability) and when it is relevant |
| Limits | None stated | Mentions few clusters | Quantifies (undercoverage with 7; minimum detectable difference) and separates sampling error from bias |
| Decision | Statistic only | States what can be claimed | States what would be done differently because of the uncertainty |

## Interview rep (10-15 minutes, spoken or written; strand: ML fundamentals / statistics)

> "We A/B-evaluated two anomaly detectors offline. On our test set of 50,000 one-second windows from
> 20 machines, detector B has precision 0.912 and detector A 0.904. Is B better? Walk me through
> what you would check and compute. You have per-window predictions and labels for both, with a
> machine id."

Conditions for this week (weeks 3-5): timed, 12 minutes; write a second attempt before reading the
worked answer. The rubric is in the solutions file.

Then, from memory and without running it, write a paired cluster bootstrap for the difference in
precision in at most 15 lines of NumPy. State one edge case your code must handle.
