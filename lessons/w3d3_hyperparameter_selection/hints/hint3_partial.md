# Hint 3 - partial implementation (w3d3)

```python
def nested_estimate(estimator_factory, candidates, tidy, folds, metric, feature_columns,
                    label_column="anomaly", group_column="experiment_id", rule="max", complexity=None):
    if len(folds) < 3:
        raise ValueError("nested validation needs at least three folds")   # inner search needs two
    outer_scores, chosen_params, inner_best = [], [], []
    for k, outer in enumerate(folds):
        inner_folds = [f for j, f in enumerate(folds) if j != k]
        trials = grouped_search(estimator_factory, candidates, tidy, inner_folds, metric,
                                feature_columns, label_column, group_column)
        chosen = select_best(trials, rule, complexity)
        train_groups = [g for f in inner_folds for g in f]
        score = ...        # refit chosen["params"] on train_groups, score the outer fold
        outer_scores.append(score)
        chosen_params.append(chosen["params"])
        inner_best.append(chosen["mean"])
    return {...}           # which fields does the docstring promise?
```

```python
def frozen_threshold_evaluation(dev_scores, dev_labels, test_scores, test_labels, rule="best_f1", budget=None):
    threshold = select_threshold(dev_scores, dev_labels, rule, budget)   # dev only
    return {"threshold": threshold, "rule": rule,
            "dev": evaluate_at_threshold(dev_scores, dev_labels, threshold),
            "test": evaluate_at_threshold(test_scores, test_labels, threshold)}
```

Still yours: the search loop, both selection rules with their tie-breaks, the two threshold rules, and
in the challenge, the selection rule itself and the nested estimate over the recorded folds.
