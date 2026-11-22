# w3d6 assessment

Write answers before opening `solutions/lessons/w3d6_error_analysis_transfer/assessment_answers.md`.
Short answers: 3-6 sentences, with a number where one exists.

## Reasoning questions

1. In the lab output, row-pooled recall is 0.656 and the mean of per-experiment recalls is 0.663. In
   the planted check data the same two quantities are 0.87 and 0.25. What property of the data makes
   them agree in one case and disagree in the other, and which would you report to (a) the reliability
   engineer and (b) someone sizing compute for alert storage?
2. Fragment errors are 695 segments and 2,861 rows; late detections are 6 segments and 273 rows. The
   stakeholder's stated concern is detection delay. Rank the two with frequency x cost x fixability,
   making your assumptions explicit, and say what evidence would reverse your ranking.
3. You examine recall by family, by gap presence, by row-sharing, by burn-in flow level and by "flow
   moves less than 1 sd under the fault". Only the last shows a difference (0.445 vs 0.747). Give two
   distinct reasons why it should not be reported as a discovered failure slice.
4. `other/13` has false-alarm rate 0.878 and a 329-row pre-onset alarm. `other/12` and `other/13`
   share 178 rows with contradictory labels. What can and cannot be concluded about the detector from
   `other/13`, and how would you present these two experiments in a results table?
5. At threshold 2.5766 `valve2/2` has recall 0.785 and delay 37 rows; at 2.577 it has 0.618 and 56.
   Explain the mechanism, and state which of your error-analysis conclusions survive it.
6. (Challenge) The honest model reaches 0.722 and the no-model rule 0.727 on 209 calls. A colleague
   proposes gradient boosting "to get clearly ahead of the rule". Using the generator ceiling (0.751)
   and the interval (0.651 to 0.783), say what you expect and what you would do instead.
7. (Challenge) The temporal split with and without the label-delay exclusion gives the same AUC
   (0.763 vs 0.764). Why is the exclusion still required, and in what situation would the two differ a lot?

## Design-choice explanation (about 150 words)

Your next experiment is hysteresis: raise the alarm at the current threshold, clear it only after the
score has stayed below a lower threshold for `h` rows. Choose how you will pick `h` and the lower
threshold, on which data, with which metrics, and how you will prevent the choice from being an
artefact of the 25 development experiments. State the side effect you expect and the result that
would make you abandon the idea.

## Rubric

| Criterion | Not yet | Adequate | Strong |
|---|---|---|---|
| Unit of analysis (Q1) | treats the two numbers as interchangeable | explains weighting by rows vs by experiments | ties each to a question someone actually has |
| Ranking (Q2) | ranks by size only or by cost only | uses all three factors with stated assumptions | names the evidence that would change the ranking |
| Slice discipline (Q3) | accepts the slice | names multiplicity or label-dependence | both, plus what a legitimate version would look like |
| Label noise (Q4, Q5) | blames the model or blames the labels wholesale | separates irreducible from model error | proposes reporting with and without, and notes fragility of per-experiment numbers |
| Evidence versus effort (Q6, Q7) | expects a better model to fix it | uses ceiling and interval to bound the gain | redirects effort to the causal question or to the no-history slice; explains construction over measurement |
| Design choice | tunes on test, or on all dev at once | grouped cross-validation over experiments, both metrics | also pre-states the abandon criterion and the delay cost |

## Interview rep (debugging narrative, 10-15 minutes, spoken; Week 3 conditions: timed, rubric only)

> "A fraud model had validation AUC 0.97. Two weeks after launch, on the first labelled production
> sample, AUC is 0.71. Talk me through how you would investigate. I will answer questions about the
> system if you ask them."

Speak for five minutes without notes, then write down the ordered list of hypotheses you gave and the
single query or check you would run for each. Compare with the rubric in `assessment_answers.md`
only after writing. Per the Week 3 rule, no worked answer is given until you have made a second
attempt.
