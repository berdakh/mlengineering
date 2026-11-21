# a3_cleaning - reviewer notes

Reference: `lab/clean.py`, `lab/NOTES.md`. Ground truth for the full file comes from the generator
(`diagnostic/a3_cleaning/checks/expected_clean.csv`); the reference reproduces it exactly
(`python tools/verify_checks.py diagnostic/a3_cleaning`).

## Planted defects (972 raw rows, 900 customers)

Exact duplicates; stale earlier versions of a customer; three date formats including offset
timestamps whose local date differs from the UTC date; case/whitespace noise in `country` and `plan`;
missing codes `""`, `unknown`, `-`; out-of-vocabulary plan `gold`; `$` prefixes; prices in cents
flagged only by `price_unit`; age sentinels `-1`, `999` and impossible ages.

## Common incorrect answers and why they fail

* **`df.drop_duplicates()` only** - stale versions survive; `customer_id` not unique (mutant
  `exact_dupes_only`). Also **`drop_duplicates("customer_id")` without sorting by `updated_at`** keeps
  an arbitrary version.
* **`pd.to_datetime(col)` on the mixed column** - depending on the pandas version this raises, or
  guesses month-first for `DD/MM/YYYY` and silently swaps day and month when day <= 12 (mutant
  `month_day_swapped`). Ambiguous formats must be parsed with an explicit `format=`.
* **Slicing the first 10 characters of an offset timestamp**, or `tz_localize(None)` before converting
  to UTC - yields the local date (mutant `tz_dropped`). Convert to UTC first, then drop the zone.
* **Stripping `$` but ignoring `price_unit`** (mutant `cents_not_converted`), or dividing every value
  above some magic number by 100 - works on this file, encodes a guess rather than the documented unit.
* **Replacing missing codes with the string `"UNKNOWN"`** or ages with `0`/the mean - the contract asks
  for real missing values; imputation is a modelling step that belongs in a pipeline fitted on train only.
* **Mutating `raw`** (`raw["age"] = ...`) - rejected by `test_output_columns_and_no_mutation`.
* **Clipping impossible ages to 13/110** - fabricates data.

## Rubric

| Aspect | Demonstrated independently | Partial | Not yet demonstrated |
|---|---|---|---|
| Finding defects | NOTES lists defects with counts/examples found by inspection (`value_counts`, `str.len`, regex) | Defects found mainly from failing check names | Few defects found |
| pandas fluency | Vectorised, explicit formats, no row loops needed, no chained-assignment warnings | Works but through `apply` with Python branching everywhere, or fragile | Could not express the transformations |
| Time zones and dates | UTC conversion correct and explained | Correct after check feedback | Wrong |
| Judgment | States what was decided for out-of-vocabulary values and why; distinguishes cleaning from imputation | Decisions made but not stated | Silent coercion (`errors="coerce"` everywhere with no count of what was lost) |

A row-wise `apply` solution that passes is still a pass on correctness; note fluency separately.
