# Final assessment submission

Fill this in at the end of each sitting. Be literal: "ran out of time at step 2" is a useful answer.

Date(s) taken:
Python / pandas / scikit-learn versions (`python -c "import sys, pandas, sklearn; print(sys.version, pandas.__version__, sklearn.__version__)"`):
Did you take the Week 1 diagnostic? (yes / no / partly):

## Per-section record

| Section | Minutes used | Checks passing at time-out (e.g. 18/22) | Help used beyond official docs (none / what) | Confidence before seeing solutions (low / medium / high) |
|---|---|---|---|---|
| f1_python | | | | |
| f2_sql | | | | |
| f3_cleaning | | | | |
| f4_baseline | | | | |
| f5_leakage | | | | |
| f6_testing_api | | | | |
| f7_explain | n/a (written) | | | |
| t1_transfer | | | | |

To get the "checks passing" figure: `python -m pytest labs/w8d6_final_assessment/<section>/checks -q`.

## Short written items

**f2** - for each query, one line: what would a plausible wrong version have returned, and why?

1.
2.
3.
4.
5.

**Which section felt hardest, and was it hard because of the skill or because of the time box?**

**Compared with Week 1, what did you do differently without deciding to?**

**Anything in the tasks or checks that you think is wrong or ambiguous?**

## What to send back for feedback

1. This file.
2. Your `lab/` directories (a commit hash is ideal) for f1-f7 and t1, including `NOTES.md`,
   `ANSWERS.md`, `FINDINGS.md`, `MEMO.md` and `REPORT.md`.
3. The output of `for s in labs/w8d6_final_assessment/*/checks; do python -m pytest $s -q -p no:cacheprovider | tail -1; done`.
