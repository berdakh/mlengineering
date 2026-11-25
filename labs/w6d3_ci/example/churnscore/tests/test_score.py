import pytest

from churnscore import churn_risk


def test_bounds():
    assert 0.0 < churn_risk(0, 0) < 1.0


def test_monotone():
    assert churn_risk(12, 3) > churn_risk(12, 1)
    assert churn_risk(36, 1) < churn_risk(6, 1)


def test_rejects_negative():
    with pytest.raises(ValueError):
        churn_risk(-1, 0)
