"""Functions extracted from the meters notebook."""
import pandas as pd


def load_readings(path):
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["day"] = df.timestamp.dt.date
    return df


def daily_totals(readings):
    return readings.groupby(["meter_id", "day"]).kwh.sum().reset_index()
