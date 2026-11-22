# w1d7 - Week 1 review and catch-up (light day)

**Time budget: 60-90 minutes.** No new material.

| Activity | Time |
|---|---|
| 1. Retrieval sheet, from memory | 25 min |
| 2. Score it against the answers; choose what to redo | 10 min |
| 3. Redo one thing, cold and unassisted | 20-30 min |
| 4. Interview set 1 (timed) | 40 min, or only P1 + E3 (20 min) on a short day |
| 5. Update progress flags and the spaced-review list | 5 min |

If you are behind on Week 1, do activities 1 and 2 (35 min), then spend the rest of the session on
the unfinished unit. Retrieval comes first even then: it tells you what the catch-up should target.

## Purpose

Reading a lesson again feels productive and changes little. Recalling its content without the page
in front of you is harder and is what makes it available in an interview or at a keyboard a month
later. This session is built around that: answer first, check second, and treat every wrong or
hesitant answer as a pointer to something to redo, not to re-read.

Units covered: the diagnostic (`w1d1`, `w1d2`), [`w1d3`](../w1d3_package_structure/README.md),
[`w1d4`](../w1d4_config_logging/README.md), [`w1d5`](../w1d5_testing_ml_code/README.md), and `w1d6`
(independent notebook refactor). Handbook: H2.1, H2.2, H9.1.

Question 12 covers [`w1d6`](../w1d6_notebook_to_package/README.md) and handbook H2.3. If you have
not done `w1d6` yet, skip it and return on day 7 of Week 2.

## 1. Retrieval sheet (25 minutes, closed book)

Rules: no lesson, handbook, repository or search. Write answers in `progress/notes.md` or on paper,
two to five sentences each. If you cannot answer, write what you *would check* and move on; a blank
is information. Do not open the answers until all twelve have an attempt.

**Packaging and environments (w1d3, H2.1)**

1. You run `python -m pytest` in a project root and all tests pass. A colleague installs the wheel you
   built from the same commit and gets `ModuleNotFoundError` for one of your subpackages. Give the
   mechanism that lets both be true, and two independent changes that would have exposed the problem
   on your machine.
2. What does `pip install -e .` install into the environment, and what does it *not* copy? Name two
   kinds of change to the project after which you must reinstall for the change to take effect.
3. Distinguish *declared dependencies* (`pyproject.toml`) from a *locked environment*. Who needs
   which, and what goes wrong if a library author publishes exact pins as its dependencies?

**Configuration, logging, reproducible runs (w1d4, H2.2)**

4. A colleague's `--set split.seed=3` run and yours with seed 7 differ by 0.04 F1 and they conclude
   their feature change helped. State two distinct reasons this conclusion is not yet supported, and
   name the file(s) in a run directory you would inspect for each.
5. Give the precedence order of configuration sources, and explain why validation should happen once,
   after merging, and why an unknown key must be an error.
6. Why must a library module never call `logging.basicConfig()` (or attach handlers) at import time?
   What does a library module do instead, and where does configuration happen?

**Testing ML code (w1d5, H9.1)**

7. For `rms(x)` name one known-answer test and one invariance (metamorphic) test, each with the
   mathematics that justifies the expected value, and say which defect each would catch that the
   other might not.
8. Why is `assert auc > 0.95` a poor *unit* test? Say what kind of check it is, where it belongs, and
   what a defensible minimal version of it looks like.
9. `pytest.approx(expected)` uses a relative tolerance by default. When does a relative tolerance
   fail to work at all, what do you use instead, and how do you choose the size of a tolerance?

**Diagnostic topics**

10. A query uses `WHERE customer_id NOT IN (SELECT customer_id FROM tickets)` and returns zero rows,
    although many customers have no tickets. Explain exactly why, and give two correct formulations.
11. In the pump script, `StandardScaler` was fitted on all rows before the group split. Explain why
    this is leakage. Removing it left the printed metrics unchanged on that data: does that make the
    original acceptable? Answer in terms of what an evaluation is supposed to guarantee.

**Refactoring under version control (w1d6)**

12. What is a characterisation (golden-output) test, why do you write it *before* touching the code,
    and when do you delete or replace it? Why should a commit never mix a structural change with a
    behaviour change? Then: list four categories of file that an ML project must keep out of Git,
    with the reason for each.

## 2. Score and choose (10 minutes)

