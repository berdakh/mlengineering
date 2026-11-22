# Mutant: fallback presented as success

When no grid setting meets the budget, the quietest one is returned with `feasible = True`.

**Why it is plausible.** The function "found the best available setting", and a boolean defaulting to
True is one line nobody rereads.

**What goes wrong.** Downstream reports state that the budget is met when it is not.

**Caught by.** `test_impossible_budget_is_reported_as_infeasible`.
