# w2d6 - model answers

## Reasoning questions

**1.** precision = πr / (πr + (1−π)f). At π = 0.30: 0.27 / (0.27 + 0.014) = **0.951**. At π = 0.001:
0.0009 / (0.0009 + 0.01998) = **0.043**, about 22 false alarms per true one. ROC AUC is unchanged:
it is built from recall and FPR, each a rate *within* one true class, so the class ratio cancels.
Average precision changes (and so does its floor, 0.30 versus 0.001) because precision mixes the two
classes in proportion to their sizes.

*Common incorrect answers.* "Precision stays 0.9-ish because the classifier is the same": confuses
recall with precision. "ROC AUC drops because the problem got harder": the ranking problem did not
change. "Average precision is unaffected because it is threshold-free": threshold-free is not
prevalence-free.

**2.** A constant score flags every row at any threshold it can reach, so recall = 1 and precision =
π. F1 = 2π / (1 + π) = 0.746 / 1.373 = **0.544**. With 37 % positives, F1 has a free floor of 0.54:
"F1 = 0.6" is barely above doing nothing, and F1 values on SKAB cannot be compared with F1 values on a
benchmark with 1 % positives (floor 0.02).

*Common incorrect answers.* "The floor of F1 is 0" (true only as π → 0). "0.544 means it found half
the anomalies" (it found all of them and half-drowned them).

**3.** 31 of the 34 experiments start their single anomalous segment between t = 550 and 600 (median
572); the dev-selected threshold is t ≥ 572. Flagging "everything after the usual onset time" catches
nearly every anomalous row (recall 0.99). Precision is 0.72 because the anomaly usually *ends*
(median t ≈ 970) while the recording continues to about t ≈ 1,140, so the late rows are false alarms.
PR-AUC is poor for the same reason: ranking by t puts those late normal rows at the very top of the
list, so precision is low exactly where average precision weights it first. A learned model can find
the clock through (a) anything that drifts monotonically during a run, such as motor or fluid
temperature warming up, cumulative or long-window features, an explicit time or position feature;
(b) sequence position itself in a recurrent or attention model, or window index. This is a protocol
regularity, not physics: a deployed detector does not get faults on a schedule.

*Common incorrect answers.* "The clock is a strong baseline we should build on" (it is a leak
detector; its success is a property of how SKAB was recorded). "PR-AUC shows it is useless, so
ignore it" (the F1 it reaches at one threshold is the highest in the table; a model tuned on F1 would
be rewarded for learning it).

**4.** Dev PR-AUC is computed on pooled dev rows and reflects ranking *within and across* dev
experiments. The frozen threshold (about 10.95) is below essentially every test row's score: test
experiments sit at a different distance from the global reference than dev experiments do, because
operating regimes differ between experiments far more than within them (the fault-free recording has
`flow_rate` near 125 L/min with standard deviation 1.6; the normal rows of labelled experiments
average about 63 with standard deviation about 42). So the scores are not on a common scale across
experiments. Lesson: a threshold transfers only if the score distribution of normal data is stable
across the units you deploy on. A ranking metric pooled over units can hide that. Check per-unit
score distributions and per-unit alarm rates, not only pooled PR-AUC.

*Common incorrect answer.* "The test set is harder." Its ranking is not notably worse per family; the
calibration of the score across experiments is what failed.

**5.** Balanced weighting makes the model behave as if positives were about half the data. Its
outputs are inflated (in the worked example the mean prediction is 0.33 at 4 % prevalence), so
"p ≥ 0.08" selects most of the population and the campaign loses money. Ranking metrics are unchanged,
so nothing warned them. Ways forward: (i) fit unweighted and use its probabilities; (ii) keep the
weighted model but recalibrate on held-out data (Platt or isotonic), or correct the prior
analytically (subtract the log of the odds inflation from the logit); (iii) abandon the probability
rule and choose a threshold on the *score* directly by maximising net value on validation data.

*Common incorrect answer.* "Lower the threshold to compensate." Without recalibration there is no
principled value to lower it to.

