"""Each lab query must return the specified table on the shipped database and on a re-seeded one."""
from __future__ import annotations

import oracle
import pytest
import wbsql

CASES = [
    ("q1_latest_status.sql", oracle.latest_status, ["device_id"]),
    ("q2_time_in_state.sql", oracle.time_in_state, ["device_id", "status"]),
    ("q3_running_alerts.sql", oracle.running_alerts, ["reading_id"]),
    ("q4_rolling_features.sql", oracle.rolling_features, ["reading_id"]),
    ("q5_alert_episodes.sql", oracle.alert_episodes, ["device_id", "episode_no"]),
    ("q6_asof_calibration.sql", oracle.asof_calibration, ["reading_id"]),
]


@pytest.mark.parametrize("filename,expected_fn,keys", CASES, ids=[c[0][:2] for c in CASES])
def test_query_matches_specification(target, con, filename, expected_fn, keys):
    sql = wbsql.read_sql_file(target / "queries" / filename)
    got = wbsql.run_sql(con, sql)
    wbsql.assert_same_table(got, expected_fn(con), keys, filename)


def test_time_in_state_accounts_for_every_second(target, con):
    """Per device the state durations must add up to the span from its first event to the report end."""
    got = wbsql.run_sql(con, wbsql.read_sql_file(target / "queries" / "q2_time_in_state.sql"))
    assert {"device_id", "total_seconds"} <= set(got.columns), "q2 needs device_id and total_seconds"
    totals = got.groupby("device_id")["total_seconds"].sum()
    first = dict(con.execute("SELECT device_id, MIN(ts_epoch) FROM device_status_events GROUP BY device_id"))
    for device, start in first.items():
        assert totals.get(device) == oracle.REPORT_END_EPOCH - start, (
            f"q2: durations for {device} do not sum to the time between its first event and the report end")
