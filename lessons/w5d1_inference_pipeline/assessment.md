# W5D1 assessment

Answer in writing before opening `solutions/lessons/w5d1_inference_pipeline/assessment_answers.md`.
Model answers, common incorrect answers and the interview-rep rubric are there.

## Reasoning questions (5-10 minutes)

1. Your parity check between the batch command's CSV and the evaluated path first showed a maximum
   difference of 1.4e-14 on scores around 8, with identical alarms. Is that skew? What would make
   you change your answer?
2. A colleague proposes to "make the service robust to sensor recalibration" by standardising each
   incoming batch with its own mean and standard deviation. Give the precise failure this introduces
   for the flow-rate detector, and one input on which it is maximally wrong.
3. `validate_input` refuses a file whose columns are right but in a different order. A reviewer calls
   that pedantic: "just select the columns by name". Argue both sides; which do you ship, and what
   would change your mind?
4. Why is a run with fewer than `n_burn + 1` rows an *error for that run* rather than a schema error
   for the whole batch? Give one case in which you would nevertheless stop the whole batch.
5. The batch command refuses to overwrite `out/` when its manifest belongs to another input. Name the
   incident this prevents and the cost it imposes.

## Design-choice explanation (10 minutes, written)

Explain to a teammate why the operating point in `model.json` was chosen with scores produced by
`Detector.score_batch` rather than by the w4d5 evaluation code, given that the two produce identical
numbers today. Your answer should mention what is being protected against, and what test keeps the
two paths from drifting apart.

## Rubric for open answers

| Criterion | Meets | Exceeds |
|---|---|---|
| Distinguishes numerical noise from skew | uses decision changes or a stated relative tolerance | relates the tolerance to how close scores are to the threshold |
| Names the fit-time / predict-time boundary | says which values are fixed at fit time | explains why recomputing them on the batch changes the model |
| Contract thinking | states what the boundary accepts and refuses | gives the failure mode each refusal prevents |
| Operational cost | names one cost of the strictness | proposes how to keep strictness and limit the cost (e.g. versioned schemas) |

## Interview rep: debugging (10-15 minutes, timed, reduced assistance)

> "We trained a fraud model offline with PR-AUC 0.62. Two weeks after launch, alerts are a third of what
> the offline evaluation predicted at the same threshold, and the analysts say the alerts they do get
> are good. No errors in the logs. Walk me through how you would find out what is going on."

Speak for 5 minutes, then write the three checks you would run first, in order, and what each result
would tell you. Score yourself with the rubric in the answers file before reading the model answer.
