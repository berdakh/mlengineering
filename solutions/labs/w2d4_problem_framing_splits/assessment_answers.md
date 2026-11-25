# W2D4 assessment: model answers

Open only after writing your own answers.

## Q1

**First question:** *what was a fold made of: rows or whole experiments?* Rows one second apart in the
same recording are near-duplicates (same operating point, same slowly varying temperatures), so a
row-level fold lets the forest look up the neighbours of each test row.

**Expected change:** a clear drop and a much wider spread across folds. Measured in this lesson on the
25 development experiments (`example/skab_row_vs_experiment.py`): row-level 4-fold ROC-AUC 0.986
(folds 0.982-0.987), experiment-level 4-fold 0.849 (folds 0.740-0.936); PR-AUC 0.980 versus 0.841.

*Common incorrect answers.*
* "Ask which hyperparameters were used" or "ask whether the scaler was fitted inside the folds." Real
  issues, second-order here: a forest does not need scaling, and no tuning explains 0.99.
* "The number will drop to chance." Not what happens: the sensors do carry transferable signal. The
  honest statement is "lower and far more variable", and the variability is itself a finding.
* "ROC-AUC is the wrong metric." True (prevalence 35 %, and the decision is event-level), but it is
  not the *first* question; a correct metric on a leaking split is still meaningless.

## Q2

| Case | Unit of generalisation | Split |
|---|---|---|
| (a) seizure detector for unseen hospitals | hospital (patients nested inside) | hold out whole hospitals; patient-wise is necessary but not sufficient (site effects: amplifiers, montage, annotators) |
| (b) same 200 shops, next quarter | time | temporal: train on the past, test on a later period; grouping by shop is *not* required because the shops recur. A random split by shop would answer a question nobody asked |
| (c) card fraud | time, and the entity that carries the pattern (card; ideally also merchant/ring) | temporal first; within the evaluation period report separately for cards seen and not seen in training; be aware that ring-level leakage via merchants survives a card-level split |
| (d) one pump retrained monthly | time, within that pump | temporal (walk-forward) on that pump's history. Cross-pump splitting would measure something irrelevant |

*Common incorrect answer:* "always split by group." The unit is derived from the deployment
situation. (b) and (d) are the cases experienced cross-subject researchers get wrong by reflex.

## Q3

1. **Logging gap in two test experiments.** The manifest does not change. A data-quality fact about
   test data is handled by a rule decided without looking at model results (for example: "segments
   after a gap longer than 5 s restart the feature warm-up"), applied to *all* experiments. Removing
   test experiments because they are inconvenient is selection on the test set.
2. **Four new experiments.** `v1` stays as it is, so old results remain interpretable. Either leave
   the new recordings unassigned and use them as an additional, later test set (the most valuable use:
   they are genuinely post-hoc), or create `v2` that adds them, and recompute and relabel every
   result. `validate_splits` should fail until one of these is done.
3. **Disappointing result, another seed looks better.** Nothing. This is exactly what freezing is for.
   Re-drawing the split after seeing results turns the test set into a tuning knob; the estimate is
   then optimistic by an unknown amount. If family balance is a real concern it had to be raised
   before results (and stratification already addresses it).

*Common incorrect answers:* "regenerate with the same seed after adding the files" (the worked
example, part 2, shows membership changes); "drop the two gappy experiments from test."

## Q4

| Framing | Labels needed | Right when |
|---|---|---|
| (a) forecast next minute of pressure | none beyond the signal itself (self-supervised) | the decision depends on a future *value* (for example scheduling against a limit), or as an intermediate step whose residual becomes an anomaly score |
| (b) classify windows normal/faulty | reliable positive and negative labels covering the fault types you expect to meet | faults recur in known forms and there are enough labelled episodes per form; fails silently on fault mechanisms absent from training |
| (c) anomaly detection on normal data | plenty of verified-normal operation; fault labels only for *evaluation* | faults are rare, varied or new; the price is that "abnormal" includes harmless novelty (a new operating mode), so false alerts rise after any process change |

For SKAB: (a) is not the goal because no decision uses a forecast value; (b) is possible (35 %
positives) but protocol B tests whether it survives unseen fault families; (c) matches the stakeholder
need and has a designated fault-free recording. The labels and sampling structure decide, not the
model family one prefers.

*Common incorrect answer:* "forecasting needs no labels so it is always the safest." It needs no
*fault* labels, but then nothing in training tells the model which deviations matter.

## Q5 (design choice)

**For a fixed test set plus grouped development folds.** One untouched set of experiments gives a
final estimate that no modelling decision has influenced, at the cost of a single evaluation; it is
simple to explain and to audit ("these nine files were never used"), it mirrors how a model is
actually accepted before deployment, and it cannot be eroded by the dozens of small choices
(features, thresholds, which baseline to keep) that nested CV only protects against if *every* choice
is inside the inner loop, which in practice it never is.

**Strongest argument against, at this size.** Nine experiments means nine events: event recall moves
in steps of 0.11 and its interval is very wide; `valve2` is represented by a single test experiment.
Nested cross-validation would use all 34 events for the estimate and so be far less noisy.

**What to report so the weakness is visible.** The test estimate *with* an experiment-level bootstrap
interval; the grouped cross-validation estimate on the development pool next to it (if they disagree
strongly, say so); per-family results; and the count of events behind every number.

*Rubric.* 2 points: both sides argued with a mechanism, and a concrete reporting remedy. 1 point: one
side only, or "nested CV is more rigorous" without saying what it costs. 0: treats the choice as
arbitrary. *Common incorrect answer:* "a fixed test set wastes data, so use all of it for CV and
report the CV score of the tuned model" - that is the selection-optimistic number.

## Interview rep: model answer

Prioritised checks (strongest first):

1. **Label availability / censoring.** Customers who signed up in the last 12 months cannot have a
   12-month label. If they were kept and labelled by current status, recent sign-ups are "retained" by
   construction; if rows were kept only when the outcome was known, recent cohorts contain churners
   only. *Test:* tabulate label by sign-up month; restrict to cohorts at least 12 months old.
   *Direction:* unpredictable sign, usually down, and the base rate changes.
2. **Split does not match deployment.** The model will score *future* sign-up cohorts; a random
   customer split mixes cohorts, so pricing changes, product changes and seasonality are shared between
   train and test. *Test:* train on cohorts up to month M, evaluate on later cohorts (only those with
   matured labels). *Direction:* down; report how AUC varies by cohort.
3. **Features that are not truly "first 30 days".** Lifetime totals, current plan, "last login", account
   status, support-ticket counts computed at extraction time all encode the outcome. *Test:* rebuild
   features from event logs with a hard cut-off at day 30; look for single features with implausible
   importance. *Direction:* down, sometimes dramatically.
4. **Hidden groups.** Re-subscribers, household or company accounts, shared payment methods appear as
   several customers. *Test:* group by payment method or address hash and re-split. *Direction:* down, usually modestly.
5. **Is AUC the right evidence?** What action follows, at what capacity, compared with what rule
   (for example "fewer than 3 active days in the first 30")? *Test:* precision in the top k % against
   that rule on the temporal test set. *Direction:* may reveal that 0.91 buys little over the rule.

*Scoring.* Strong: 1 and 2 both raised with a concrete test, at least one of 3-5, and directions
stated. Adequate: 2 and 3. Weak: only generic items ("check for overfitting", "try more models",
"use nested CV"). *Common incorrect emphasis:* worrying about the 5-fold tuning procedure. Tuning
inside the 80 % is fine; the problems are all in what the rows and labels *are*.
