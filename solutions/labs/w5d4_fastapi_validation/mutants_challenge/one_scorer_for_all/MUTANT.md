# Mutant: one_scorer_for_all

Keeps one StreamScorer for the whole service and ignores the machine id when scoring: every
machine's samples end up in one burn-in, and the first machine to send data calibrates all of them.
