import pandas as pd
import pytest

from meterkit import daily_totals, mean_kwh, peak_days


@pytest.fixture
def readings():
    return pd.DataFrame({
        "meter_id": ["A", "A", "A", "B", "B"],
        "day": ["d1", "d1", "d2", "d1", "d2"],
        "kwh": [1.0, 2.0, 5.0, 10.0, 20.0],
    })


def test_mean_uses_every_meter(readings):
    assert mean_kwh(readings) == pytest.approx(7.6)


def test_daily_totals_and_peak(readings):
    daily = daily_totals(readings)
    assert daily.kwh.tolist() == [3.0, 5.0, 10.0, 20.0]
    assert peak_days(daily)[["meter_id", "day"]].values.tolist() == [["A", "d2"], ["B", "d2"]]
