"""nested_estimate: the outer fold takes no part in choosing the model that is scored on it."""
import numpy as np
import pytest

import synth

COLUMNS = ["f0", "f1", "f2", "f3", "f4", "f5"]
CANDS = [{"column": c} for c in COLUMNS]


def nested(sel, tidy, folds, cands=CANDS, factory=synth.ColumnScorer):
    return sel.nested_estimate(factory, cands, tidy, folds, synth.auc, synth.FEATURES)


def test_result_has_the_documented_fields(sel):
    tidy, folds = synth.make_tidy(8, 100, seed=2, signal={"f2": 0.8}), synth.folds_of(8, 4)
    out = nested(sel, tidy, folds)
    assert len(out["outer_scores"]) == 4 and len(out["chosen_params"]) == 4 and len(out["inner_best"]) == 4
    assert out["mean"] == pytest.approx(np.mean(out["outer_scores"]))
    assert out["se"] == pytest.approx(np.std(out["outer_scores"], ddof=1) / 2.0)


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_matches_the_independent_oracle(sel, seed):
    """Weak, similar signals in several columns: which column wins depends on which folds you look at."""
    tidy = synth.make_tidy(8, 80, seed=seed, signal={"f1": 0.30, "f2": 0.35, "f3": 0.32, "f4": 0.28})
    folds = synth.folds_of(8, 4)
    scores, chosen = synth.oracle_nested(synth.fold_auc_table(tidy, folds, COLUMNS))
    out = nested(sel, tidy, folds)
    assert [p["column"] for p in out["chosen_params"]] == [COLUMNS[i] for i in chosen], (
        "the candidate chosen for an outer fold must be the inner-search winner on the OTHER folds")
    np.testing.assert_allclose(out["outer_scores"], scores, atol=1e-12)


def test_poisoned_outer_fold_cannot_influence_its_own_selection(sel):
    """In fold 0 only, column f5 IS the label. Anywhere else it is noise. f1 carries a modest real signal.

    A procedure that lets fold 0 vote on its own model picks f5 for fold 0 and reports a perfect score.
    """
    tidy = synth.make_tidy(8, 300, seed=11, signal={"f1": 0.45})
    folds = synth.folds_of(8, 4)
    poisoned = tidy["experiment_id"].isin(folds[0])
    tidy.loc[poisoned, "f5"] = 6.0 * tidy.loc[poisoned, "anomaly"] - 3.0
    out = nested(sel, tidy, folds, cands=[{"column": "f1"}, {"column": "f5"}])
    assert out["chosen_params"][0] == {"column": "f1"}, "fold 0 leaked into the search that chose its model"
    assert out["outer_scores"][0] < 0.95


def test_inner_search_never_scores_or_fits_the_outer_fold_before_the_final_refit(sel):
    """Count how often each group is scored: 3 inner validations per candidate where it is an inner
    fold (3 outer iterations) and exactly once per outer iteration as the outer fold."""
    tidy, folds = synth.make_tidy(8, 60, seed=4, signal={"f2": 0.8}), synth.folds_of(8, 4)
    nested(sel, tidy, folds)
    n_scored = sum(1 for kind, groups in synth.CALLS if kind == "score" and 0 in groups)
    assert n_scored == 3 * len(CANDS) + 1, (
        f"group g00 was scored {n_scored} times; expected {3 * len(CANDS)} inner validations + 1 outer evaluation")
    fitted = None
    for kind, groups in synth.CALLS:
        if kind == "fit":
            fitted = groups
        else:
            assert not (fitted & groups)


def test_selection_optimism_is_visible_on_pure_noise_and_absent_from_the_nested_estimate(sel):
    """40 candidates that are all worthless. The best inner mean is well above chance by luck alone;
    the nested estimate of the procedure stays at chance. Averaged over 6 SYNTHETIC noise datasets."""
    cands = [{"seed": s} for s in range(40)]
    naive, honest = [], []
    for seed in range(6):
        tidy, folds = synth.make_tidy(8, 60, seed=100 + seed), synth.folds_of(8, 4)
        trials = sel.grouped_search(synth.ProjectionScorer, cands, tidy, folds, synth.auc, synth.FEATURES)
        naive.append(max(t["mean"] for t in trials))
        honest.append(nested(sel, tidy, folds, cands, synth.ProjectionScorer)["mean"])
    assert np.mean(naive) > 0.53, "the maximum of 40 noisy estimates should look better than chance"
    assert abs(np.mean(honest) - 0.5) < 0.03, (
        f"nested estimate on pure noise is {np.mean(honest):.3f}; it should be near 0.5. "
        "Reporting the winner's own search score is not an estimate of the procedure.")
    assert np.mean(naive) - np.mean(honest) > 0.03


def test_nested_needs_three_folds(sel):
    tidy = synth.make_tidy(4, 40, seed=0)
    with pytest.raises(ValueError):
        nested(sel, tidy, synth.folds_of(4, 2))
