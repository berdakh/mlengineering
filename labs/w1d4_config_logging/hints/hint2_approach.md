# Hint 2 — suggested approach

**Lab**

1. `load_config`:
   - read the TOML into `raw` (a dict of dicts);
   - reject unknown *sections*; make `merged = {section: dict(raw.get(section, {}))}` for all four
     known sections so later code never needs `.get`;
   - for each override string: split on the first `=`, split the left side on the first `.`,
     convert the right side to a typed value, assign into `merged[section][key]`;
   - per section, compare `set(values)` with the dataclass field names
     (`dataclasses.fields(cls)`), check each value's type against the field's annotation, then
     construct the dataclass; a missing required field is the one remaining way construction can fail;
   - finally run the range checks on the built object.
2. Typed override values: the simplest consistent rule is "the right-hand side is a TOML value", which
   you can parse by handing `tomllib.loads` a one-line document. Decide what happens when that
   parse fails (reject, or treat as a plain string) and document it.
3. CLI order of operations: parse args → load config (on error: message to stderr, return 2) →
   create run directory → configure logging (now the log file path exists) → write `config.json` →
   compute → write `metrics.json`, `environment.json` → print JSON → return 0.
4. Logging setup: get the logger named after your package, set it to DEBUG, add a
   `StreamHandler(sys.stderr)` at the configured level and a `FileHandler` at DEBUG, set
   `propagate = False`. Remove existing handlers first so the function can be called twice.
5. Run id: a UTC timestamp alone collides within a second. Either add something that differs
   (a short hash, a counter) or create with `mkdir(exist_ok=False)` and retry with a suffix.

**Challenge**

1. `load_run(path)` → dict with the three parsed JSON files, raising one custom exception if the
   directory or any file is missing.
2. `flatten(nested)` → `{"split.seed": 7, ...}`; write it recursively so depth does not matter.
3. `config_diff`: iterate over the union of flattened keys; keep those whose values differ.
4. `metric_diff`: iterate over the intersection of metric names; keep those where both values are
   numbers (mind that `bool` is a subclass of `int`); `delta = b - a`.
5. `same_data`: compare the content hashes recorded in `environment.json`.
6. Wire a second sub-parser; catch your exception in the command function and return 2.
