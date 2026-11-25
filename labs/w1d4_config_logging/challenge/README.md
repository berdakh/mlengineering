# W1D4 independent challenge — `pumpwatch compare-runs`

**Time:** about 40 minutes · **Assistance:** none intended (hints exist; using them changes how you
record this unit) · **Solution:** not in this directory.

## Situation

Two training runs disagree. Before anyone discusses models, you want a tool that answers, from the
run directories alone: *what was configured differently, how did the metrics move, and was it even
the same data?*

## Task

Copy your finished lab package into this directory and extend it:

```bash
cp -r labs/w1d4_config_logging/lab/. labs/w1d4_config_logging/challenge/
```

Add a second sub-command:

```
pumpwatch compare-runs RUN_A RUN_B
```

which reads the two run directories written by `pumpwatch train` and prints one JSON object to
stdout:

```json
{
  "config_diff": {"split.seed": {"a": 7, "b": 3}},
  "metric_diff": {"auc": {"a": 0.9992, "b": 1.0, "delta": 0.0008}},
  "same_data": true
}
```

## Acceptance criteria

1. `config_diff` contains exactly the configuration values that differ, keyed by **dotted name**
   (`section.key`), each with the value in run A (`a`) and in run B (`b`). Identical configs give `{}`.
2. `metric_diff` has one entry per **numeric** metric present in both runs, with `a`, `b` and
   `delta`. You must decide and document the sign convention; the checks expect the convention under
   which a positive `delta` means the metric is higher in RUN_B. Non-numeric metrics
   (e.g. `test_units`) are not differenced.
3. `same_data` is `true` exactly when both runs read byte-identical data — regardless of where the
   file was located — and `false` otherwise.
4. If either argument is not a complete run directory, the command exits non-zero with a one-line
   message on stderr, no traceback, and nothing on stdout.
5. `pumpwatch train` still passes the lab checks.
6. In `challenge/README_NOTES.md`, answer in 3–5 sentences: *under which values of `config_diff` and
   `same_data` is it legitimate to attribute a metric delta to a modelling change, and what would
   you still want to know?* (Graded with the assessment rubric, not by the checks.)

## Checks

```bash
python -m pytest labs/w1d4_config_logging/checks_challenge -q     # about 20 s
```

The checks train five small runs (including one on an identical copy of the data at another path and
one on a file edited in place) and grade only the command's output and exit codes.

## What this transfers

The lab had you *write* provenance. Here you *consume* it, which is where weaknesses in what you
recorded become visible. If your lab's `config.json` or `environment.json` lacks something this
command needs, fix the lab first — that is the intended lesson, not an obstacle.
