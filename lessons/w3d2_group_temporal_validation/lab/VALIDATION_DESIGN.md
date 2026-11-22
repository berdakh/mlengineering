# Validation design memo: `flowguard`

Author: | Date: | Manifest: `splits/v2.json` (w3d1)

Keep it to one page. Every claim about a number must point to a row of your `compare_schemes.py` table.

## 1. Deployment question (one sentence)

> The model will be used to ...

## 2. Estimand

The expected value of ______ (metric) for a model trained ______ (how, on what), on ______ (which unseen
units, which time, which regime).

## 3. Primary scheme and why

* Primary scheme:
* Why it matches the deployment question:
* Schemes rejected, and why (one line each):
* Schemes kept as stress tests, and what each would tell you if it failed:

## 4. What the table does and does not support

| Claim | Supported by | Not supported because |
|---|---|---|
| | | |
| | | |

## 5. Buffer (purge and embargo)

Feature window w = ___ rows, label horizon h = ___ rows, so buffer = ___ rows each side. Where in the
project it applies, and where it does not:

## 6. Known weaknesses of this design

1.
2.
3.

---

### Rubric (used for grading, read it before writing)

| Criterion | Strong | Weak |
|---|---|---|
| Deployment question | names the unit (new experiments / pumps), the time relation and the regime question | "evaluate the model" |
| Estimand | metric, training procedure and population of the unseen data are all stated | metric only |
| Primary scheme | follows from the question; rejection of row-wise and time-block schemes argued from the question, not from the numbers | chosen because its number is highest or lowest |
| Use of evidence | cites table rows; separates leakage (1 vs 4), regime shift (4 vs 5) and noise (fold spread, few experiments) | compares rows that answer different questions as if they were rankings |
| Buffer | correct formula and value; says it does not apply to experiment-held-out folds (no shared samples across experiments) | wrong value, or applied everywhere "to be safe" without saying why |
| Weaknesses | at least two concrete ones: few experiments, family-day confounding, overlap groups shrinking effective folds, test set of seven | generic "more data would help" |
