# w1d3 lab workspace

You work **in this directory**. When you are done it should look like this:

```
lab/
  pyproject.toml
  src/pumpwatch/__init__.py, io.py, features.py, split.py, model.py, cli.py
  golden.txt            output of the original script (Task 1)
  REFACTOR_LOG.md       your record of what changed and what did not
  messy_analysis.py     the original; keep it until the package reproduces it
  stubs/                signatures to start from (copy into src/pumpwatch/)
```

Instructions are in the lesson: [`../README.md`](../README.md#4-guided-lab).

* `stubs/` holds the module contracts (signatures + docstrings). Copy them to
  `src/pumpwatch/` and fill them in. The signatures are the part other lessons rely on;
  everything inside the functions is yours.
* `compare_to_golden.py` compares the JSON your CLI prints with `golden.txt`.
* Checks (from the repository root): `python -m pytest lessons/w1d3_package_structure/checks -q`

The dataset is SYNTHETIC (`data/README.md`). Numbers here show that the plumbing
is right; they say nothing about detecting faults in real pumps.
