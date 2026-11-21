# w1d6 assessment

Write your answers (in `progress/notes.md` or a file in your project) **before** opening
`solutions/lessons/w1d6_notebook_to_package/assessment_answers.md`. Short answers; reasoning matters
more than length.

## A. Reasoning questions

**Q1. Order dependence.** In `explore_skab.py`, the cell "z-score against normal" uses `df`. State
exactly which rows `df` holds when the file is run top to bottom, why that is not what the comment
claims, and what *third* outcome the author could have seen in the live notebook.

**Q2. Counting what a cleaning step removes.** The notebook prints `(46806, 13)` and then
`(37401, 14)`. Without running anything else, what is the most likely identity of the 9,405 missing
rows, what single fact about the files makes `dropna()` remove them, and why is the resulting
`37401` a particularly dangerous wrong number?

**Q3. Design choice (explain and defend).** `load_experiment` has to do something with a file that
has no `anomaly`/`changepoint` columns. Options: (a) fill with 0, (b) fill with NaN and keep a
nullable column, (c) raise, (d) add a separate boolean `is_labelled` column. Choose one for this
project, justify it against at least two of the others, and name one later stage of the project that
your choice makes easier and one it makes riskier.

**Q4. Commit boundaries.** You discover the positional-id bug while extracting `load_raw`. Describe
the commits you make, in order, and what evidence each one carries. What is lost if you fix it
inside the extraction commit?

**Q5. Limits of the method.** Give two situations in which a characterization (golden-output) test is
the wrong tool, and say what you would use instead in each.

## B. Rubric for open-ended answers (applies to Q3-Q5 and to your `NOTES.md`)

| Level | Description |
|---|---|
| **Demonstrated** | States the mechanism, not just the symptom; gives a concrete consequence for a later stage (splits, features, evaluation); compares alternatives on a stated criterion; names what the choice costs |
| **Partial** | Correct conclusion with a generic justification ("cleaner", "safer"); or mechanism right but no downstream consequence |
| **Not yet** | Restates the code; treats the notebook's output as ground truth; cannot say which commit would carry which change |

## C. Commit hygiene

Self-review with `lab/COMMIT_REVIEW.md`. Its levels (Demonstrated / Partial / Not yet) are the
grade for the history; the automated checks deliberately do not look at Git.

## D. Interview rep: debugging (10-15 minutes, timed)

Conditions for Week 1: first attempt untimed is allowed, but **say or write your hypotheses in the
order you would test them before running any code**. The rubric scores the ordering.

> A colleague reports: "`test_defaults` passes when I run it alone and fails when I run the whole
> file. Sometimes the alert thresholds in the service are wrong after someone calls the endpoint
> with an override." The function:
>
> ```python
> import json
> from pathlib import Path
>
> _CACHE = {}
>
>
> def load_thresholds(path, overrides={}):
>     """Per-sensor alert thresholds from a JSON file, with optional overrides."""
>     if path not in _CACHE:
>         _CACHE[path] = json.loads(Path(path).read_text())
>     thresholds = _CACHE[path]
>     thresholds.update(overrides)
>     return thresholds
> ```
>
> 1. List your hypotheses in the order you would check them, with the one-line experiment for each.
> 2. Identify the defect(s). Say which suspicious-looking thing is **not** the cause, and how you know.
> 3. Fix it, keeping the "parse each file once" behaviour.
> 4. Write the two tests that would have caught it.
> 5. One sentence: what does this have in common with today's notebook?

Reference, tests and scoring: `solutions/lessons/w1d6_notebook_to_package/interview_rep/` and the
answers file.
