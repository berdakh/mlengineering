# Mutant: budget ignored

Every grid setting is treated as feasible, so the setting with the highest dev event recall wins
whatever its false-alarm rate.

**Why it is plausible.** It is what tuning for recall (or for point F1) does by habit; the budget is a
constraint from outside the metric and is easy to leave as a comment.

**What goes wrong.** The chosen setting pages the operator far more often than agreed, and the report
still says `feasible: True`.

**Caught by.** `test_choice_respects_the_budget_on_dev`, `test_impossible_budget_is_reported_as_infeasible`.
