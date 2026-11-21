# W2D4 assessment

Write your answers in `progress/notes.md` (or a file of your own) **before** opening
`solutions/lessons/w2d4_problem_framing_splits/assessment_answers.md`. About 15 minutes for Q1-Q5.

## Reasoning questions

**Q1.** A colleague reports "ROC-AUC 0.99 on SKAB with a random forest on the raw sensor values,
5-fold cross-validation". State the one question you ask first, and what you expect the number to
become when it is answered properly. (The lesson's worked example contains the measured answer.)

**Q2.** For each situation name the unit of generalisation and therefore the unit of splitting:
(a) a seizure detector to be sold to hospitals that are not in your dataset;
(b) a demand forecast for the same 200 shops next quarter;
(c) a fraud model scoring card transactions, where one card has many transactions and fraud rings
    reuse merchants;
(d) a fault detector for one specific pump that will be retrained monthly on that pump's own data.

**Q3.** Your split manifest was frozen three weeks ago. Since then: (i) you found that two test
experiments have a 60-second logging gap; (ii) four new experiments were recorded; (iii) the test
PR-AUC of your favourite model is disappointing and a different seed would "balance the families
better". For each, say what you do to the manifest and why.

**Q4.** The same eight-sensor stream could be framed as (a) forecasting the next minute of pressure,
(b) classifying each window as normal or faulty, (c) anomaly detection trained on normal data only.
For each framing, state what labels it needs, and one condition under which it is the right choice.

**Q5 (design choice).** `make_splits` puts a fixed 25 % of experiments in a test set and uses
grouped folds on the rest, instead of nested cross-validation over all 34 experiments. Argue for
this choice, then give the strongest argument against it for a dataset of this size, and say what
you would report to make the weakness visible.

## Rubric for the written problem statement (lab Task 6 and challenge Part A)

Score each row 0 / 1 / 2. "2" requires a position a reviewer could disagree with.

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Decision | describes a model ("predict anomalies") | names a user | names who does what differently, and the status quo |
| Unit and prediction time | absent or mixes units | unit of prediction given | prediction, decision and generalisation units distinguished; information cut-off explicit |
| Label | "the label column" | definition given | origin, delay, noise and their consequence for achievable performance |
| Costs | "both errors matter" | asymmetry stated | rough ratio or budget stated as an assumption, and tied to the threshold or the top-k |
| Metric chain | a metric named | metric justified | business quantity -> operational proxy -> development metric, with what each can mislead about |
| Baseline | none | a trivial baseline | do-nothing **and** the expert rule, plus what margin justifies a model |
| Splits | random or unspecified | grouped or temporal | unit justified from deployment; what is frozen; second protocol or stated blind spot |
| Limits | none | generic caveat | specific claims the data cannot support |

Interpretation: 13-16 with no zeros is a statement you could defend in a design review. Any zero
in *Decision*, *Label* or *Splits* means rewrite that section before building anything on it.

## Interview rep (validation and leakage, 10-15 min, write or speak your answer first)

> "We built a model that predicts, from the first 30 days of a customer's activity, whether they
> will still be subscribed after 12 months. We took all customers who signed up in the last three
> years, split them 80/20 at random by customer, tuned on the 80 % with 5-fold CV and got AUC 0.91
> on the 20 %. Before we ship: what would you check?"

Give a prioritised list of at most five checks. For each: what could be wrong, how you would test
it with the data they already have, and which direction the reported number would move.
