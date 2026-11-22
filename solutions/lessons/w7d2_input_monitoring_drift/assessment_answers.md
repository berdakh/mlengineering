# W7D2 assessment: model answers

## Reasoning questions

**1. Mean of sorted differences.** Equal to W1 only when both samples have the same size (then the
optimal transport pairs the i-th smallest values). With 60 against 9,000 it either fails or, if truncated
to the shorter length, compares the window with the 60 *smallest* reference values: a large, meaningless
distance. Use the CDF integral (or `scipy.stats.wasserstein_distance`). *Wrong answer:* "it is fine
because both are sorted".

**2. Sentinels out of the statistics.** A sentinel is not a measurement; it is a broken input with a
different cause (a producer bug) and owner. Included, it dominates the window: W1 moves by roughly
(share of sentinels) x 10,000 L/min, so the dashboard shows a huge "drift" on flow rate while the actual
flow distribution may be unchanged, and the real issue (a producer sending sentinels) is reported under
the wrong name. Count violations separately and exclude them.

**3. KS on 1 Hz data.** The test assumes independent observations; consecutive seconds are strongly
correlated, so the effective sample size is far smaller than 60 and the null distribution used for the
p-value is too narrow: false positives in most windows (worked example: 75 % at phi = 0.9). Use the KS
*statistic* (or W1) with a threshold calibrated on stable windows of the same sensor, which includes the
autocorrelation in the calibration.

**4. PSI and window size.** Under no drift, the expected PSI is approximately (k - 1)(1/n + 1/m): sampling
noise in the bin shares. Smaller windows have noisier shares and larger PSI; a fixed 0.1 is therefore
exceeded by most 60-sample windows and by almost no 480-sample windows (98 % at n = 30, 0 % at n = 480
in Figure 2).

**5. Replay, reference A.** The calibration windows were the development runs' normal operation, so the
thresholds absorbed the variation between those runs. A closing valve changes the one-minute
distributions of most sensors by less than that variation: no alert. The two `other` test runs operate at
a slightly different temperature / vibration level than any development burn-in, so every normal minute
exceeds the threshold: the monitor detects "new operating conditions", not faults.

**6. Price alert after a planned change.** Not necessarily. Drift says the input distribution moved;
accuracy depends on whether the model's learned relation still holds at the new prices and whether the
decision boundary is crossed more often. You need labels (delayed), or proxies such as the prediction
distribution and downstream business metrics; and you need to know whether the price range after the
change was represented in training. Annotate the change and re-baseline; evaluate when labels arrive (w7d3).

## Design-choice explanation (what a strong answer contains)

Per-machine reference (each run's first 5 minutes after start-up, or a rolling "last stable hour"),
one-minute windows (the detector's alarm granularity), W1 in sensor units with per-sensor thresholds
calibrated on stable data across many machines with a Bonferroni split over the 8 sensors, target about
1 alert per machine-day measured on held-out stable data. Separate schema and missingness counters with
their own alerts to the data owner. An alert means "this machine's inputs changed: check sensor or
process"; it does not mean "fault" (the detector decides that) and does not mean "the model is wrong"
(that needs labels). Optionally a daily fleet-level report against the development data for "outside the
validated domain".

## Interview rep: worked answer and rubric

1. $D = \sup_x |F_1(x) - F_2(x)|$. Under the null (same continuous distribution, independent samples) its
   distribution depends only on the sample sizes (distribution-free), which gives the p-value. Fails with
   autocorrelation (effective sample size), and with ties or discrete data the exact null changes.
2. Report an effect size in meaningful units: W1 or difference in means/quantiles in the feature's units,
   share of values outside the historical range, compared with a materiality threshold agreed with the
   product team. With 10 million rows every difference is significant.
3. Label reference rows 0 and current rows 1, train a classifier with cross-validation, measure AUC on
   held-out rows. 0.5: the classifier cannot tell them apart (no detectable change in the joint
   distribution it can model). 0.65: the samples differ; the model's feature importances point to where.
   Group-aware CV if rows are dependent.
4. A change in the relation between features (joint distribution) can leave every marginal unchanged,
   e.g. current and flow both normal but no longer correlated; and many small marginal changes can matter
   together while each stays under its threshold.

| Score | Criteria |
|---|---|
| Strong | all four correct, mentions independence and effect sizes, gives a concrete joint-shift example |
| Adequate | definitions right, misses why p-values fail or the classifier-test interpretation |
| Weak | equates significance with importance; cannot define the statistic |

## Challenge: common weak submissions

* Ignore the calendar: the price feature alerts for weeks after the planned change (alert fatigue).
* Suppress the feature forever: the unplanned price drop on day 50 is missed.
* PSI > 0.25 rule: misses the 10 % price drop (PSI about 0.1) and even the planned 12 % change.
* Monitor only the values present: a 30 % outage of `basket_size` is invisible.
