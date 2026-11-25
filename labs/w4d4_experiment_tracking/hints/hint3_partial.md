# Hint 3 — partial implementation (w4d4)

```python
def expand_sweep(spec):
    sweep = spec["sweep"]
    seeds = list(sweep.get("seeds", [0]))
    if sweep.get("mode", "grid") == "grid":
        grid = flatten(spec.get("grid", {}))
        keys = sorted(grid)
        points = [dict(zip(keys, values)) for values in itertools.product(*(grid[k] for k in keys))]
    else:
        ...  # _flatten_space, a seeded rng, n_samples draws of _sample
    configs = []
    for point in points:
        for seed in seeds:
            config = copy.deepcopy(spec.get("base", {}))
            for key, value in point.items():
                set_dotted(config, key, value)
            config.update({"seed": seed, "task": sweep["task"], "sweep": sweep["name"]})
            configs.append(config)
    return configs
```

```python
# aggregate, the part that keeps sparse configurations
keys = ["sweep", *sorted(c for c in index.columns if c.startswith("param."))]
frame = index.copy()
for key in keys:
    frame[key] = frame[key].astype(object).where(frame[key].notna(), "-")
complete = frame[frame["status"] == "complete"]
stats = complete.groupby(keys, dropna=False)[f"metric.{metric}"].agg(
    n="count", mean="mean", sd="std", min="min", max="max").reset_index()
# ... then count non-complete runs per configuration and merge as "excluded"
```

Challenge:

```python
va = dict(zip(ga[pair_on], ga[f"metric.{metric}"]))
vb = dict(zip(gb[pair_on], gb[f"metric.{metric}"]))
shared = sorted(set(va) & set(vb))
diffs = [va[k] - vb[k] for k in shared]
```
