# Mutant: export-time aggregate used under another name

`FEATURES` is clean, but the design matrix adds `customer_late_rate` as `customer_history_score`.
That column is the customer's late share over ALL their invoices, including the test-period ones and
the invoice being scored: target leakage through an aggregate. It is the subtle leak of this table,
because a history rate is exactly the feature one wants; the honest version is
`prior_late_invoices / prior_resolved_invoices`. Test AUC rises from about 0.76 to about 0.86, above the
generator's own 0.825.

Passes the declared-features check. Rejected by the scramble check and the generator-bound check.
