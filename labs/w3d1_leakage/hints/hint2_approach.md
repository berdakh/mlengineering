# Hint 2 - which probe finds which leak

**Leak hunt, in this order.**

1. Run `leaky_baseline.py` and read the feature importances. Then a **single-feature probe**: for each
   column, average precision of that column alone (or of a one-feature model) on the inherited split.
   Two columns stand out. For each, write when it is produced. One of them is an identifier.
2. **Compare stored aggregates with a point-in-time recomputation.** `prior_late_rate` and
   `customer_late_rate` look alike. Recompute a customer's late rate using only invoices issued before
   each row, and compare it with each column. Which one matches, and which one also knows the future?
3. **Look for twins.** Group rows by everything except `invoice_id`, `issue_date` and `amount`. Some
   groups have two rows dated 20-70 days apart with the same outcome. Decide which one is the real
   prediction opportunity, and remove the other before splitting.
4. **Match the split to deployment.** The model scores invoices issued *after* the data. Compare a
   random split with a split at `CUTOFF`. Invoices of one customer in one month share circumstances
   that the random split lets the model see.
5. **Move every fitted step into one estimator.** Imputation, one-hot encoding and scaling belong in a
   `ColumnTransformer` inside a `Pipeline`, fitted on training rows only.

Measure each leak's effect by switching it on alone, everything else fixed. Record it in `LEAK_REPORT.md`.

**Overlap groups.** Build a hash per row from `datetime` plus the eight sensors, keep the distinct
(hash, experiment) pairs, find hashes present in two or more experiments, and join experiments that
share at least `min_shared_rows` rows. Connected components, not pairs: `other/2`, `other/3` and
`other/4` are one group although 2 and 4 share nothing directly.

**Repair.** For each group that is split: if any member is in the test set *and* the group touches the
reference recording, the test members must leave test; otherwise move every member into the development
fold that already holds most of them. Never move a development experiment into test.
