# Mutant: `reminders_sent` as a feature

Reminders are sent after an invoice passes its due date, so the count is the outcome seen from the
dunning system. It looks like an ordinary operational column and has no missing values, which is
why it gets through. Test AUC becomes about 1.0.

Rejected by the declared-features check, the scramble check and the generator-bound check.
