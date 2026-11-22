# W3D5 assessment - model answers, common incorrect answers, rubrics

Open after writing your own answers. Numbers quoted here were computed in the authoring session
(Wilson limits with the formula of README section 2.4; the 1 − 0.95^k figure by arithmetic; the
interview-rep demo by running `interview_rep/paired_precision.py`).

## Q1. "F1 = 0.812 ± 0.006" from a row bootstrap of 12,000 rows from 10 experiments

**Model answer.** The resampling unit is wrong. Rows of one experiment are correlated, so a row
bootstrap produces replicate test sets that are far more alike than two real test sets of ten new
experiments would be. The interval is too narrow, typically by a factor of several (4 to 11 on SKAB
in the lab), and the "±" also hides that the interval need not be symmetric. Smallest change: resample
the 10 experiments (or overlap groups) with replacement, keep the threshold frozen, recompute F1 on the
concatenated rows, and report the percentile interval with "10 clusters" beside it. Add that with 10
clusters even that interval undercovers somewhat.

**Common incorrect answers.**
* "Use more bootstrap replicates." The Monte Carlo error is not the problem; the unit is.
* "Use a t-interval instead." Still treats 12,000 rows as independent.
* "The interval is too wide because F1 is unstable." Wrong direction.

## Q2. Cluster-bootstrap recall interval [0.71, 0.93] on 7 clusters

**Model answer.** (1) With few clusters the bootstrap variance is biased low by roughly (G − 1)/G
and the percentile interval undercovers: in the worked example a nominal 95 % interval covered about
87-88 % of the time with 7 or 9 clusters. (2) The interval conditions on the fitted model and the
frozen threshold; training-set sampling, seed noise and the selection of this model (and threshold)
are not in it, so the uncertainty about the method is larger. A third acceptable reason: the
resampling distribution has only 1,716 distinct resamples and cannot exceed the most extreme
cluster. **Why any width can mislead:** an interval describes sampling variation only. Leakage, a
label that the clock predicts, overlap between "independent" clusters, or a test bench that differs
from deployment all bias the point estimate, and no interval widens for bias.

**Common incorrect answers.** "Use BCa and it will be fine" (BCa is second-order accurate but cannot
create information that 7 clusters do not contain); "the interval is fine because recall is a mean"
(it is a ratio of sums over clusters, and the cluster count still governs).

## Q3. Overlapping intervals, same 30 experiments

**Model answer.** Overlap of two marginal intervals is not the test for a paired design. Each
marginal interval contains the between-experiment variance that both models share (hard experiments
are hard for both). The difference cancels that shared part: Var(d̄) = (σ_a² + σ_b² − 2rσ_aσ_b)/G.
If the correlation across experiments is high, the paired interval for the difference can exclude
zero while the marginal intervals overlap almost entirely (worked example: overlapping intervals,
paired interval [+0.0155, +0.0191]). The number that settles it is the **paired interval of the
difference** (or equivalently the per-experiment differences: their mean and spread, or the number of
experiments on which A wins).

**Common incorrect answers.** "Overlap means no difference" (too conservative under pairing). "No
overlap is required for a claim" (same mistake). "Compute a two-sample t-test on the 30 + 30 scores"
(ignores the pairing).

## Q4. Eight of eight events detected

**Model answer.** Write "8 of 8 held-out events detected (95 % interval for the detection rate: 68 %
to 100 %, Wilson)". The exact Clopper-Pearson interval is 63 % to 100 %. One sentence for a
non-statistician: "Eight successes in eight tries is what you would also see fairly often from a
detector that catches only seven faults in ten, so we can say it is good, not that it is perfect."
Add what "detected" meant (matching rule, delay) and that false alarms are a separate number.

**Common incorrect answers.** "100 % ± 0 %" (Wald collapses at the boundary). "Bootstrap it" (every
resample gives 1.0). "Detection is 100 % on the test set, which is all we claim" (true, and useless
for the decision: stakeholders will read it as a property of the detector).

## Q5. Five seeds 0.84, 0.86, 0.81, 0.87, 0.85 against a deterministic 0.84

**Model answer.** The seed mean is 0.846 with sd 0.023 over seeds. (a) Not supported: the mean
exceeds the baseline by 0.006, a quarter of one seed-sd, and seed variation is only one of the
sources; the test-set sampling uncertainty (which neither number includes) is likely larger.
(b) Not supported either in the sense of a demonstrated non-inferiority; it is merely *consistent*
with the data. (c) True and meaningless: picking the best seed is selection on noise. (d) is the
honest answer. Next: evaluate the neural model's seed-average score (or each seed) and the baseline
on the same test clusters, form per-cluster differences, and compute a paired cluster-bootstrap
interval for the difference; report seed mean ± sd separately. If the interval is wide, say what
difference the test set could resolve (section 2.7).

**Common incorrect answers.** Reporting 0.87 ("the method can reach 0.87"). Averaging seeds and
then bootstrapping over the five seeds as if they were test samples.

