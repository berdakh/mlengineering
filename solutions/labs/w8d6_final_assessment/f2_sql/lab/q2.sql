-- q2: 2025 signups that never filed a complaint.
-- NOT EXISTS is NULL-safe. `NOT IN (SELECT account_id FROM complaints)` returns no rows at all,
-- because complaints.account_id contains NULLs (web-form complaints) and `x NOT IN (..., NULL)` is never TRUE.
SELECT a.account_id
FROM accounts AS a
WHERE a.signup_date >= '2025-01-01' AND a.signup_date < '2026-01-01'
  AND NOT EXISTS (SELECT 1 FROM complaints AS c WHERE c.account_id = a.account_id);
