# Hint 1 - concept (w3d4)

* Everything this module decides about an alarm is decided from **its start row**. If you find yourself
  asking "does the alarm overlap the event?", re-read the matching rule: overlap is not the question.
* An event and an alarm are the same data structure: a half-open `(start, end)`. Lengths are
  `end - start`; adjacent runs `(2, 5)` and `(5, 8)` share no row.
* Post-processing order matters: merge runs that are close, *then* drop runs that are short. Short
  fragments of one fault are exactly what merging is for.
* A missed event has a delay too: infinity. Summaries are taken over **all** events.
* Time comes from timestamps. Rows are a proxy for time only when sampling is regular and gap-free,
  which SKAB is not.
* Challenge A: a rate from a few hours of data is a count over an exposure. The number to compare with
  a budget is the upper confidence bound, not the point estimate.
* Challenge B: start from what is known about how the *labels* are produced (lag, jitter, event length,
  event spacing), not from what makes a detector score well.
