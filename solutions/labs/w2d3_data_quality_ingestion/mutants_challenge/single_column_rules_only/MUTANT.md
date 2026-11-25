# Mutant: single_column_rules_only

Every column is validated on its own (type, range, allowed set), but the two rules that relate columns
are missing: `refunded_amount <= amount` and `delivered_ts >= order_ts`.

Why it is plausible: schema tools make per-column rules effortless, and each value looks valid in
isolation. Why it is wrong: the defects that cost money are usually relational - a refund larger than
the order, a delivery before the purchase. They are invisible to column-wise validation.

Rejected by: `test_row_level_violation...[refund_exceeds_amount]`, `[delivered_before_ordered]`.
