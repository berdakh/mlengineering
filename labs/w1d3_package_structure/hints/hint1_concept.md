# Hint 1 — concepts (challenge)

- A console script and `python -m package` are two *different* launch mechanisms.
  The first is generated from `[project.scripts]`. For the second, Python looks for a
  specific module **inside the package**. `python -m pumpwatch.cli` working tells you
  nothing about `python -m pumpwatch`.
- Think about where each responsibility belongs before writing code. You already have a
  module that owns "turn a path into a validated DataFrame". Writing and re-reading the
  feature table is the same kind of job. The CLI should stay a thin layer that parses
  arguments, calls functions, and translates *expected* failures into exit codes.
- "Exactly one of two options" is a standard argument-parsing situation; `argparse` has
  direct support for it. You do not need to hand-write the check.
- Every way of getting data in is a boundary, and every boundary needs the same care.
  When you add a second loader, ask what the first loader checks that the second should too.
- Criterion 5 says "for either subcommand". If your error handling wraps only the code
  path that existed before, the new path is unprotected.
- Changing the version is a metadata change. Remember what an editable install does and
  does not pick up automatically.

Lab hints: if you are stuck on the lab rather than the challenge, the lesson's
debugging table (section 4) is the place to look first.
