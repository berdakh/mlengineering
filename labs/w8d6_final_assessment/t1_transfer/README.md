# t1 - Final transfer task: a complete evaluation in 90 minutes

**Independent and timed. 90 minutes, one sitting, no hints, no solutions, no assistant.**
Set a timer. When it rings, stop, commit what you have, and write down what is missing. An unfinished
honest evaluation is worth more than a finished one with a leak.

This is the counterpart of the w3d6 transfer sitting, on a problem you have not seen. The data is
**SYNTHETIC**: an invented reservation service, "TableTop" (schema and limits in
[`../data/README.md`](../data/README.md)). Being simulated, it tells you nothing about real diners;
it does let the checks compare your evaluation with the generator's ground truth.

## Situation

TableTop takes reservations for 10 restaurants. A no-show costs a table for the evening. Every
evening a small team phones guests booked for the **next** service day to confirm. They can call
**10 % of the next day's reservations** (rounded up). A call to a guest who would not have come
frees the table in time; a call to a guest who would have come is wasted.

They ask: *if a model chose whom to call, what share of our calls would reach a would-be no-show, and
is that better than a rule we could apply ourselves?* The model would be trained once, on everything
known on the evening of 2024-09-30, and used for service days from 2024-10-01.

You receive one export, `../data/reservations.csv`, documented in the data README.

## What to produce

1. `lab/evaluate.py`: implement the five pieces whose signatures are fixed in the file
   (`FEATURES`, `split_train_test`, `daily_topk_precision`, `fit_and_score`, `run`).
2. `lab/REPORT.md` (template provided, one page): framing, leak audit, split, baseline and model,
   metric, interval, one slice, limitations.

Suggested use of the 90 minutes: 10 framing and reading the dictionary, 15 leak audit, 15 split and
metric, 25 baseline and model, 10 interval and slice, 15 writing.

## Check your work

```bash
python labs/w8d6_final_assessment/t1_transfer/lab/evaluate.py
python wb.py check labs/w8d6_final_assessment/t1_transfer     # or:
python -m pytest labs/w8d6_final_assessment/t1_transfer/checks -q
```

The checks grade the *evaluation*: what the model may see, how the data is split, what the metric
computes, and whether the reported performance is possible at all. They do not reward a higher score.

## Acceptance criteria

* The checks pass.
* Every column is classified in the report as usable or not on the evening before service, with the reason.
* The split matches the deployment described above.
* The reported number is the decision metric, compared with a rule that needs no model, with an
  interval whose resampling unit you justify.
* One slice of the called reservations is reported with its size.
* Limitations name at least: what the synthetic data cannot show, what the interval does not cover,
  and one way the deployment could differ from the test period.

## Recording the sitting

Fill in the conditions box at the top of `REPORT.md`. Scoring guidance and a reference report are in
`solutions/labs/w8d6_final_assessment/t1_transfer/`. Open them after you have stopped.
