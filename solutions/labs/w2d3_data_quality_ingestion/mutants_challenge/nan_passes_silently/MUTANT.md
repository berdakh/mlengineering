# Mutant: nan_passes_silently

Rules are written as "a row is invalid if `amount <= 0`". Values that fail to parse (`"40,00"`, empty)
become NaN under `pd.to_numeric(errors="coerce")`, every comparison with NaN is False, so the row is
"not invalid" and passes.

Why it is plausible: it is the most direct translation of the rule, and it finds every negative
amount in the sample file. Why it is wrong: the unparseable values are the ones most likely to break
downstream arithmetic, and they are exactly the ones this check waves through. Write validity as
"parsed AND condition".

Rejected by: `test_row_level_violation...[amount_decimal_comma]`, `[amount_missing]`.
