# Hint 2 — approach (w4d4)

* `config_hash`: `json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)` then
  `hashlib.sha256(...).hexdigest()[:12]`.
* `expand_sweep`: build a list of *points* (dicts of dotted key -> value) first, then a double loop
  `for point in points: for seed in seeds:` that deep-copies the base.
* `_status`: read `status.json` with `_read_json`; `None` means partial.
* `execute`: compute the id, check `_status`, `mkdir(exist_ok=True)`, `unlink(missing_ok=True)` the two
  completion files, write, run, write. Catch `Exception`, not `BaseException` (let Ctrl-C stop the sweep).
* `build_index`: `for run_dir in sorted(runs_dir.iterdir())`, skip anything without a readable
  `config.json`, `flatten(config)` for the `param.*` columns.
* `aggregate`: split the index into complete and non-complete rows, group both by the same keys, merge
  the counts. Replace NaN in key columns with a sentinel before grouping.
* `reproduce`: `get_task(config["task"])(config)` and `math.isclose` per key.

Challenge: select each group, check `group[pair_on].duplicated().any()`, build `{seed: value}` dicts,
intersect their keys.
