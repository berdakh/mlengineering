# a3 - Data cleaning with pandas

**Time box: 35 minutes.** Session A, section 3 of 3. No hints; pandas documentation is fine.

## Situation

`diagnostic/data/signups_dirty.csv` (**synthetic**) is a CRM export of customer signups. It was
assembled from several regional systems and has not been cleaned. Raw columns (all read as text):

| Column | Meaning as documented by the source team |
|---|---|
| `customer_id` | Customer key. The export may contain several rows per customer. |
| `signup_date` | Signup date. Regional systems export it as an ISO date, as `DD/MM/YYYY`, or as a local timestamp with UTC offset. The business definition of the signup date is the **UTC calendar date**. |
| `country` | ISO 3166-1 alpha-2 code, entered by hand. |
| `plan` | One of `basic`, `standard`, `premium`. |
| `monthly_price` | Monthly price. See `price_unit`. |
| `price_unit` | `usd` or `cents`. |
| `age` | Age in years. Legacy systems used sentinel codes for "not provided". |
| `updated_at` | When this row was last written (`YYYY-MM-DD HH:MM:SS`, UTC). |

## Task

Implement `clean(raw)` in `lab/clean.py`. Look at the data first; the list above does not tell you
everything that is wrong. Output contract:

* Exactly these columns: `customer_id, signup_date, country, plan, monthly_price_usd, age`.
* One row per `customer_id`; when a customer has several rows, the most recently updated one is kept.
* `signup_date`: timezone-naive datetime at midnight, the UTC calendar date.
* `country`: upper-case two-letter code, or missing.
* `plan`: `basic` / `standard` / `premium`, or missing for anything else.
* `monthly_price_usd`: numeric, US dollars.
* `age`: numeric; "not provided" codes and values outside 13-110 are missing.
* Missing means a real missing value (`None`/`NaN`/`NaT`/`pd.NA`), never a placeholder string or number.
* `raw` is not modified.

Then fill in `lab/NOTES.md`: each defect, how many rows, how you detected it, what you decided.

## Check your work

```bash
python diagnostic/a3_cleaning/lab/clean.py       # prints head, dtypes, missing counts
python wb.py check diagnostic/a3_cleaning        # or:
python -m pytest diagnostic/a3_cleaning/checks -q
```

The starter raises `NotImplementedError`, so every check fails until you implement `clean`.

## Acceptance criteria

* All checks pass, including the comparison of the full file with the generator's ground truth.
* `NOTES.md` shows the defects were *found by inspection* (counts, examples), not inferred from test names.

## Submit

`lab/clean.py`, `lab/NOTES.md`, time used.
