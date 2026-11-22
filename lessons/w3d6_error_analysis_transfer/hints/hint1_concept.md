# Hint 1 - concept

Opening this hint means the work is recorded as guided, not independent.

**Lab.** Every function in `flowguard.erroranalysis` is a group-by over experiments followed by
arithmetic on two aligned 0/1 arrays, `label` and `flag`. The three ideas the checks enforce:

1. *The experiment is the unit.* A slice value is the mean of per-experiment numbers. If you find
   yourself summing TP and FN across experiments before dividing, you are computing something else.
2. *Undefined is `NaN`.* Ask of every ratio: what is the denominator, and can it be zero? If it can,
   the answer in that case is "not measurable", and it must stay out of means.
3. *A wrong row belongs to a run, and a run belongs to an event (or to none).* Classify the run by
   where it sits relative to the labelled event and to the event's first detection.

**Challenge.** Three questions settle most of it, and none is about modelling:

* For each column: *on what date does this value come into existence?* Compare that with the issue date.
* For each training row: *on the day the model is trained, has its label been decided?*
* For the metric: *what exactly does the team do on a Monday, and with which invoices?*
