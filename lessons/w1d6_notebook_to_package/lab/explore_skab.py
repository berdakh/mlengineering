# ---
# exported from: skab_first_look_v2.ipynb   (cells were NOT last run top to bottom)
# run from the repository root, after:  python project/get_skab.py
#     python lessons/w1d6_notebook_to_package/lab/explore_skab.py
# ---

# %%
import glob
import os

import numpy as np
import pandas as pd

pd.set_option("display.width", 160)

# %%
NEW_NAMES = ["datetime", "accelerometer1_rms", "accelerometer2_rms", "current", "pressure", "temperature",
             "thermocouple", "voltage", "flow_rate", "anomaly", "changepoint"]

# %% valve1
frames = []
files = sorted(glob.glob("data/raw/skab/valve1/*.csv"))
for i, f in enumerate(files):
    df = pd.read_csv(f, sep=";")
    df.columns = NEW_NAMES
    df["experiment_id"] = "valve1/" + str(i)
    df["family"] = "valve1"
    frames.append(df)
print("valve1", len(files))

# %% valve2
files = sorted(glob.glob("data/raw/skab/valve2/*.csv"))
for i, f in enumerate(files):
    df = pd.read_csv(f, sep=";")
    df.columns = NEW_NAMES
    df["experiment_id"] = "valve2/" + str(i)
    df["family"] = "valve2"
    frames.append(df)
print("valve2", len(files))

# %% other
files = sorted(glob.glob("data/raw/skab/other/*.csv"))
for i, f in enumerate(files):
    df = pd.read_csv(f, sep=";")
    df.columns = NEW_NAMES
    df["experiment_id"] = "other/" + str(i)
    df["family"] = "other"
    frames.append(df)
print("other", len(files))

# %% normal data - no label columns in this one
free = pd.read_csv("data/raw/skab/anomaly-free/anomaly-free.csv", sep=";")
free.columns = NEW_NAMES[:9]
free["experiment_id"] = "anomaly-free/anomaly-free"
free["family"] = "anomaly-free"
frames.append(free)

# %%
all_df = pd.concat(frames)
all_df["datetime"] = pd.to_datetime(all_df["datetime"])
print(all_df.shape)

# %% clean up
all_df = all_df.dropna()
all_df = all_df.sort_values("datetime").reset_index(drop=True)
all_df["t"] = all_df.index
print(all_df.shape)

# %% how many experiments, how long
print("experiments:", all_df.experiment_id.nunique())
print(all_df.groupby("family").experiment_id.nunique())
n = all_df.groupby("experiment_id").size()
print("rows per experiment: min %d median %d max %d" % (n.min(), n.median(), n.max()))

# %% anomaly fraction
print("anomaly fraction overall: %.3f" % all_df.anomaly.mean())
print(all_df.groupby("family").anomaly.mean().round(3))

# %% look at one experiment  (the one with the long gap?)
df = all_df[all_df.experiment_id == "other/2"]
dt = df.datetime.diff().dt.total_seconds()
print("other/2 rows", len(df), "max gap s", dt.max())

# %% sampling interval - everything
dt = all_df.datetime.diff().dt.total_seconds()
print("median dt", dt.median(), "max dt", dt.max(), "n gaps > 5 s:", int((dt > 5).sum()))

# %% sensor means, normal vs anomalous
sens = NEW_NAMES[1:9]
print(all_df.groupby("anomaly")[sens].mean().round(3).T)

# %% z-score against "normal" - uses df from the cell above!
mu = df[sens].mean()
sd = df[sens].std()
z = (all_df[sens] - mu) / sd
all_df["zmax"] = z.abs().max(axis=1)
print(all_df.groupby("anomaly").zmax.median().round(2))

# %% per-experiment table
rows = []
for e in all_df.experiment_id.unique():
    d = all_df[all_df.experiment_id == e]
    rows.append({"experiment_id": e, "n_rows": len(d), "anomaly_fraction": round(d.anomaly.mean(), 3),
                 "start": str(d.datetime.min()), "end": str(d.datetime.max())})
summary = pd.DataFrame(rows).sort_values("experiment_id")
print(summary.head(8).to_string(index=False))
print("...")
