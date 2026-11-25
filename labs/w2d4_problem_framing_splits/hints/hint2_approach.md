# Hint 2 - approach (challenge)

Work with integer month numbers so the arithmetic is ordinary subtraction (`year * 12 + month`).
Let `T` be `test_start`, `H` the horizon, `last` the last month in the table.

1. **Trainable rows.** The model is fitted at the end of month `T - 1`. A row from month `m` has a
   label covering `m+1 ... m+H`. Write the inequality that says "that window had closed by then".
   Check it by hand for `H = 3`, `T = 2025-01`: the latest trainable month should be 2024-09.
2. **Evaluable rows.** Month at or after `T`, and the label window must close inside the table.
   Do not use `notna()` for this: look at which labels are known in the last three months and why.
3. **Hold-out customers.** Sample from the customers that have at least one trainable row (sorted,
   then a seeded generator). Remove *all* their trainable rows from train.
4. **Known vs new.** Define these from the result, not from the sample: a test customer is "known"
   exactly when the final training set contains a row of theirs. Customers who joined after the last
   trainable month were never sampled, yet the model has not seen them.
5. Return `df.index` labels, not positions; the checks use a shuffled, offset index.

Part C: compare `df.loc[test rows, label].mean()` with the mean over
`df[(month >= T) & label.notna()]`, and look at the months that only the second set contains.
