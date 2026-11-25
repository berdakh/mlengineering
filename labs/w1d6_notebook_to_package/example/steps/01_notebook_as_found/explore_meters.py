# exported from meters_quicklook.ipynb
# %%
import pandas as pd

df = pd.read_csv("meters.csv")

# %%
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["day"] = df.timestamp.dt.date

# %%
daily = df.groupby(["meter_id", "day"]).kwh.sum().reset_index()

# %% look at the big one
df = df[df.meter_id == "M2"]
print(df.kwh.describe().round(3).to_string())

# %% fleet numbers
print("fleet mean kwh per reading: %.3f" % df.kwh.mean())
peak = daily.sort_values("kwh").groupby("meter_id").tail(1).sort_values("meter_id")
print(peak.to_string(index=False))
