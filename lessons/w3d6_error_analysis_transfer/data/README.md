# LedgerLine invoices (SYNTHETIC)

`invoices.csv`: 11,088 invoices issued by an invented B2B software vendor to 650 customers between
2023-01-01 and 2024-12-31, exported from the billing system on **2025-03-15**. Every row is simulated
by `make_invoices.py` (seeded; `--check` confirms the committed file regenerates byte-identically on
NumPy 2.5.3 / pandas 3.0.5).

**What cannot be concluded from it:** anything about real payment behaviour, realistic effect sizes,
or which model family suits such data. It supports conclusions about *your evaluation procedure*,
because the generator's ground truth is known to the checks.

Do not read `make_invoices.py` before the exercise: it states which columns leak.

| Column | Type | Description, as a data dictionary from the billing team would give it |
|---|---|---|
| `invoice_id` | int | sequential invoice number |
| `customer_id` | str | customer account |
| `segment` | str | `smb`, `mid`, `enterprise` |
| `industry` | str | customer industry (6 values) |
| `country` | str | billing country (5 values) |
| `issue_date` | date | day the invoice was issued |
| `due_date` | date | `issue_date` + `payment_terms_days` |
| `payment_terms_days` | int | 14, 30 or 60 |
| `amount` | float | invoice amount, EUR |
| `prior_invoices` | int | number of earlier invoices to this customer |
| `prior_resolved_invoices` | int | earlier invoices whose late/on-time outcome was already decided on `issue_date` |
| `prior_late_invoices` | int | of those, how many were late |
| `customer_late_rate` | float | "share of the customer's invoices paid late" (from the customer master table) |
| `account_status` | str | `active` or `on_hold` (from the customer master table) |
| `reminders_sent` | int | payment reminders sent for this invoice |
| `days_to_payment` | float | days from issue to payment; empty if unpaid at export |
| `late` | int | **label**: 1 if the invoice was still unpaid 30 days after its due date |

The descriptions are deliberately the kind you receive in practice: accurate, and silent about *when*
each value becomes known. Working that out is part of the exercise.

A label fact you need: `late` is decided on `due_date + 30 days`. Before that day nobody knows it.
