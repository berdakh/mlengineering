# W5D2 independent challenge: version the logistic candidate

**Setting.** The team wants the supervised logistic candidate from w4d5 in the registry, as
`flowguard-logistic 0.1.0`, to run as a shadow scorer. Unlike the shipped flow-rate detector, its state
includes a fitted scikit-learn `LogisticRegression`. The tempting artifact is `joblib.dump(model)`.
Your job is to produce one that is safe to load, survives library upgrades and refuses what it cannot
interpret, and to write down the rules.

**Given:** `src/flowguard/` (snapshots, including `detectors.SupervisedLogistic`), the frozen manifest,
and [`publish_logistic.py`](publish_logistic.py), which trains the model on the REAL development data,
calls your module, registers and promotes the bundle, loads it back and compares scores on the 7 test
experiments (needs `python project/get_skab.py` once).

**Your task.**

1. Copy your finished lab module to `src/flowguard/artifacts.py` (the challenge reuses `verify_bundle`,
   `register`, `promote` and `resolve`).
2. Write `logistic_bundle.py` to the contract in its docstring: `save_logistic` and `load_logistic`.
3. Write `COMPATIBILITY.md`: what is stored and why that format, what the loader refuses, what is only
   recorded, and how model versions and bundle format versions are numbered.
4. Run `publish_logistic.py` and record in COMPATIBILITY.md the bundle size and the largest score
   difference you observed.

**Acceptance criteria** (`python wb.py check w5d2 --challenge`):

* loaded scores equal the trained model's within 1e-12 on synthetic runs, including values far
  beyond the clip;
* no pickle is used to save or load, and no file in the bundle is a pickle stream;
* the bundle passes `verify_bundle`, can be registered, promoted and resolved, and loads from the registry;
* a bundle with an edited weight or parameter is refused; a bundle whose feature layout differs from the
  one your loader implements is refused even when its checksums agree; so is a newer format version;
* `COMPATIBILITY.md` has no `TODO`, at least 150 words, and mentions scikit-learn.

**Time.** 45 minutes. No solution is provided until you have attempted it.
