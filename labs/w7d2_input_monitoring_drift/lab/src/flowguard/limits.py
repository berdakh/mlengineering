"""Physical sanity limits per sensor (the w5d4 data-dictionary ranges). SNAPSHOT; given to you.

A value outside these limits, or not finite, is a SCHEMA violation (a broken input: unit error, sentinel
such as -9999, sign error). It is counted on its own and excluded from distribution statistics, because
a single -9999 would otherwise dominate any drift statistic and hide what the other rows are doing.
"""
from __future__ import annotations

SENSOR_LIMITS: dict[str, tuple[float, float]] = {
    "accelerometer1_rms": (0.0, 10.0),      # g
    "accelerometer2_rms": (0.0, 10.0),      # g
    "current": (0.0, 50.0),                 # A
    "pressure": (-5.0, 20.0),               # bar
    "temperature": (-40.0, 200.0),          # deg C, motor body
    "thermocouple": (-40.0, 200.0),         # deg C, fluid
    "voltage": (0.0, 500.0),                # V
    "flow_rate": (0.0, 500.0),              # L/min
}
