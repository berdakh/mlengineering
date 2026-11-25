# Mutant: silent_repair

`run_checks` sorts by time and drops duplicate timestamps before evaluating anything, "so the checks
see a well-formed table". The ordering and uniqueness checks can then never fail.

Why it is plausible: sorting and de-duplicating is the reflex from notebook work, and the resulting
table looks fine. Why it is wrong: the defect is hidden, not handled. Which of two conflicting rows was
kept is arbitrary, and nobody learns that the logger is writing retries. Validation must look at the
data as it arrived; repair, if any, is a separate, recorded decision.

Rejected by: `test_each_defect_is_reported...[duplicate_timestamps]`, `[unsorted_rows]`,
`test_errors_stop_the_pipeline_loudly`.
