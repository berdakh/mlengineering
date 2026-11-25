"""The pandas functions must reproduce q4, q5 and q6, and agree with the learner's own SQL."""
from __future__ import annotations

import oracle
import pandas as pd
import pytest
import wbsql

CASES = [
    ("rolling_features", "q4_rolling_features.sql", oracle.rolling_features, ["reading_id"], ("readings",)),
    ("alert_episodes", "q5_alert_episodes.sql", oracle.alert_episodes, ["device_id", "episode_no"], ("readings",)),
    ("asof_calibration", "q6_asof_calibration.sql", oracle.asof_calibration, ["reading_id"], ("readings", "calibration")),
]


def call(pandas_module, name, frames, args):
    assert hasattr(pandas_module, name), f"pandas_equiv.py must define {name}()"
    inputs = [frames[a].copy() for a in args]
    try:
        result = getattr(pandas_module, name)(*inputs)
    except NotImplementedError:
        pytest.fail(f"pandas_equiv.{name} is not implemented yet", pytrace=False)
    for original, passed in zip(args, inputs):
        pd.testing.assert_frame_equal(frames[original], passed, obj=f"{name} must not modify its input '{original}'")
    return result


@pytest.mark.parametrize("name,filename,expected_fn,keys,args", CASES, ids=[c[0] for c in CASES])
def test_pandas_matches_specification(pandas_module, frames, con, name, filename, expected_fn, keys, args):
    got = call(pandas_module, name, frames, args)
    wbsql.assert_same_table(got, expected_fn(con), keys, f"pandas_equiv.{name}")


@pytest.mark.parametrize("name,filename,expected_fn,keys,args", CASES, ids=[c[0] for c in CASES])
def test_pandas_agrees_with_your_sql(target, pandas_module, frames, con, name, filename, expected_fn, keys, args):
    from_sql = wbsql.run_sql(con, wbsql.read_sql_file(target / "queries" / filename))
    from_pandas = call(pandas_module, name, frames, args)
    wbsql.assert_same_table(from_pandas, from_sql.to_dict("records"), keys, f"pandas_equiv.{name} versus {filename}")
