# a3 notes (reference)

## Defects found in the raw export (972 rows -> 900 customers)
1. Exact duplicate rows and stale earlier versions of a customer (same id, older `updated_at`,
   different plan/price). Detected with `customer_id.duplicated()`; kept the latest `updated_at`.
   `drop_duplicates()` alone leaves the stale versions in.
2. `signup_date` in three formats: ISO date, `DD/MM/YYYY`, ISO timestamp with UTC offset. Parsed each
   format explicitly; timestamps converted to UTC before taking the date (the local date differs from
   the UTC date for some rows). Letting the parser infer the format swaps day and month whenever day <= 12.
3. `country`: case/whitespace variants, and three missing codes (empty, `unknown`, `-`).
4. `plan`: case/whitespace variants, and an out-of-vocabulary value (`gold`) -> missing, not a 4th plan.
5. `monthly_price`: `$` prefix on some rows, and integer cents on rows with `price_unit == "cents"`
   (a plan priced 999-1999 "dollars" is the visible symptom).
6. `age`: sentinel codes -1 / 999 and impossible values (0, 3, 150, 212) -> missing. Left missing, not
   imputed: imputation is a modelling decision that belongs in the training pipeline, fitted on train only.

## Least sure about
Whether out-of-vocabulary plans should be missing or should fail the pipeline. In production I would
count them and alert above a threshold rather than silently null them.
