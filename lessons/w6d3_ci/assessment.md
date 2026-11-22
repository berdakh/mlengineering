# W6D3 assessment

Write your answers before opening `solutions/lessons/w6d3_ci/assessment_answers.md`.

## Reasoning questions

1. Your `test` job takes 4 minutes and `image` takes 3. Without `needs:`, a push with a failing test
   finishes in how long, and what has been spent? With `needs: [test]`? Which do you choose for a
   pull request, and would you choose differently for a release tag?
2. A matrix entry `python-version: 3.10` fails with "Version 3.1 was not found". Explain the cause
   precisely (which component reads what), and why `3.11` unquoted happens to work.
3. Give the rule that decides whether a check belongs in the per-push gate or in the scheduled lane,
   and classify: (a) `ruff check`; (b) "AUC on the frozen test set >= 0.80"; (c) a test that the API
   returns 422 for a NaN; (d) "p95 latency of /predict < 100 ms"; (e) building the Docker image;
   (f) a drift report on last week's production inputs.
4. A workflow interpolates `${{ secrets.TOKEN }}` into a `run:` line and the log shows `***`. Is the
   secret safe? Name two ways it can still leak, and the safer pattern.
5. Why do pull requests from forks not get repository secrets, and what does that imply for what your
   per-push gate may depend on?
6. `actions/checkout@v7`, `@main`, `@<40-hex SHA>`: rank them by reproducibility and by maintenance
   effort, and say which you would require in a regulated organisation.

## Design-choice explanation (write 150-250 words)

The challenge's image job ran `docker exec app curl ...` and failed because the image has no curl.
You can fix it by installing curl in the image or by checking from the runner. Argue for one, covering:
image size and attack surface, what the check is supposed to prove, and how a container *health check*
(the orchestrator's probe) differs from a CI smoke test.

## Rubric (for the open answers)

| Criterion | Strong | Adequate | Weak |
|---|---|---|---|
| Correct mechanism | names the component and the behaviour (YAML parser, expression substitution, job parallelism) | right idea, vague mechanism | restates the symptom |
| Gate/lane reasoning | applies "red on an unchanged commit?" consistently and explains (b), (d), (f) | classifies correctly without the rule | puts statistical checks in the gate |
| Security | separates masking from protection; mentions env and fork policy | one of the two | trusts `***` |
| Trade-offs | states what is given up by each option | one side only | no trade-off |
| Evidence | cites a log line, a measurement or a check result | general claims | none |

## Interview rep (10-15 minutes, debugging, reduced assistance)

Say your answer aloud or write it in 10 minutes, then compare with the rubric in the answers file.

> "Our CI has been red on `main` since this morning, and nobody merged anything that touches the model.
> The failing step is `pip install -e .[dev]` in the Python 3.13 matrix entry that someone added on
> Friday; the 3.11 and 3.12 entries are green. The log ends with
> `error: subprocess-exited-with-error ... Building wheel for <some dependency> ... failed`.
> On my laptop `pip install -e .` works. What do you look at, in what order, and what are the likely
> causes? How do you unblock `main` today, and what do you change so this does not recur?"
