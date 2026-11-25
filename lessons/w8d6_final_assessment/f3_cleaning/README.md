# f3 - Data cleaning with pandas (parallel form of a3)

**Time box: 35 minutes.** Sitting A, section 3 of 3. No hints; pandas documentation is fine.

## Situation

`lessons/w8d6_final_assessment/data/accounts_dirty.csv` (**synthetic**) is Parcelo's CRM export of
business accounts, merged from several sales tools and never cleaned. Raw columns (all read as text):

| Column | Meaning as documented by the source team |
|---|---|
| `account_id` | Account key. The export may contain several rows per account. |
| `signup_date` | Signup date. Tools export it as an ISO date, as `DD.MM.YYYY`, or as a local timestamp with UTC offset. The business definition of the signup date is the **UTC calendar date**. |
| `region` | Home depot code (three letters, e.g. `ALA`), entered by hand. |
| `tier` | One of `starter`, `business`, `enterprise`. |
| `fee` | Platform fee. See `fee_unit`. |
| `fee_unit` | `usd_month` (monthly fee) or `usd_year` (accounts billed annually; the annual amount). |
| `employees` | Number of employees of the customer company. Legacy tools used sentinel codes for "unknown". |
| `updated_at` | When this row was last written (`YYYY-MM-DD HH:MM:SS`, UTC). |

## Task

Implement `clean(raw)` in `lab/clean.py`. Look at the data first; the list above does not tell you
everything that is wrong. Output contract:

* Exactly these columns: `account_id, signup_date, region, tier, monthly_fee_usd, employees`.
* One row per `account_id`; when an account has several rows, the most recently updated one is kept.
* `signup_date`: timezone-naive datetime at midnight, the UTC calendar date.
* `region`: upper-case three-letter code, or missing.
* `tier`: `starter` / `business` / `enterprise`, or missing for anything else.
* `monthly_fee_usd`: numeric, US dollars per month.
* `employees`: numeric; "unknown" codes and values outside 1-50,000 are missing.
* Missing means a real missing value (`None`/`NaN`/`NaT`/`pd.NA`), never a placeholder string or number.
* `raw` is not modified.

Then fill in `lab/NOTES.md`: each defect, how many rows, how you detected it, what you decided.

## Check your work

```bash
python lessons/w8d6_final_assessment/f3_cleaning/lab/clean.py    # prints head, dtypes, missing counts
python wb.py check lessons/w8d6_final_assessment/f3_cleaning      # or:
python -m pytest lessons/w8d6_final_assessment/f3_cleaning/checks -q
```

The starter raises `NotImplementedError`, so every check fails until you implement `clean`.

## Acceptance criteria

* All checks pass, including the comparison of the full file with the generator's ground truth.
* `NOTES.md` shows the defects were *found by inspection* (counts, examples), not inferred from test names.

## Submit

`lab/clean.py`, `lab/NOTES.md`, time used.
