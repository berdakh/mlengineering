"""Worked example, part 1: three ways a CSV is read 'successfully' and wrongly.

Runs offline on a tiny inline file (SYNTHETIC, written for this example).

    python labs/w2d3_data_quality_ingestion/example/parsing_pitfalls.py
"""
from __future__ import annotations

import io

import pandas as pd

# A European export: semicolon separator, decimal comma, day-first dates.
TEXT = """datetime;Pressure;Voltage;anomaly
03/04/2020 10:14:33;0,054;233,1;0
03/04/2020 10:14:34;0,382;236,0;0
13/04/2020 10:14:35;1,120;231,7;1
"""


def show(title: str, df: pd.DataFrame) -> None:
    print(f"--- {title}")
    print(f"shape={df.shape}  dtypes={ {c: str(t) for c, t in df.dtypes.items()} }")
    print(df.head(3).to_string(index=False), "\n")


# 1. Defaults: no exception, one column. Shape is the cheapest check there is.
show("defaults (sep=',')", pd.read_csv(io.StringIO(TEXT)))

# 2. Right separator, wrong decimal: numbers arrive as strings. Still no exception.
df = pd.read_csv(io.StringIO(TEXT), sep=";")
show("sep=';' only", df)

# 3. Let pandas guess the dates one cell at a time: rows 1-2 are read month-first,
#    row 3 cannot be (month 13) and is read day-first. One column, two conventions.
guessed = df["datetime"].map(pd.to_datetime)
print("--- per-cell date guessing")
print(guessed.to_string(index=False), "\n")

# 4. Everything explicit. A cell that does not match the format becomes NaT/NaN,
#    which a quality check can count, instead of becoming a different valid value.
raw = pd.read_csv(io.StringIO(TEXT), sep=";", dtype=str, keep_default_na=False)
clean = pd.DataFrame({
    "datetime": pd.to_datetime(raw["datetime"], format="%d/%m/%Y %H:%M:%S", errors="coerce"),
    "pressure": pd.to_numeric(raw["Pressure"].str.replace(",", ".", regex=False), errors="coerce"),
    "voltage": pd.to_numeric(raw["Voltage"].str.replace(",", ".", regex=False), errors="coerce"),
    "anomaly": pd.to_numeric(raw["anomaly"], errors="coerce").astype("int64"),
})
show("explicit separator, decimal, format, dtypes", clean)
print("seconds between rows:", clean["datetime"].diff().dt.total_seconds().tolist())
