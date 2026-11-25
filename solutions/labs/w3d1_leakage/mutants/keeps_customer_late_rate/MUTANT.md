# Mutant: keeps_customer_late_rate

Keeps `customer_late_rate` because it 'looks like `prior_late_rate`'. It is an aggregate over all of the customer's invoices in the export, including later ones and the row itself (temporal aggregate leakage).
