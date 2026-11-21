# Hint 2 — approach

**Lab: `run_checks`.**

1. Check the column set first. If something is missing, return that single failing result: nothing
   else can be evaluated.
2. Build `groups = dict(tuple(tidy.groupby("experiment_id")))` once.
3. For each check, build a dict `offenders: experiment_id -> short description`, by looping over the
   groups. Empty dict → passed. Otherwise join the items into `detail`. One small helper turns
   `(name, offenders, severity)` into a `CheckResult`; every check then has the same shape.
4. Per-group computations you need:
   - duplicates: `g["datetime"].duplicated(keep=False)`
   - order: `g["datetime"].diff().dt.total_seconds() < 0` anywhere
   - gaps: the same diff `> 5`
   - stuck: longest run of equal consecutive values — find where the value changes
     (`x[1:] != x[:-1]`), take the positions of the changes, difference them
   - labels: `set(g[col].unique()) - {0, 1}`

**Lab: `ingest`.**

```
tidy   = load_raw(raw_dir)
report = summary of run_checks(tidy)          # plain dict, JSON-serialisable
write quality_report.json                     # always
if any failed error:  delete skab.csv / provenance.json if present; raise QualityError(report)
bytes  = tidy rendered to CSV in memory       # so you can hash exactly what you write
write skab.csv, then provenance.json (input hashes, output hash, MANIFEST fields, versions)
```

Write JSON with `sort_keys=True` and a trailing newline. No clock, no hostname, no absolute paths.

**Challenge.** Parse once at the top with `errors="coerce"` (`pd.to_numeric`, `pd.to_datetime(...,
format=...)`). For each row rule build a boolean Series `valid`; the failing ids are
`df.loc[~valid, "order_id"]`. Write validity as `parsed.notna() & condition` so that NaN is invalid.
The "if and only if" rule is an equality between two boolean Series. The two batch-level
expectations produce one result each, with a number or a date in `detail` instead of order ids.
