# SYNTHETIC data. The "before" state: works only when run from the repository root,
# because the data path is relative to the current working directory.
import pandas as pd

df = pd.read_csv("labs/w1d3_package_structure/example/data/room_temps.csv")
df = df.dropna()
for r in df.room.unique():
    d = df[df.room == r]
    print(r, round(d.temp_c.mean(), 2), round(d.temp_c.max() - d.temp_c.min(), 2), len(d))
