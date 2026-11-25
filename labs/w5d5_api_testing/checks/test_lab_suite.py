"""Grades the learner's TEST SUITE (lab/tests/) by mutation, as in lesson w1d5.

    python -m pytest labs/w5d5_api_testing/checks -q
"""
import pytest

from bugs import BUGS

MAX_SECONDS = 30.0


def test_suite_passes_on_correct_service(grading):
    reference, _ = grading
    assert reference.passed, (
        "Your suite must pass against the correct service (pytest exit code "
        f"{reference.returncode}). It runs from a temporary directory with the network blocked: "
        "build bundles in tmp_path and use TestClient, not a running server.\n" + reference.output
    )


def test_suite_is_fast(grading):
    reference, _ = grading
    assert reference.seconds < MAX_SECONDS, f"suite took {reference.seconds:.1f} s (limit {MAX_SECONDS:.0f} s)"


@pytest.mark.parametrize("bug", BUGS, ids=[b.name for b in BUGS])
def test_suite_detects_bug(grading, bug):
    reference, runs = grading
    if not reference.passed:
        pytest.skip("suite does not pass on the correct service yet")
    run = runs[bug.name]
    if not run.failed_tests:
        pytest.fail(f"SURVIVED: {bug.name} - {bug.description}. Your tests still pass on this "
                    f"defective service (pytest exit code {run.returncode}).", pytrace=False)
