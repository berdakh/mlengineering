# Diagnostic submission

Fill this in at the end of each session. Be literal: the point is an accurate picture, and
"ran out of time at step 2" is a useful answer.

Date(s) taken:
Python / pandas / scikit-learn versions (`python -c "import sys, pandas, sklearn; print(sys.version, pandas.__version__, sklearn.__version__)"`):

## Per-section record

| Section | Minutes used | Checks passing at time-out (e.g. 18/22) | Help used beyond official docs (none / what) | Confidence before seeing solutions (low / medium / high) |
|---|---|---|---|---|
| a1_python | | | | |
| a2_sql | | | | |
| a3_cleaning | | | | |
| b1_baseline | | | | |
| b2_leakage | | | | |
| b3_testing_api | | | | |
| b4_explain | n/a (written) | | | |

To get the "checks passing" figure: `python -m pytest diagnostic/<section>/checks -q` and copy the last line.

## Short written items

**a2** - for each query, one line: what would a plausible wrong version have returned, and why?

1.
2.
3.
4.
5.

**Which section felt least familiar, and what specifically was unfamiliar?**

**Which section would you have done differently with no time limit?**

**Anything in the tasks or checks that you think is wrong or ambiguous?**

## What to send back for feedback

1. This file.
2. Your `lab/` directories (a commit hash or a diff is ideal):
   * `a1_python/lab/usage_report.py`, `NOTES.md`
   * `a2_sql/lab/q1.sql` ... `q5.sql`
   * `a3_cleaning/lab/clean.py`, `NOTES.md`
   * `b1_baseline/lab/baseline.py`, `ANSWERS.md` and the printed report
   * `b2_leakage/lab/fixed_eval.py`, `FINDINGS.md`
   * `b3_testing_api/lab/test_split.py`, `schemas.py`, `ANSWERS.md`
   * `b4_explain/lab/MEMO.md`
3. The output of `python -m pytest diagnostic -q -p no:cacheprovider` (last 15 lines).
