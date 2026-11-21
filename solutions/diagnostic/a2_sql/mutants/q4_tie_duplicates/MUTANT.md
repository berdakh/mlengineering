q4 joins on MAX(invoice_date) and ignores the tie-break: customers whose failed charge was retried successfully on the same day are wrongly reported.
