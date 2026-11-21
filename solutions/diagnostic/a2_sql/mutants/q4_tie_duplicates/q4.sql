SELECT i.customer_id, i.invoice_id, i.invoice_date
FROM invoices AS i
JOIN (SELECT customer_id, MAX(invoice_date) AS d FROM invoices GROUP BY customer_id) AS m
  ON m.customer_id = i.customer_id AND m.d = i.invoice_date
WHERE i.status = 'failed';
