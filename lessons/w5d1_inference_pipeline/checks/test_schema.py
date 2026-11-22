"""The inference boundary: validate_input. SYNTHETIC data; behaviour from the module docstring."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from conftest import COLUMNS, make_run


def test_valid_input_is_accepted_and_typed(fg):
    df = make_run("a").astype({"datetime": str})
    out = fg.inference.validate_input(df)
    assert list(out.columns) == COLUMNS
    assert pd.api.types.is_datetime64_any_dtype(out["datetime"])
    assert all(out[c].dtype == np.float64 for c in COLUMNS[2:])
    assert len(out) == len(df)
    np.testing.assert_array_equal(out["flow_rate"].to_numpy(), df["flow_rate"].to_numpy())


def test_input_is_not_mutated(fg):
    df = make_run("a").astype({"datetime": str})
    before = df.copy()
    fg.inference.validate_input(df)
    pd.testing.assert_frame_equal(df, before)


def test_schema_error_is_a_value_error(fg):
    assert issubclass(fg.inference.SchemaError, ValueError)


@pytest.mark.parametrize("column", ["flow_rate", "run_id", "datetime"])
def test_missing_column_is_named(fg, column):
    df = make_run("a").drop(columns=[column])
    with pytest.raises(fg.inference.SchemaError, match=column):
        fg.inference.validate_input(df)


def test_unexpected_column_is_named(fg):
    df = make_run("a").assign(anomaly=0)          # labels must never reach the serving path
    with pytest.raises(fg.inference.SchemaError, match="anomaly"):
        fg.inference.validate_input(df)


def test_misordered_columns_are_refused_not_matched_by_position(fg):
    cols = list(COLUMNS)
    cols[-1], cols[-2] = cols[-2], cols[-1]        # voltage and flow_rate swapped
    df = make_run("a")[cols]
    with pytest.raises(fg.inference.SchemaError, match="(?i)order"):
        fg.inference.validate_input(df)


def test_no_rows_is_refused(fg):
    with pytest.raises(fg.inference.SchemaError):
        fg.inference.validate_input(make_run("a").iloc[:0])


def test_non_numeric_sensor_value_is_named(fg):
    df = make_run("a").astype({"pressure": object})
    df.loc[5, "pressure"] = "1,25"                 # a decimal comma from a locale-misconfigured exporter
    with pytest.raises(fg.inference.SchemaError, match="pressure"):
        fg.inference.validate_input(df)


def test_unparseable_datetime_is_named(fg):
    df = make_run("a").astype({"datetime": object})
    df.loc[3, "datetime"] = "not a time"
    with pytest.raises(fg.inference.SchemaError, match="datetime"):
        fg.inference.validate_input(df)


def test_missing_sensor_values_are_not_a_schema_error(fg):
    df = make_run("a")
    df.loc[10, "current"] = np.nan
    out = fg.inference.validate_input(df)
    assert np.isnan(out.loc[10, "current"])