**6.** No. Brier score decomposes into reliability (calibration), resolution (discrimination) and
uncertainty. New features probably improved resolution; calibration may be the same or worse. Look
at a reliability table on held-out data (equal-count bins), the mean predicted versus observed rate,
and if needed the decomposition itself. Also ask whether 0.003 is distinguishable from noise at this
sample size.

## Design-choice explanation: what a strong answer contains

* **Choice:** per-experiment burn-in on a single sensor (`flow_rate` abs z) as the bar: test PR-AUC
  0.805 and F1 0.748, close to the supervised row (0.827 / 0.783) and requiring no fault labels.
  Choosing the supervised row is also defensible if the answer says it assumes future faults resemble
  labelled ones and points to family `other` (0.751) as the place that assumption is weakest.
* **Evidence used honestly:** global-reference thresholds do not transfer (Q4); burn-in max-abs-z and
  Mahalanobis are *not* better than one sensor; differences of a few hundredths between rows are not
  claimed because the test set has 9 experiments and no intervals yet.
* **Assumption:** each unit starts in a healthy state and a 100-second calibration period is
  acceptable; rows in it are unmonitored.
* **Failure scenario:** a restart while the fault is already present (the fault becomes "normal"), or
  a legitimate set-point change after burn-in (everything alarms).
* **Monitoring:** alarm rate per unit after restarts; drift of the burn-in mean relative to fleet
  history; an absolute sanity limit alongside the relative one.
* **The clock:** any model must be shown to beat the clock *and* not to be using it (w3d1).

Weak answers: pick the highest number; do not name an assumption; treat the global reference as
"the correct semi-supervised setup" because the benchmark ships it.

## Interview rep - worked answer and rubric

**(a)** With $z_i = w^\top x_i + b$ and $\sigma$ the logistic function:
$\min_{w,b} \; -\sum_i \big[y_i \log \sigma(z_i) + (1-y_i)\log(1-\sigma(z_i))\big] + \tfrac{\lambda}{2}\lVert w \rVert^2$
(intercept not penalised; scikit-learn parameterises $C = 1/\lambda$ and multiplies the data term).

**(b)** Keeping each negative with probability β = 0.1 multiplies the odds of the positive class in
the sample by 1/β = 10 at every x. For a well-specified logistic model that changes only the
intercept: $b_{\text{sample}} = b_{\text{true}} + \log(1/\beta) = b_{\text{true}} + \log 10$; the
slopes estimate the same quantities, with larger variance because data was discarded. To correct:
subtract log 10 from the intercept, equivalently
$p = \dfrac{\beta p_s}{\beta p_s + (1 - p_s)}$. Nuances worth a sentence each: with L2 the relative
weight of the penalty grows when rows are dropped, so λ should be retuned; if the model is
misspecified the slopes do shift; the ranking barely changes, so downsampling is a compute decision,
not an accuracy one. Class weights have the same effect on the intercept as resampling.

**(c)** Not accuracy: 99 % is free. ROC AUC is fine for comparing rankers and is stable if prevalence
drifts, but it will not reveal that precision is unusable at 1 %. PR-AUC (with its 0.01 floor stated)
or, better, precision/recall at the operating point the business can afford. Limits: PR numbers are
not comparable across prevalences; all three ignore calibration; and the right answer depends on the
action taken on a positive.

| | Not yet | Adequate | Strong |
|---|---|---|---|
| (a) | no regulariser or wrong sign | correct loss | notes the unpenalised intercept and C = 1/λ |
| (b) | "it helps the model learn the minority class" | intercept shifts by log 10, correct it | derivation via odds, variance cost, penalty interaction, misspecification caveat |
| (c) | recommends accuracy or ROC AUC only | PR-based metric with reason | ties the metric to the decision and states what none of them measure |

*Common incorrect answers.* "Downsampling removes bias towards the majority class": the unweighted
model is not biased; its probabilities are correct and its default 0.5 threshold is simply the wrong
operating point. "After downsampling use threshold 0.5": that is an implicit, uncontrolled choice of
operating point. "The coefficients change by a factor of 10."

Sources for (b): King and Zeng (2001), "Logistic regression in rare events data" (prior correction);
cited from memory, not re-opened in this session.
