# Hint 1 — concept

**Lab.** Two ideas carry almost every check.

1. *A check is a statement about rows together, per experiment.* Anything involving "previous row"
   (`diff`, duplicates, runs) is computed inside a `groupby("experiment_id")`. The first row of one
   experiment has nothing to do with the last row of another. You know this as "never filter or
   epoch across a subject boundary".
2. *The checker describes; the caller decides.* `run_checks` returns results for everything it
   looked at. `ingest` reads the severities and decides whether a table gets written. If you find
   yourself sorting, dropping or raising inside `run_checks`, the two roles have merged.

For idempotence, ask of every value you write to a file: is this a function of the input bytes and
the code, or of *when and where* I ran?

**Challenge.** Each contract sentence is one rule; write it as "which rows are **valid**". Think
about what a comparison returns when one side could not be parsed. Two sentences in the contract are
not about rows at all — what are they about, and can a row be "the offending row" for them?
