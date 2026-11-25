# Hint 3 — partial implementation

Fragments, not a solution: the validation logic, the logging setup body, the environment
collection and the diff logic are left for you. Opening this hint means the unit counts as guided
practice for the parts shown.

## Lab

```python
# config.py
class ConfigError(ValueError):
    """A configuration problem the user can fix; the message names the dotted key."""

_SECTIONS = {"data": DataConfig, "split": SplitConfig, "model": ModelConfig, "logging": LoggingConfig}

def parse_override(text: str) -> tuple[str, str, object]:
    key, sep, raw = text.partition("=")
    section, dot, name = key.strip().partition(".")
    if not sep or not dot or not section or not name:
        raise ConfigError(f"override {text!r} must look like section.key=value")
    try:
        value = tomllib.loads(f"v = {raw}")["v"]      # "11" -> 11, "0.5" -> 0.5, '"x"' -> "x"
    except tomllib.TOMLDecodeError:
        value = raw.strip()                            # bare words / paths stay strings
    return section, name, value

def _build_section(name, cls, values):
    fields = {f.name: f for f in dataclasses.fields(cls)}
    unknown = sorted(set(values) - set(fields))
    if unknown:
        raise ConfigError(f"unknown configuration key: {name}.{unknown[0]}")
    ...   # type-check each value against fields[key].type, then construct cls(**kwargs)
```

Note: with `from __future__ import annotations`, `fields[key].type` is the *string* `"float"`, not
the class `float`.

```python
# cli.py - the order matters
def run_train(args) -> int:
    try:
        cfg = load_config(args.config, args.overrides)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    resolved = cfg.to_dict()
    run_dir = create_run_dir(args.run_dir, resolved)
    setup_logging(cfg.logging.level, run_dir / "train.log")
    write_json(run_dir / "config.json", resolved)
    ...
    print(json.dumps({"run_dir": str(run_dir), "metrics": metrics}, indent=2))
    return 0
```

```python
# runs.py
def create_run_dir(base, config: dict) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{stamp}-{config_fingerprint(config)}"     # fingerprint: short sha256 of sorted-key JSON
    candidate, n = Path(base) / stem, 1
    while True:
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            n += 1
            candidate = Path(base) / f"{stem}-{n}"
```

## Challenge

```python
def flatten(nested: dict, prefix: str = "") -> dict:
    flat = {}
    for key, value in nested.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, prefix=f"{dotted}."))
        else:
            flat[dotted] = value
    return flat
```

The remaining pieces (`load_run`, the two diffs, `same_data`, the sub-command) follow hint 2.
The full reference is in `solutions/labs/w1d4_config_logging/challenge/`.
