SELECT account_id FROM accounts
WHERE signup_date >= '2025-01-01' AND signup_date < '2026-01-01'
  AND account_id NOT IN (SELECT account_id FROM complaints);
