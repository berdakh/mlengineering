# Refactor log - pumpwatch (reference)

## Environment

- Python version: 3.13 (authoring environment; the package declares `>=3.11`)
- How the environment was created: `python -m venv .venv`
- Installed with: `pip install -e solutions/labs/w1d3_package_structure/lab`

## Characterization (Task 1)

- Command: `python labs/w1d3_package_structure/lab/messy_analysis.py > golden.txt`
- Output: `auc 0.9992283950617284`, `ap 0.9970760233918129`, `acc 0.9666666666666667`,
  `f1 0.9090909090909091`, test units `['P01', 'P06', 'P09']`.
- Non-determinism: none found. The only random element is `GroupShuffleSplit(random_state=7)`.
  Two consecutive runs gave byte-identical output.

## Issues noticed while reading the script (not fixed during the port)

| # | Issue | Affects results? | Decision |
|---|-------|------------------|----------|
| 1 | `StandardScaler` fitted on all rows before the split | In principle yes (test statistics shape the training inputs) | Fix as a separate step after the port |
| 2 | Data path relative to the working directory | No, but the script only runs from the repo root | Fixed by the CLI `--data` argument |
| 3 | Band-power code duplicated for the two bands | No | Collapsed into `band_power()` during the port (verified identical) |
| 4 | `from sklearn.metrics import *` | No | Explicit imports |
| 5 | `fs = 256`, bands, `C`, seed, test size are bare literals | No | Named constants / CLI options; config file is w1d4 |
| 6 | Threshold fixed at 0.5 for acc/F1 on ~17% positives | Affects acc/F1 meaning, not correctness | Left; evaluation choices are weeks 2-3 |
| 7 | Single split, 3 test units, no uncertainty | Interpretation only | Left; week 3 |
| 8 | `label` taken from the first sample of each window | No (constant per window in this data) | Left, noted as an assumption |

## Behaviour-preserving steps

| Step | What moved where | Verified how | Result vs golden |
|------|------------------|--------------|------------------|
| 1 | Feature loop -> `features.py` (`band_power` written once) | Feature table compared with the script's `feat` via `np.allclose(rtol=0, atol=1e-12)` | identical |
| 2 | Split -> `split.py`, model/metrics -> `model.py` (scaler still outside) | `compare_to_golden.py` | identical |
| 3 | `cli.py` + `[project.scripts]`, reinstall | `pumpwatch train --data ...` from `/tmp` | identical |

## Behaviour-changing steps

| Step | What changed and why | Before | After | Interpretation |
|------|----------------------|--------|-------|----------------|
| 4 | Scaler moved inside the estimator (`make_pipeline(StandardScaler(), LogisticRegression())`) so it is fitted on training units only | auc 0.99923, ap 0.99708, acc 0.96667, f1 0.90909 | the same to every printed digit | The leak was real and the fitted model did change (train-only scaler: scales up to ~13% different, means shifted up to ~0.17 SD), but ranking of test scores and every 0.5-threshold decision were preserved, so the four printed metrics are identical. The change is justified by construction: the evaluation no longer *can* be contaminated this way. An unchanged summary number is not evidence that the leak was absent or the fix unnecessary. |
