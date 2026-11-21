"""pandas equivalents of q4, q5 and q6. Fill in the three functions.

Inputs arrive exactly as SQLite returns them:

    readings    = SELECT * FROM readings_dedup   (reading_id, device_id, ts, ts_epoch, temperature, alert)
    calibration = SELECT * FROM calibration      (device_id, valid_from, valid_from_epoch, offset_c, alert_threshold_c)

Each function returns a DataFrame with the same columns as the matching query. Row order
does not matter. Do not modify the input frames in place. Try them interactively:

    python -c "
    import sqlite3, pandas as pd, sys
    sys.path.insert(0, 'lessons/w2d2_sql_windows_timeseries/lab')
    import pandas_equiv as pe
    con = sqlite3.connect('lessons/w2d2_sql_windows_timeseries/data/coldchain.db')
    readings = pd.read_sql_query('SELECT * FROM readings_dedup', con)
    print(pe.alert_episodes(readings).head())"
"""
from __future__ import annotations

import pandas as pd


def rolling_features(readings: pd.DataFrame) -> pd.DataFrame:
    """q4: columns reading_id, device_id, ts, temp_mean_30m, n_30m, delta_prev, gap_s."""
    raise NotImplementedError


def alert_episodes(readings: pd.DataFrame) -> pd.DataFrame:
    """q5: columns device_id, episode_no, start_ts, end_ts, n_samples, peak_temperature."""
    raise NotImplementedError


def asof_calibration(readings: pd.DataFrame, calibration: pd.DataFrame) -> pd.DataFrame:
    """q6: columns reading_id, device_id, ts, corrected_temperature, alert_threshold_c, over_threshold."""
    raise NotImplementedError
