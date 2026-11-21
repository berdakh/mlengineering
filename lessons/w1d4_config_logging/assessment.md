# W1D4 assessment

Write answers in your own words (2–6 sentences each unless stated) **before** opening
`solutions/lessons/w1d4_config_logging/assessment_answers.md`. Suggested location:
`progress/journal/w1d4_assessment.md`.

## A. Reasoning questions

**A1.** A config loader is written as `seed = cfg.get("split", {}).get("seed", 7)` for every key.
Describe a concrete sequence of events in which this produces a wrong *published* number without
any error or warning. What property of the loader would have prevented it?

**A2.** Your run directory contains `config.json`, and the repository contains
`configs/base.toml` at the recorded git commit. Give two situations in which these two disagree
about a value, and say which one you trust and why.

**A3.** A teammate adds `logging.basicConfig(level=logging.INFO)` at the top of
`pumpwatch/features.py` "so that the logs show up in my notebook". What breaks, for whom, and what
should they do instead (two acceptable alternatives)?

**A4.** With the base config, ten split seeds give F1 between 0.778 and 0.930 (s.d. 0.044) on the
synthetic pump data. You change one feature and, with seed 7, F1 moves from 0.909 to 0.930.
What can you conclude? What is the minimal additional evidence you would collect, and how does
today's work make collecting it cheap?

**A5.** Two runs have identical `config.json` and identical `git_commit`, yet different
`metrics.json`. List, in the order you would check them, the remaining explanations, and name the
recorded field (or the absence of one) relevant to each.

**A6.** Where should each of these live, and why: (i) the regularisation strength `C`;
(ii) an AWS access key for the bucket holding training data; (iii) the band edges of the
high-frequency feature (70–110 Hz); (iv) the log level; (v) the URL of the production database
used by the deployed service?

## B. Design-choice explanation

**B1.** (8–12 sentences.) In the lab, console logs go to stderr at the configured level, the log
file is always written at DEBUG, and handlers are attached to the `pumpwatch` logger with
`propagate = False` rather than to the root logger. Defend or criticise this design. Your answer
must address: what a user piping the output sees; what a developer embedding `pumpwatch` in a
FastAPI service (W5) would want instead; and one cost of the chosen design.

## C. Interview rep (Python, 12 minutes, no assistance, no running code until the end)

You are given log lines in this format:

```
2026-11-21 20:08:55,740 INFO    pumpwatch.io | loaded data path=a.csv rows=38400 duration_ms=41
2026-11-21 20:08:55,931 WARNING pumpwatch.features | interpolating missing samples n_missing=38
2026-11-21 20:08:55,948 INFO    pumpwatch.split | split seed=7 duration_ms=12
```

Write `summarise(lines: list[str], k: int) -> dict` returning

```python
{"levels": {"INFO": 2, "WARNING": 1},
 "slowest": [("pumpwatch.io", 41), ("pumpwatch.split", 12)]}   # up to k (logger, duration_ms), slowest first
```

Lines without `duration_ms` do not appear in `slowest`. Malformed lines (no `|`) are skipped and
counted under `"levels"` as `"MALFORMED"`. State the time complexity in terms of the number of lines
*n* and *k*, and say what you would change if *n* were 10⁹ lines read from a stream.

Then (and only then) run your function on the three lines above. Self-score with the rubric.

## D. Rubric

Each open answer is scored 0–3. Record scores honestly; they feed the "review needed" flag, not a grade.

| Score | Meaning |
|---|---|
| 0 | Missing, or restates the question |
| 1 | A correct statement, but no mechanism (says *that*, not *why* or *how it fails*) |
| 2 | Correct mechanism and a concrete consequence; one relevant aspect missing or one imprecise claim |
| 3 | Correct mechanism, concrete consequence, the relevant trade-off or limit named, no incorrect claims |

Specific requirements for a 3:

- **A1** — names a silent-typo (or misplaced-section) scenario end to end *and* identifies "reject unknown keys" (not "be more careful").
- **A2** — both a command-line override and a post-run/uncommitted edit (or dirty tree); trusts the snapshot because it was written by the run from the resolved object.
- **A3** — root logger reconfigured at import for every host application (and `basicConfig` being a no-op if handlers already exist, so it does not even reliably help); alternatives: configure in the notebook/application, or a documented opt-in helper function.
- **A4** — "nothing yet"; paired comparison over the same set of seeds/splits; cost is one `--set split.seed=…` loop.
- **A5** — at least data content (`data_sha256`), library versions/platform (`environment.json`), uncommitted changes (dirty flag), and unrecorded residual nondeterminism; ordered sensibly (cheap, likely first).
- **A6** — all five placed with a reason; distinguishes experiment config, method constant promoted to config only when it is varied, deploy config, and secrets.
- **B1** — all three required aspects; at least one genuine cost (e.g. third-party warnings invisible in the file; host applications must re-enable propagation or call their own setup).
- **C** — correct output on the sample, single pass, `heapq.nlargest` or equivalent bounded heap with O(n log k), streaming answer does not hold all lines; malformed-line handling present. Score 2 if sorted everything (O(n log n)) but correct.

**Review-needed triggers:** any A-question at 0–1, B1 below 2, or C not finished in 15 minutes.
