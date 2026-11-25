# Commit self-review (w1d6)

Automated checks cannot grade a history. Fill this in against your own `git log --stat`, honestly;
it is the evidence for the "commit hygiene" part of this unit. Paste the log first.

```
(paste `git log --oneline` here)
```

## Rubric

Mark each line **yes / partly / no** and give the commit hash that supports the answer.

| # | Criterion | Mark | Evidence (hash, or what is missing) |
|---|---|---|---|
| 1 | The first commit contains the notebook export exactly as received | | |
| 2 | `.gitignore` covering `data/`, the environment and bytecode exists **before** any commit that could have picked them up | | |
| 3 | No data file, environment, cache or secret appears anywhere in `git log --stat --all` | | |
| 4 | Every commit message is one sentence that does not need the word "and" | | |
| 5 | Every commit that changes a printed number or a test expectation says so in its message, and contains nothing else | | |
| 6 | Every extraction commit leaves the tests passing (spot-check two: `git stash -u; git checkout <hash>; python -m pytest -q`) | | |
| 7 | Each bug I fixed has a test that fails on the commit before the fix | | |
| 8 | I read `git diff --staged` before each commit (be honest: how many did you actually read?) | | |
| 9 | A stranger could follow `README.md` from a fresh clone to a printed summary | | |

## Levels

* **Demonstrated:** 1-7 are "yes" with hashes; 8 and 9 at least "partly".
* **Partial:** at most two of 1-7 are "partly", none is "no".
* **Not yet:** a data file or environment was committed, or structure and behaviour changes share
  commits throughout. Redo the history on the review day: `git rebase -i` is allowed for practice,
  but rebuilding from the first commit teaches more.

## Three sentences

1. The commit I am least happy with, and what I would split it into:
2. A hunk that `git add -p` or `git diff --staged` stopped me from committing:
3. What I will do differently the next time I am handed a notebook:
