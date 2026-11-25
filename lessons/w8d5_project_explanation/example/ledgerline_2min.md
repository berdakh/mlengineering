# 2-minute walkthrough: the LedgerLine transfer exercise (worked example)

The project is the course's w3d6 transfer task: ranking invoices for 15 collection calls a week
(SYNTHETIC data). It is used here because its honest result is *unflattering* - which is exactly the
story interviewers want to hear told well.

## Problem

LedgerLine's collections team can make fifteen proactive calls a week about invoices that might be
paid late. They chose by gut feeling and asked whether a model would choose better than a simple rule
they could apply themselves. The decision metric was therefore the share of the fifteen weekly calls
that reach an invoice which really goes late, measured on weeks after the model would have been trained.

## Constraint

A late label is only known thirty days after the due date, so on the training cut-off many recent
invoices had no label yet. Several exported columns, such as days to payment and the number of
reminders sent, are written after the invoice is issued. And invoices of one customer are related, so
the uncertainty comes from customers, not from individual invoices.

## Decision

I trained once on invoices whose labels were known before the cut-off, tested on invoices issued
after it, and removed every column not known on the issue date. I compared a rule - call the
customers with the worst resolved payment history - with a logistic regression on issue-time
features, and resampled customers for the interval.

## Evidence

The rule reached a weekly top-fifteen precision of 0.727. The model reached 0.722, with a customer
bootstrap interval of [0.651, 0.783] over 209 calls. So the model did not beat the rule: the
difference is far inside the interval.

## Limitation

The data are synthetic, so nothing here says how real customers behave. The interval covers which
customers happened to be in the test period, not retraining or a change in the customer mix. Calls
change behaviour, so once deployed the labels would be affected by the policy itself.

## Next step

Recommend the rule now, because it is free, explainable and as good as the model on this evidence. Log
every call and outcome so that a model can be re-evaluated on real policy data later, and set in
advance the difference that would justify switching.
