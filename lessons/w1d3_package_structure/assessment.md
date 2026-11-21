# w1d3 assessment

Write your answers in `lab/ASSESSMENT_ANSWERS.md` **before** opening
`solutions/lessons/w1d3_package_structure/assessment_answers.md`. Two to five sentences
each; no code needed unless asked. Budget: 10 minutes for Q1–Q6, 15 for the interview rep.

## Reasoning questions

**Q1.** You are in a project root that uses a *flat* layout. `python -m pytest` passes.
You then run `pip uninstall pumpwatch` and `python -m pytest` again, and it still
passes. Explain precisely why, and say what this implies about what the tests were
exercising all along.

**Q2.** After adding `[project.scripts] pumpwatch = "pumpwatch.cli:main"` to an already
editable-installed project, typing `pumpwatch` gives "command not found", yet
`python -m pumpwatch.cli` works. Why, and what is the fix? Name one other kind of
`pyproject.toml` edit with the same consequence.

**Q3.** A colleague proposes replacing the `dependencies` list in `pyproject.toml` with
the 140 exact pins from their `pip freeze`. Give one situation where exact pins are the
right tool and one concrete way this proposal causes harm. Where *should* the pins live?

**Q4 (design choice).** In the lab you were told to port the scaler-before-split
behaviour faithfully and to fix it only afterwards as a separate step. A reviewer says:
"That is wasteful — you knew it was a bug, you should have fixed it while moving the
code." Defend the two-step order. Then state one circumstance in which the reviewer
would be right.

**Q5.** After the leak fix the four printed metrics were identical to every digit.
Three people react:
(a) "So there was no leakage." (b) "So the fix was unnecessary; revert it to keep the
diff small." (c) "So this check cannot detect that leak; keep the fix and note the
limitation." Which is correct, and what specifically is wrong with the other two?

**Q6.** `main()` returns an integer and the module ends with `sys.exit(main())`, rather
than calling `sys.exit(2)` deep inside the function that reads the file. Give two
practical benefits of this arrangement.

## Rubric for open answers (Q4 and Q5; apply the same scale to the reflection prompt)

| Level | Description |
|---|---|
| **3 — Sound** | States the mechanism correctly, ties it to *this* lab's evidence (the unchanged metrics, the golden comparison), and names a limitation or a condition under which the conclusion would change. |
| **2 — Mostly right** | Correct conclusion and mechanism, but generic: no reference to the evidence, or no boundary condition. |
| **1 — Right word, wrong reason** | Reaches the accepted conclusion using a reason that does not hold (e.g. "always refactor first because that is best practice"; "leakage always inflates metrics"). |
| **0 — Incorrect or absent** | Wrong conclusion, or an answer that restates the question. |

Self-score honestly, then compare with the model answers. A 1 is more useful to record
than an optimistic 2: it tells the review day what to revisit.

## Interview rep (15 minutes, timed, no assistance, no scikit-learn)

> Implement
>
> ```python
> def group_split(groups: list[str], test_fraction: float, seed: int) -> tuple[list[int], list[int]]:
>     """Return (train_indices, test_indices) into `groups`."""
> ```
>
> such that: no group label appears on both sides; the *number of test groups* is
> `round(test_fraction * n_groups)` but never 0 and never all of them; the result is
> identical for the same `seed` regardless of the order in which rows arrive being
> permuted **together with** their indices (i.e. which *groups* are test depends only on
> the set of group labels and the seed); indices come back sorted ascending.
> Raise `ValueError` if there are fewer than two distinct groups or if
> `test_fraction` is not strictly between 0 and 1.

Say your approach out loud (or write two lines) before coding. When the timer ends,
stop, then test your function with the snippet in the answers file and score yourself
with the rubric there. Assistance is reduced on purpose: there are no hints for this one.
