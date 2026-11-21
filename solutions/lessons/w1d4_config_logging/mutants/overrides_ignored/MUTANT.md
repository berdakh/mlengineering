# Mutant: overrides_ignored

`--set` overrides are parsed (so typos in the section are still caught) but never merged into the configuration. The run silently uses the file values. Typical cause: the override loop was written against a copy of the dict, or after the dataclasses were already built. Caught by the precedence and seed checks.

Changed file: `src/pumpwatch/config.py`
