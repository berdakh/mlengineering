"""Grades the learner's TEST SUITE (lab/tests/) by mutation.

    python -m pytest labs/w1d5_testing_ml_code/checks -q
"""
import pytest

from bugs import BUGS

MAX_SECONDS = 20.0


def test_suite_passes_on_correct_package(grading):
    reference, _ = grading
    assert reference.passed, (
        "Your suite must pass against the correct pumpwatch package (exit code "
        f"{reference.returncode}). Tests run from a temporary directory with no network: "
        "they must build their own data.\n" + reference.output
    )


def test_suite_is_fast(grading):
    reference, _ = grading
    assert reference.seconds < MAX_SECONDS, (
        f"suite took {reference.seconds:.1f} s; a unit suite that people run on every "
        f"change must stay under {MAX_SECONDS:.0f} s"
    )


@pytest.mark.parametrize("bug", BUGS, ids=[b.name for b in BUGS])
def test_suite_detects_bug(grading, bug):
    reference, runs = grading
    if not reference.passed:
        pytest.skip("suite does not pass on the correct package yet")
    run = runs[bug.name]
    if not run.failed_tests:
        pytest.fail(
            f"SURVIVED: {bug.name} - {bug.description}. Your tests still pass when the "
            f"package contains this defect (pytest exit code {run.returncode}).",
            pytrace=False,
        )
