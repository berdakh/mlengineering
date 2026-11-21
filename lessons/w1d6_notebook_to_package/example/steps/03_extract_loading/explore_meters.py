# exported from meters_quicklook.ipynb
# %%
from meterkit import daily_totals, load_readings

df = load_readings("meters.csv")

# %%
daily = daily_totals(df)

# %% look at the big one
df = df[df.meter_id == "M2"]
print(df.kwh.describe().round(3).to_string())

# %% fleet numbers
print("fleet mean kwh per reading: %.3f" % df.kwh.mean())
peak = daily.sort_values("kwh").groupby("meter_id").tail(1).sort_values("meter_id")
print(peak.to_string(index=False))