## Q6. Six comparisons, one p = 0.03

**Model answer.** Weak. If none of the six is better and the tests were independent, the chance of
at least one p ≤ 0.05 is 1 − 0.95⁶ ≈ 0.26. The comparisons share the baseline and test set, so they
are positively correlated and the true figure is somewhat lower, but still far from 0.05. p = 0.03 is
also above the Holm threshold for the smallest of six p-values (0.05/6 ≈ 0.0083). Remedies: pre-register
the one comparison that matters; apply Holm (or Bonferroni) across the six; or confirm the winner on a
fresh set of experiments that played no part in the choice. Also report the effect size and interval:
a "significant" 0.01 PR-AUC would not change a decision.

**Common incorrect answers.** "p = 0.03 < 0.05, so it is better." "Multiple comparisons only matter
for hundreds of tests."

## Q7. Design choice: overlap group as unit, threshold frozen inside the bootstrap

**Model answer (strong).** The bootstrap must imitate how the test set came to exist. What was sampled
was a set of experiments; but five pairs of SKAB files share identical rows, so `other/2`, `other/3`,
`other/4` are not three independent draws of "a fault experiment". Treating them as separate clusters
would count shared information twice and narrow the interval; resampling overlap groups is resampling
the actual independent units, and the v2 test set has 7 of them, not 9. The opposite choice (rows or
files) estimates variability under a sampling process that never happened; it is never what we want
for a claim about new experiments, though a file-level bootstrap would be acceptable if files were
known to be independent. The threshold was chosen on development data and is part of the deployed
artifact; re-choosing it inside each replicate would estimate the variability of the *procedure*
"tune a threshold on the test set, then score it" (and leaks test labels into the threshold). That
procedure-level quantity is sometimes wanted (how much does the tuned operating point move with the
data?), but then the tuning must happen on resampled *development* clusters, in a nested design, not
on the test set. Limits: with 7 clusters the percentile interval undercovers, and neither choice
addresses bias from leakage or from the unrepresentative testbed. Decision consequence: claims are
restricted to differences the 7 or 30 clusters can resolve (about 0.25 and 0.10 PR-AUC).

**Common incorrect answers.** "Experiments, because they are separate files" (misses the overlap);
"threshold frozen for speed"; "re-tuning the threshold gives a more realistic interval" (it answers a
different question, and on test labels).

Rubric: the table in `lessons/w3d5_uncertainty/assessment.md`.

## Interview rep: "Is B better? 0.912 vs 0.904 on 50,000 windows from 20 machines"

**Rubric (score each 0/1/2).**

| Element | 0 | 1 | 2 |
|---|---|---|---|
| Unit | treats 50,000 windows as independent | mentions machines | resamples machines, explains why (shared machine state, label policy) |
| Pairing | compares two separate intervals | mentions same windows | paired difference per machine, one resample used for both models |
| Precision specifics | ignores the denominator | notes it depends on flags | handles resamples with nothing flagged; ratio of sums vs mean of ratios stated |
| Beyond sampling | none | asks about threshold/operating point | asks whether the thresholds were tuned on this set, whether recall/alert volume changed, label quality |
| Decision | "significant / not" | gives interval | relates the difference to cost (fewer false alerts per week) and proposes shadow running if unresolved |

**Worked answer (read only after a second attempt).** Precision is a ratio of TP to flagged windows.
First check that the comparison is at comparable operating points: a precision gain bought by flagging
fewer windows may cost recall, so look at recall and alert volume too, and confirm the thresholds were
not tuned on this test set. Then compute per machine TP and flagged counts for both detectors. The
independent unit is the machine: windows from one machine share its noise floor, mounting and fault
history. Bootstrap machines (20 of them) with replacement, using **one** draw per replicate for both
detectors, and compute precision(B) − precision(A) as a ratio of summed counts in each replicate;
drop and count replicates where a detector flags nothing. Report the difference, its percentile
interval, and on how many machines B is better; add a sign-flip permutation test on per-machine
differences if a p-value is requested. With 20 machines the interval undercovers somewhat. If it
includes zero, the statement is "not resolved with 20 machines", and the next step is a shadow run on
more machines, not a launch decision on 0.008.

Reference code (`solutions/lessons/w3d5_uncertainty/interview_rep/paired_precision.py`), SYNTHETIC
demo run on 2026-11-22: precision(B) − precision(A) = +0.0110, machine-level paired 95 % interval
[+0.0017, +0.0196], 0 undefined replicates. The edge case the code must handle is a resample in which
a detector flags nothing (precision undefined): it is dropped and counted, never set to 0.

**Common incorrect answers.** "50,000 windows, so any difference is significant" (row-level
thinking); "run a two-proportion z-test" (same); "B is better because 0.912 > 0.904" (no uncertainty);
"bootstrap A and B separately" (unpaired, too wide).
