# w3d6 challenge - transfer exercise, part 2: a complete evaluation in 90 minutes

**Independent and timed. 90 minutes, one sitting, no hints, no solutions, no assistant.**
Set a timer. When it rings, stop, commit what you have, and write down what is missing. An unfinished
honest evaluation scores higher than a finished one with a leak.

This is the second sitting of the course's transfer exercise (part 1 was the w2d6 challenge). The
data is **SYNTHETIC**: an invented B2B vendor, "LedgerLine". Schema and limits:
[`../data/README.md`](../data/README.md). It replaces a public business dataset whose access and
licence could not be verified from the authoring environment (see the w2d6 challenge). Being
simulated, it tells you nothing about real customers; it does let the checks compare your estimate
with the generator's ground truth.

## Situation

LedgerLine's collections team can make **15 proactive calls per week**. A call to a customer whose
invoice would have been paid late tends to bring payment forward; a call about an invoice that would
have been paid on time is wasted and mildly annoying. Each Monday they choose 15 of the invoices
issued in the previous seven days. They currently choose by gut feeling.

They ask: *if a model picked the 15, what share of our calls would land on invoices that really go
late, and is that better than a simple rule we could apply ourselves?* The model would be trained
once, on everything known on 2024-09-30, and used from 2024-10-01.

You receive one export, `../data/invoices.csv`, with a data dictionary.

## What to produce

1. `challenge/evaluate.py`: implement the five pieces whose signatures are fixed in the file
   (`FEATURES`, `split_train_test`, `weekly_topk_precision`, `fit_and_score`, `run`).
2. `challenge/REPORT.md` (template provided, one page): framing, leak audit, split, baseline and
   model, metric, interval, one error slice, limitations.

Suggested use of the 90 minutes: 10 framing and reading the dictionary, 15 leak audit, 15 split and
metric, 25 baseline and model, 10 interval and slice, 15 writing.

## Acceptance criteria

* `python wb.py check w3d6 --challenge` passes (19 checks, about 15 s). The checks grade the
  *evaluation*: what the model may see, how the data is split, what the metric computes, and whether
  the reported performance is possible at all. They do not reward a higher score.
* Every column of the table is classified in the report as usable or not at issue time, with the reason.
* The split matches the deployment described above, including what is and is not known on 2024-09-30.
* The reported number is the decision metric, compared with a rule that needs no model, with an
  interval whose resampling unit you justify.
* One slice of the model's behaviour is reported with its size, and the report says what you would
  check next.
* Limitations name at least: what the synthetic data cannot show, what the interval does not cover,
  and one way the deployment could differ from the test period.

## Recording the sitting

In `REPORT.md`, fill in the conditions box: start and stop time, anything you looked up, whether you
finished. Then `python wb.py mark w3d6 independent` only if the sitting was unassisted and the checks
pass; otherwise `python wb.py mark w3d6 review`.

Scoring guidance and a reference report are in
`solutions/lessons/w3d6_error_analysis_transfer/challenge/`. Open them after you have stopped.
