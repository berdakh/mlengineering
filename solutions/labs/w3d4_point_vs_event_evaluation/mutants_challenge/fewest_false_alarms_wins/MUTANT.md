# Mutant: minimise false alarms, full stop

Among feasible settings the one with the lowest false-alarm rate is chosen; recall only breaks ties.

**Why it is plausible.** "Stay inside the budget" slides into "be as quiet as possible".

**What goes wrong.** The quietest detector is the one that never fires. The budget is a constraint to
satisfy, and recall is what is maximised inside it; this mutant gives away detections the budget allowed.

**Caught by.** `test_choice_has_the_best_recall_among_feasible_settings`, `test_a_looser_budget_never_lowers_recall`.
