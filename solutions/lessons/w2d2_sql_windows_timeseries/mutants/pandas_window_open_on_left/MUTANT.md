# Mutant: pandas_window_open_on_left

`rolling_features` uses `rolling("1800s")` with pandas' default `closed="right"`, i.e. the window
`(t - 30 min, t]`. SQL's `RANGE BETWEEN 1800 PRECEDING AND CURRENT ROW` is `[t - 30 min, t]`. The two
differ only for a reading that lies *exactly* 1800 s before another, so the functions agree on almost
every row. The SQL-versus-pandas agreement check exists to catch this kind of boundary disagreement.

Changed file: `pandas_equiv.py`
