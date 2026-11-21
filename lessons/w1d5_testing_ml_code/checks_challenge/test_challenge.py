"""Grades the challenge: (1) your repaired implementation, (2) your tests, by mutation.

    python -m pytest lessons/w1d5_testing_ml_code/checks_challenge -q
"""
import numpy as np
import pytest

from bugs import BUGS


def _norm(events):
    return [(int(a), int(b)) for a, b in events]


# ---- (1) the repaired implementation --------------------------------------------------

def test_implementation_matches_specification_on_random_scores(submitted, reference):
    rng = np.random.default_rng(2026)
    for case in range(400):
        n = int(rng.integers(0, 40))
        score = np.round(rng.normal(0.0, 1.0, n), 1)  # rounding produces exact ties with the threshold
        if n and case % 3 == 0:
            score[rng.integers(0, n, size=max(1, n // 8))] = np.nan
        kwargs = dict(threshold=float(rng.choice([0.0, 0.5, -0.3])),
                      min_samples=int(rng.integers(1, 5)), merge_gap=int(rng.integers(0, 4)))
        expected = reference(score, **kwargs)
        got = _norm(submitted(score.copy(), **kwargs))
        assert got == expected, f"score={score.tolist()} {kwargs}: expected {expected}, got {got}"


def test_implementation_accepts_lists_and_empty_input(submitted):
    assert _norm(submitted([0, 2, 2, 0], threshold=1)) == [(1, 3)]
    assert _norm(submitted([], threshold=1)) == []


@pytest.mark.parametrize("kwargs", [dict(min_samples=0), dict(merge_gap=-1)])
def test_implementation_rejects_invalid_parameters(submitted, kwargs):
    with pytest.raises(ValueError):
        submitted([0.0, 2.0, 0.0], threshold=1.0, **kwargs)


def test_implementation_rejects_2d_input(submitted):
    with pytest.raises(ValueError):
        submitted(np.zeros((4, 2)), threshold=1.0)


# ---- (2) the test suite ---------------------------------------------------------------

def test_suite_passes_on_correct_implementation(grading):
    ref_run, _ = grading
    assert ref_run.passed, (
        "Your tests must pass against an implementation that follows the specification. "
        "If they fail here, a test encodes behaviour the spec does not promise.\n" + ref_run.output
    )


def test_suite_is_fast(grading):
    assert grading[0].seconds < 10.0


@pytest.mark.parametrize("bug", BUGS, ids=[b.name for b in BUGS])
def test_suite_detects_bug(grading, bug):
    ref_run, runs = grading
    if not ref_run.passed:
        pytest.skip("suite does not pass on the correct implementation yet")
    if not runs[bug.name].failed_tests:
        pytest.fail(f"SURVIVED: {bug.name} - {bug.description}.", pytrace=False)
