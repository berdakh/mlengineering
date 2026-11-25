# Late-payment prediction for invoices (SYNTHETIC report for peer review)

Prepared by a colleague for the finance-operations team. This report and its numbers are invented for the
exercise; review it as you would a real one.

## 1. Problem

Finance operations sends payment reminders. They would like to know, when an invoice is issued, whether it
will be paid more than 30 days late, so that they can call those customers early.

## 2. Data

We used 48,000 invoices from 3,100 business customers issued between January 2024 and June 2026. About 6 %
of invoices were paid more than 30 days late. Each customer has on average 15 invoices.

Features: invoice amount, customer industry, customer size, payment terms, number of previous late
invoices, days_since_last_reminder, and month of issue.

## 3. Method

We split the 48,000 invoices at random into 80 % training and 20 % test.
We trained a gradient-boosted classifier with default settings and a logistic regression baseline.
We then chose the threshold that maximised F1 on the test set.

## 4. Results

The model reaches 94.1 % accuracy on the test set, which shows it is highly reliable.

| Model | AUC | Recall | Precision |
|---|---|---|---|
| Gradient-boosted trees | 0.71 | 0.58 | 0.21 |
| Logistic regression | 0.69 | 0.49 | 0.18 |

The gradient-boosted model is significantly better than the logistic baseline (0.71 vs 0.69 AUC).
At the chosen threshold it finds 0.62 of the late invoices.

The most important feature by far is days_since_last_reminder, followed by invoice amount.

## 5. Conclusions

Reducing invoice amounts will cause customers to pay on time, so sales should split large invoices.
The model will work equally well for the German market we launch next quarter.
We recommend deploying it to all customers next month.

## 6. Limitations

None identified.