Open [`solutions/lessons/w1d7_review/retrieval_answers.md`](../../solutions/lessons/w1d7_review/retrieval_answers.md).
For each question mark one of:

* **solid** - correct mechanism, stated without hedging;
* **shaky** - right direction, missing the mechanism or a key condition;
* **missing** - blank or wrong.

Record the three lists with `python wb.py note w1d7 "solid: ...; shaky: ...; missing: ..."`.
The answers file also lists common wrong answers; if yours matches one, write down which.

## 3. Redo one thing, unassisted (20-30 minutes)

Pick **one** item, in this priority order:

1. a diagnostic section or lesson challenge whose checks did not pass;
2. a guided lab you passed only after reading hint 3 or a solution;
3. the task behind your weakest retrieval answer (for example: build a `src`-layout package with a
   console script from an empty directory; write the strict config loader; write known-answer and
   invariance tests for `band_power`).

Protocol

* Work in a fresh directory or branch, from a blank file. Do not open your earlier attempt, the
  hints, the solutions, or the lesson text. Library documentation is allowed.
* Set a timer for 25 minutes. Stop when it rings.
* Run the unit's checks at most twice: once when you believe you are done, once after fixing.
  ```bash
  python wb.py check w1d3 --challenge      # example
  ```
* Record the conditions honestly, because the conditions are the evidence:
  ```bash
  python wb.py note w1d5 "redo cold, 25 min, no hints/solutions, docs only: 12/14 defects killed; missed: ..."
  ```
* Only if the redo met the unit's completion criteria under these conditions:
  `python wb.py mark <unit> independent`. Otherwise `python wb.py mark <unit> review`.

A redo that fails is useful. It converts "I think I know this" into a specific gap, and that gap
goes onto the spaced-review list below.

## 4. Interview set 1 (40 minutes, timed)

[`interview/set1_python_structure.md`](../../interview/set1_python_structure.md): two coding prompts
(a streaming data structure; a refactor for testability) and two short explanations on project
structure. Follow the conditions stated there. Self-check the code with

```bash
python -m pytest interview/set1_tests -q
```

then score all four answers against `solutions/interview/set1.md`. This is the first timed set;
treat the result as a baseline, not a verdict.

## 5. Spaced review and progress flags (5 minutes)

**Spaced-review schedule.** Every question you marked *shaky* or *missing* is asked again, closed
book, at increasing intervals: on the next review day (`w2d7`, about one week), then about two weeks
later (`w4d7`), then about four weeks later (`w8d7`). A question leaves the list after two
consecutive *solid* answers. Keep the list at the top of `progress/notes.md`:

```
## Spaced review
- w1d7 Q4 (seed vs effect) - due w2d7
- w1d7 Q10 (NOT IN / NULL) - due w2d7
```

The lessons' own delayed questions are part of the same system: the retrieval question at the end of
`w1d5` is deliberately scheduled for next week, before `w2d5`, and appears on the `w2d7` sheet.

**Flags.** Go through the week once and set each flag from evidence, not from memory of effort:

```bash
python wb.py status
python wb.py mark w1d3 reading          # you read the lesson and the handbook section
python wb.py mark w1d3 guided           # the lab checks passed (hints allowed)
python wb.py mark w1d3 independent      # the challenge or a cold redo passed without hints or solutions
python wb.py mark w1d4 review           # anything shaky or missing today
python wb.py mark w1d4 review off       # clear it only after a later solid retrieval or redo
python wb.py mark w1d7 guided           # this session done
```

Checklist

- [ ] Twelve retrieval answers attempted before opening the key
- [ ] solid / shaky / missing lists recorded with `wb.py note`
- [ ] One cold redo done and its conditions recorded
- [ ] Interview set 1 attempted under the stated conditions and scored
- [ ] `review` flag set on every unit with a shaky or missing answer
- [ ] Spaced-review list updated in `progress/notes.md`
- [ ] If the diagnostic submission has not been pushed yet: push it now, before Week 2 adapts to it

Next: Week 2 starts with `w2d1` (SQL I: grain, joins, aggregation and NULL semantics); see
[roadmap/SCHEDULE.md](../../roadmap/SCHEDULE.md).

---

*Content status and verification: see `STATUS.md`. Interview set 1's reference answers and tests were
executed (details in `solutions/interview/set1.md`). The retrieval answers are prose and were
checked against handbook sections H2.1, H2.2 and H9.1; the SQL statements in answer 10 were executed.*
