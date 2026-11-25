# Hint 1 — concepts

* **Gate vs lane.** Ask of every step: "could this be red on an unchanged commit?" A download, a
  statistical estimate on 7 experiments and a wall-clock assertion can all be red with no code change.
  They go to a scheduled workflow. Lint, deterministic tests and the image build stay in the gate.
* **Jobs run in parallel** unless `needs:` orders them, and each job is a fresh machine.
* **YAML types.** `3.10` without quotes is the number 3.1. `on` without quotes is read as `True` by
  YAML 1.1 parsers (GitHub handles it; Python's YAML library does not).
* **Least privilege.** The workflow token's rights come from `permissions:`. A test workflow reads.
* **Expressions are substituted before the shell runs.** `${{ secrets.X }}` inside `run:` puts the
  secret into the script text.
* **Challenge.** Each log is one of: a test that measures the machine instead of the code; a cache key
  that is new on every run; a command that does not exist where it is run.
