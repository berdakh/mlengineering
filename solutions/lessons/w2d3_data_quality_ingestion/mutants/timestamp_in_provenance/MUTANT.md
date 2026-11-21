# Mutant: timestamp_in_provenance

`provenance.json` records `created_at` with the wall-clock time of the run.

Why it is plausible: "when was this made" sounds like provenance. Why it is wrong here: the output is
no longer a function of the input, so a hash comparison can no longer answer "did anything change?".
Every rerun looks like a change and caches keyed on content are invalidated for nothing. The run time
belongs in the log or the run directory (w1d4), not in a content-addressed artefact.

Rejected by: `test_ingest_is_idempotent`.
