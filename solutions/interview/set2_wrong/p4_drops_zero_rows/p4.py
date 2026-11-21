"""WRONG: groups by customer and snapshot date, so snapshot rows without tickets disappear, duplicate
snapshot rows collapse, and the result is no longer aligned to snapshots.index."""
import pandas as pd


def tickets_90d(tickets: pd.DataFrame, snapshots: pd.DataFrame) -> pd.Series:
    pairs = snapshots.merge(tickets.dropna(subset=["customer_id"]), on="customer_id")
    keep = (pairs["opened_at"] < pairs["snapshot_date"]) & (
        pairs["opened_at"] >= pairs["snapshot_date"] - pd.Timedelta(days=90))
    return pairs[keep].groupby(["customer_id", "snapshot_date"]).size()
