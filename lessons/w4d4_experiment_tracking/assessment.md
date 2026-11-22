# Assessment — w4d4 experiment tracking

Answer in writing before opening `solutions/lessons/w4d4_experiment_tracking/assessment_answers.md`.

## A. Reasoning questions (about 15 minutes)

1. Two runs have identical `config.json` files but different `metrics.json`. List four explanations, and
   for each, which field of the run record would show it.

2. Why is the seed part of the run id, although it is not a hyperparameter you would select?

3. A teammate proposes keeping only `index.csv` in the repository and deleting run directories older than
   a month "to save space". What is lost, and what would you keep instead if space really is a problem?

4. The sweep table shows `n = 2, excluded = 1` for one configuration. What are the two possible states
   of the excluded run, and what should happen to each before the table is used for a decision?

5. In `skab_detector`, every configuration is scored on rows `t >= 200`, even those with a 100-row
   burn-in. What would go wrong if each configuration were scored from the end of its own burn-in?

## B. Design-choice explanation (about 10 minutes)

The registry in this lesson treats run directories as the source of truth and rebuilds the index from
them. MLflow treats its backend database as the source of truth. Give one situation in which each design
is the better choice, and one failure that each design makes easy.

## C. Rubric

| Criterion | Weak | Solid | Strong |
|---|---|---|---|
| Identity | "a unique name" | content hash of the config | hash of the *resolved* config, canonical form, seed included, why each matters |
| Provenance | config only | config + code version | config, code (with dirty flag), data fingerprint, environment, and what each catches |
| Completion | "it has metrics" | status file | status written last and atomically; partial vs failed handled differently |
| Aggregation | mean of everything | complete runs only | excluded counted, sparse parameters kept, n = 1 shown honestly |
| Reproduction | "rerun the script" | re-execute stored config | compare with tolerance; say what a mismatch would mean |

## D. Interview rep — Python, nested dicts and JSON (15 minutes, closed book)

Write two functions without pandas:

```python
def diff_configs(a: dict, b: dict) -> dict:
    """Dotted keys whose values differ between two nested configs.

    Returns {"changed": {key: (a_value, b_value)}, "only_a": {key: value}, "only_b": {key: value}}.
    Nested dicts are compared key by key; lists and scalars are compared as values.
    """

def best_per_group(records: list[dict], group_by: list[str], metric: str) -> dict:
    """records are run records like {"config": {...}, "metrics": {...}, "status": "complete"}.
    group_by are dotted config keys. Return {group tuple: record} with the highest metric per group,
    considering complete runs only; ties keep the record that appears first."""
```

Examples to test your code against:

```python
diff_configs({"model": {"alpha": 1.0, "kind": "ridge"}, "seed": 0},
             {"model": {"alpha": 2.0}, "seed": 0, "data": {"n": 5}})
# {"changed": {"model.alpha": (1.0, 2.0)}, "only_a": {"model.kind": "ridge"}, "only_b": {"data.n": 5}}
```

Then state the time complexity of each function. A reference with tests is in
`solutions/lessons/w4d4_experiment_tracking/interview_rep/config_diff.py`; run
`python solutions/lessons/w4d4_experiment_tracking/interview_rep/config_diff.py path/to/your_file.py`
to test your file after writing it.
