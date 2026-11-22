# Assessment: w7d3 drift versus degradation

Answer in writing before opening `solutions/lessons/w7d3_drift_vs_degradation/assessment_answers.md`.

## Reasoning questions

1. Give the definitions of covariate, prior and concept shift in terms of $P(x)$, $P(y)$, $P(y \mid x)$,
   $P(x \mid y)$. For each, name one change in the SKAB plant that would produce it.
2. In period B of the replay the drift monitor flagged every window and the detector caught exactly
   the same faults. Explain why, using the score's definition. Then describe a *different* detector for
   which the same recalibration would have degraded performance.
3. Period C's recall estimate was unknown on day 65, 0.67 on day 90 and 0.36 on day 150, against a true
   0.20. Explain each of the three numbers and why none of them equals 0.20.
4. Operators investigate only the 30 % of alarms with the highest peak score. In which direction is
   measured precision biased, and how would you obtain an unbiased estimate without investigating
   every alarm?
5. Your recall monitor needs a ±0.10 interval. Faults happen about twice a week, and missed-fault
   reports arrive up to 60 days late. How long is a window, and how stale is each answer?
6. Why does `window_metrics` place a label in a window by event time but decide whether it exists by
   label time? What goes wrong with each of the two other combinations?

## Design-choice explanation (required)

7. `monitor_report` returns "inconclusive" when the interval straddles the baseline, instead of
   comparing the point estimate with `baseline - margin`. Defend this choice to a plant manager who
   wants a red/green light, and say what it costs.

## Interview rep (15 minutes, timed, rubric only)

> "We ship a model that predicts whether a customer will cancel their subscription in the next 90
> days. It has been live for two months. The product team asks for a weekly dashboard showing that the
> model is still accurate. Design what you would show them."

Speak or write for at most 10 minutes, then score yourself with the rubric in the answers file.

## Rubric for questions 2, 3, 7 and the interview rep

| Score | Meaning |
|---|---|
| 0 | Treats drift as degradation, or reports metrics without label delay or denominators |
| 1 | Separates the questions but cannot say how labels arrive or how many are needed |
| 2 | Separates the questions, states delay, coverage and the direction of each bias, sizes a window |
| 3 | All of 2, plus proposes a fast proxy with its failure mode and a concrete action per outcome |
