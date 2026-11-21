"""WRONG: `<=` counts tickets opened at the snapshot instant itself: information not yet available at prediction time."""
import pandas as pd


def tickets_90d(tickets: pd.DataFrame, snapshots: pd.DataFrame) -> pd.Series:
    # Give every snapshot row a positional id: the caller's index may be non-unique or unordered.
    snaps = snapshots[["customer_id", "snapshot_date"]].reset_index(drop=True)
    snaps["_row"] = range(len(snaps))
    pairs = snaps.merge(tickets[["customer_id", "opened_at"]].dropna(subset=["customer_id"]),
                        on="customer_id", how="inner")
    in_window = (pairs["opened_at"] <= pairs["snapshot_date"]) & (
        pairs["opened_at"] >= pairs["snapshot_date"] - pd.Timedelta(days=90))
    counts = pairs.loc[in_window].groupby("_row").size()
    out = counts.reindex(range(len(snaps)), fill_value=0).astype("int64")
    out.index = snapshots.index
    return out.rename("tickets_90d")
