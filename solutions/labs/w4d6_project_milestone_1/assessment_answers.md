# W4D6 assessment: model answers

## Reasoning questions

**1.** You edit the manifest, for example to move an overlap group. `make evaluate` compares
`results.json` with its prerequisites: the tidy CSV and the code are unchanged, so make reports
nothing to do. The old report, built on the old split, remains. It carries the old manifest hash in
its Provenance section, but nobody compares hashes by eye. Later someone quotes the report as
describing the new split. The fix is to list `$(SPLITS)` as a prerequisite: every input that can
change an output must be a prerequisite.
*Wrong answers:*
* "make detects that the JSON content would change." It does not; it compares timestamps.
* "It errors." It does not; it silently does nothing.

**2.** A script can still compute numbers in the rendering step (a mean, a percentage, a ratio), or
read some values from another source. Those numbers cannot be traced to or diffed in the results
file. Requiring every shown number to be a stored value makes the results file the single source of
truth. You can then compare two versions of the evaluation by diffing JSON, and re-style the report
without any risk of changing a number.

**3.** Nothing reruns: `make` does not track variable values, so `results.json` is up to date by
timestamp and the report still shows 2000 replicates (stated in its Protocol table, which is the one
saving grace). To track parameters, write them to a stamp file, for example
`results/params.txt` containing `N_BOOT=... BURN_IN=... SEED=...`. Rewrite it only when its content
changes (compare first), and list it as a prerequisite of `results.json`. Alternatively, use a tool
that tracks content hashes (DVC, Snakemake).

**4.**
* Iterating over a `set`, whose order is arbitrary across processes for strings because of hash
  randomisation.
* A sort that is not stable or not total: ties in the sort key broken by input order that differs
  between runs, for example a dict built from a `groupby` without `sort=True`.

Also acceptable: a `sorted(..., key=...)` whose keys contain NaN. Fixes: sort with a total key (add
the name), and avoid iterating sets when building output.

**5.** In a separate, explicitly host-labelled artifact: the w4d5 decision memo, or a
`reports/benchmarks/<host>.json` produced by its own target, which is not part of the byte-identity
contract. Latency depends on the machine, its load and its thread settings (w4d5 saw 3.5 ms against
8 s). Inside the main report it would break reproducibility, and readers would take it as a
property of the model.

## Design choice: a model answer

Keep the stages.

* **Rebuild cost.** With intermediate files, make reruns only what is stale. Changing the report's
  wording takes a second instead of a full evaluation (about a minute here, hours on a large
  benchmark).
* **Reviewability.** `results.json` is a diffable record of every number. Comparing two evaluations
  is a JSON diff, and the traceability check (every table number appears in the JSON) is only
  possible with the file in between.
* **Diagnosis.** When something breaks, the stage boundary localises it. A wrong tidy table points to
  ingestion; right results with a wrong report point to rendering.

The "fewer moving parts" argument is real when stages are trivial, so do not split a five-line
script into three files. Here, though, each boundary carries information. The intermediates must be
build outputs (never edited, removed by `make clean`, git-ignored), or they become another source of
stale data.

*Weak answers* argue from code length alone, or keep the intermediates without saying how they are
kept fresh.

## Interview rep: rubric and worked answer

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Problem and stakeholder first | starts with models | brief | budget and who acts on alarms |
| Unit of independence | rows | "experiments" | experiments grouped by shared rows, 23 dev / 7 test clusters |
| Leakage prevention named | none | one | frozen split, burn-in calibration, dev-only choices, clock shortcut ruled out |
| Uncertainty | none | intervals mentioned | paired cluster bootstrap and Wilson, with what they omit |
| Result and decision | leaderboard | numbers | rule plus decision plus one test look |
| Reproducibility | none | "scripted" | one command, byte-identical, hashes |
| Time | > 6 min | 5-6 | 4-5 |

*Worked answer (about 4 minutes).*

"The goal was an alarm on a lab pump loop with at most one false alarm per eight hours. Each SKAB
file is one experiment, and some files share rows, so the independent unit is a group of
experiments: 23 clusters for development and 7 for test, frozen before any model work.

Every detector calibrates on the first 100 rows of a run, and those rows are excluded from scoring.
I also checked that elapsed time alone does not predict the label in my features. The protocol picks
operating points and the model on development data only, and looks at the test set once.

I compared four candidates with paired cluster-bootstrap intervals for PR-AUC against the simplest,
a single-sensor z-score, with a minimum practically important difference of 0.05 fixed in advance.
The supervised logistic model was +0.07, but its interval reached down to +0.02, so not shown to
matter. The isolation forest was shown worse. The rule took the simplest model. On test it caught 5
of 7 faults with no false alarms; with 7 events that recall interval runs from 0.36 to 0.92, and I
say so.

Misses were in valve1/8 and valve2/0. On development data the 'other' family is the weakest, with 3
of 12 detected at the strict budget. That is the next thing to work on.

All of it is one `make evaluate` from the raw files, and a clean rebuild is byte-identical; the
report carries the hashes of the manifest and the data."
