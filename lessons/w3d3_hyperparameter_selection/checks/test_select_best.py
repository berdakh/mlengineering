"""select_best: the 'max' rule and the one-standard-error rule."""
import pytest


def trial(i, mean, se, size):
    return {"trial": i, "params": {"size": size}, "fold_scores": [mean] * 4, "mean": mean, "se": se}


TRIALS = [trial(0, 0.70, 0.02, 1), trial(1, 0.78, 0.02, 2), trial(2, 0.80, 0.03, 8),
          trial(3, 0.81, 0.02, 16), trial(4, 0.795, 0.02, 4)]


def size(params):
    return params["size"]


def test_max_rule_picks_the_highest_mean(sel):
    assert sel.select_best(TRIALS, "max")["trial"] == 3


def test_max_rule_breaks_ties_by_the_earliest_trial(sel):
    tied = [trial(0, 0.8, 0.01, 1), trial(1, 0.8, 0.01, 1)]
    assert sel.select_best(tied, "max")["trial"] == 0


def test_one_se_rule_prefers_the_simplest_trial_within_one_se_of_the_best(sel):
    # best mean 0.81 with SE 0.02 -> eligible: mean >= 0.79 -> trials 2 (size 8), 3 (16), 4 (4)
    assert sel.select_best(TRIALS, "one_se", size)["trial"] == 4


def test_one_se_uses_the_standard_error_of_the_best_trial(sel):
    trials = [trial(0, 0.70, 0.50, 1), trial(1, 0.80, 0.01, 9)]     # trial 0's own huge SE is irrelevant
    assert sel.select_best(trials, "one_se", size)["trial"] == 1


def test_one_se_never_returns_a_trial_outside_the_band(sel):
    assert sel.select_best(TRIALS, "one_se", size)["mean"] >= 0.81 - 0.02


def test_one_se_needs_a_complexity_function(sel):
    with pytest.raises(ValueError):
        sel.select_best(TRIALS, "one_se")


def test_unknown_rule_and_empty_input_are_errors(sel):
    with pytest.raises(ValueError):
        sel.select_best(TRIALS, "median")
    with pytest.raises(ValueError):
        sel.select_best([], "max")
