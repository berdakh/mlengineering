"""grouped_search: every trial recorded, folds respected, rows outside the folds never touched."""
import numpy as np
import pytest

import synth

COLUMNS = ["f0", "f1", "f2", "f3"]
CANDS = [{"column": c} for c in COLUMNS]


@pytest.fixture()
def data():
    # 8 development groups in 4 folds + 3 further groups (g08..g10) standing in for TEST experiments
    tidy = synth.make_tidy(n_groups=11, rows=120, seed=5, signal={"f1": 0.5, "f2": 1.0})
    return tidy, synth.folds_of(8, 4)


def run(sel, tidy, folds, cands=CANDS):
    return sel.grouped_search(synth.ColumnScorer, cands, tidy, folds, synth.auc, synth.FEATURES)


def test_every_trial_is_recorded_in_candidate_order(sel, data):
    tidy, folds = data
    trials = run(sel, tidy, folds)
    assert len(trials) == len(CANDS), "all trials must be returned, not only the winner"
    for i, (trial, cand) in enumerate(zip(trials, CANDS)):
        assert trial["trial"] == i and trial["params"] == cand
        assert len(trial["fold_scores"]) == len(folds)
        assert trial["mean"] == pytest.approx(np.mean(trial["fold_scores"]))
        assert trial["se"] == pytest.approx(np.std(trial["fold_scores"], ddof=1) / np.sqrt(len(folds)))


def test_fold_scores_equal_the_independent_oracle(sel, data):
    """Score k of a trial is the metric on fold k alone (not pooled, not on training rows)."""
    tidy, folds = data
    expected = synth.fold_auc_table(tidy, folds, COLUMNS)
    got = np.array([t["fold_scores"] for t in run(sel, tidy, folds)])
    np.testing.assert_allclose(got, expected, atol=1e-12)


def test_no_group_is_both_fitted_and_scored_by_the_same_model(sel, data):
    tidy, folds = data
    run(sel, tidy, folds)
    calls = list(synth.CALLS)
    assert calls, "the estimator returned by estimator_factory was never used"
    fitted = None
    for kind, groups in calls:
        if kind == "fit":
            fitted = groups
        else:
            assert fitted is not None, "predict_proba was called before fit"
            assert not (fitted & groups), (
                f"groups {sorted(fitted & groups)} were in the training rows AND the validation rows of one "
                "model: the inner folds are not grouped")


def test_each_validation_set_is_exactly_one_fold(sel, data):
    tidy, folds = data
    run(sel, tidy, folds)
    as_codes = {frozenset(int(g[1:]) for g in fold) for fold in folds}
    scored = {groups for kind, groups in synth.CALLS if kind == "score"}
    assert scored == as_codes, "validation rows must be the given folds, one fold at a time"


def test_rows_outside_the_folds_are_never_fitted_or_scored(sel, data):
    """g08..g10 are in the table but in no fold - they stand for test experiments."""
    tidy, folds = data
    run(sel, tidy, folds)
    touched = set().union(*(groups for _, groups in synth.CALLS))
    assert touched <= set(range(8)), (
        f"groups {sorted(touched - set(range(8)))} are not in any fold but reached the search. "
        "'Everything except the validation fold' is not the training set.")
    for kind, groups in synth.CALLS:
        if kind == "fit":
            assert len(groups) == 6, "a model is fitted on all OTHER folds (6 of the 8 groups here)"


def test_search_is_deterministic(sel, data):
    tidy, folds = data
    assert run(sel, tidy, folds) == run(sel, tidy, folds)


def test_a_fresh_estimator_is_built_for_every_fit(sel, data):
    tidy, folds = data
    built = []

    def factory(**params):
        built.append(params)
        return synth.ColumnScorer(**params)

    sel.grouped_search(factory, CANDS, tidy, folds, synth.auc, synth.FEATURES)
    assert len(built) == len(CANDS) * len(folds)
