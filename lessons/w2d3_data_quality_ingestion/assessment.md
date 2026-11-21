# W2D3 assessment

Write answers before opening `solutions/lessons/w2d3_data_quality_ingestion/assessment_answers.md`.
Questions 1–3 are in the essential path (10 min); 4–5 and the interview rep are the extension.

## Reasoning questions

**Q1 (3–4 sentences).** The given `load_raw` preserves file order and does not drop duplicates. A
colleague proposes adding `.sort_values(["experiment_id", "datetime"]).drop_duplicates()` to it
"so the table is always clean". What is lost, and what would you do instead if duplicated rows
turned out to be common?

**Q2.** Classify each as *error* or *warning* for this project and give the one-sentence reason.
(a) 3 % of `thermocouple` values in one experiment are NaN. (b) An experiment has two anomalous
segments. (c) A file's timestamps are all exactly one hour later than its neighbours' (clock
change). (d) `voltage` is 0.0 for the last 400 rows of one experiment. (e) A new file contains a
ninth sensor column not in the schema.

**Q3.** Your ingest step is idempotent on your laptop. In CI, the SHA-256 of `skab.csv` differs from
yours although the raw hashes match. List three plausible causes in order of likelihood and how you
would discriminate between them.

**Q4 (design choice — defend it).** The reference writes `quality_report.json` even when ingestion
fails, but deletes any existing `skab.csv`. An alternative design keeps the last good table in place
so that downstream jobs "still have something to run on". Argue for one design for (i) a nightly
training pipeline and (ii) an online scoring service that reads reference statistics from the table.
State what each design must add to be safe.

**Q5 (challenge report).** Exchange is not possible in self-study, so score your own
`QUALITY_REPORT.md` against the rubric below, then compare with the reference report.

## Rubric (each item: met / partly / not met)

| Item | Met when |
|---|---|
| Q1 mechanism | Says the ordering and uniqueness checks become unfalsifiable and the upstream fault recurs unseen; notes that which duplicate survives is arbitrary |
| Q1 alternative | Proposes an explicit, named, counted repair step after detection (or fixing the source), not silence |
| Q2 classification | Reasons from "would a later step silently compute something false?", not from how alarming it looks; (c) and (e) get a nuanced answer |
| Q3 hypotheses | Names environment-dependent formatting/versions, ordering, and line endings/locale or equivalent; proposes a discriminating test for each (diff the files, compare provenance versions) |
| Q4 tradeoff | Distinguishes failing closed from failing stale; ties the choice to the consumer; adds the missing safeguard (staleness marker/alert, atomic promotion) |
| Q5 report | Counts and examples per rule; row defects separated from batch-level signals; one clear decision for tonight; asks the owner specific questions; no silent repair |

## Common wrong turns to check yourself against

- Treating severity as a ranking of how bad the data looks.
- Answering Q3 with "non-determinism" without a mechanism.
- Proposing to drop or impute in the loader.
- A report that lists defects with no decision and no request.

## Interview rep (10–15 min, spoken or written; strand: ML fundamentals / data)

> "You are building a failure-prediction model for a fleet of pumps. One vibration sensor's value
> is missing in about 8 % of rows. Walk me through how you decide what to do about it."

Conditions (Weeks 1–2): untimed first attempt, then read the rubric in the answers file and write a
second attempt. Aim for a structured answer of under three minutes. Do not start with an imputation
method.
