"""The feature query must be correct AND must not read anything later than each label's timestamp."""
from __future__ import annotations

import sqlite3

import oracle
import pandas as pd
import pytest
import wbsql

FEATURES = ["last_temperature", "mean_temp_60m", "n_alerts_24h", "seconds_since_fault", "status_at_label"]


@pytest.mark.parametrize("which", ["shipped", "reseeded"])
def test_features_match_specification(feature_sql, databases, which):
    con = wbsql.connect_readonly(databases[which])
    try:
        got = wbsql.run_sql(con, feature_sql)
        wbsql.assert_same_table(got, oracle.label_features(con), ["label_id"], "features.sql")
    finally:
        con.close()


def test_one_row_per_label_even_without_history(feature_sql, databases):
    """A label with no earlier readings or events must still produce a row (with NULL / 0 features)."""
    con = sqlite3.connect(databases["scratch"])
    try:
        con.execute("INSERT INTO devices VALUES ('D99', 'north')")
        con.execute("INSERT INTO maintenance_labels VALUES (9001, 'D99', '2026-03-02 00:00:00', 1772409600, 0)")
        got = wbsql.run_sql(con, feature_sql)
        row = got[got["label_id"] == 9001]
        assert len(row) == 1, "a label whose device has no readings or events must still appear exactly once"
        assert int(row["n_alerts_24h"].iloc[0]) == 0, "n_alerts_24h is a count: 0 when there is nothing to count"
        for column in ("last_temperature", "mean_temp_60m", "seconds_since_fault", "status_at_label"):
            assert pd.isna(row[column].iloc[0]), f"{column} must be NULL when there is no history"
    finally:
        con.rollback()
        con.close()


def test_features_do_not_change_when_the_future_changes(feature_sql, databases):
    """Rewrite everything after each label's timestamp; that label's features must not move.

    This is the definition of point-in-time correctness, tested directly: a feature that
    is a function of the past only is invariant to any edit of the future.
    """
    con = sqlite3.connect(databases["scratch"])
    try:
        baseline = wbsql.run_sql(con, feature_sql).set_index("label_id")
        labels = con.execute("SELECT label_id, device_id, label_ts_epoch FROM maintenance_labels").fetchall()
        leaked: dict[str, int] = {}
        for label_id, device, t in labels:
            con.execute("UPDATE sensor_readings SET temperature = temperature + 50, alert = 1 "
                        "WHERE device_id = ? AND ts_epoch > ?", (device, t))
            con.execute("UPDATE device_status_events SET status = 'fault' WHERE device_id = ? AND ts_epoch > ?",
                        (device, t))
            con.execute("INSERT INTO sensor_readings VALUES (?, ?, 'x', ?, 99.0, 1)", (10_000_000 + label_id, device, t + 1))
            con.execute("INSERT INTO device_status_events VALUES (?, ?, 'x', ?, 'fault')", (10_000_000 + label_id, device, t + 1))
            after = wbsql.run_sql(con, feature_sql).set_index("label_id")
            con.rollback()
            for column in FEATURES:
                a, b = baseline.loc[label_id, column], after.loc[label_id, column]
                same = (pd.isna(a) and pd.isna(b)) or (not pd.isna(a) and not pd.isna(b) and (
                    abs(float(a) - float(b)) < 1e-9 if column != "status_at_label" else a == b))
                if not same:
                    leaked[column] = leaked.get(column, 0) + 1
        assert not leaked, (
            "these features changed when only rows AFTER the label time were modified, so they read the future: "
            + ", ".join(f"{c} ({n} of {len(labels)} labels)" for c, n in sorted(leaked.items())))
    finally:
        con.rollback()
        con.close()
