-- q3: per enterprise account, total delivered fee and number of complaints.
-- Aggregate each child table to one row per account BEFORE joining: joining shipments and complaints
-- in one step yields (#shipments x #complaints) rows per account and inflates both figures.
WITH fees AS (
    SELECT account_id, SUM(fee) AS total_fee
    FROM shipments WHERE status = 'delivered' GROUP BY account_id
),
cmp AS (
    SELECT account_id, COUNT(*) AS n_complaints
    FROM complaints WHERE account_id IS NOT NULL GROUP BY account_id
)
SELECT a.account_id,
       ROUND(COALESCE(fees.total_fee, 0), 2) AS total_delivered_fee,
       COALESCE(cmp.n_complaints, 0)         AS n_complaints
FROM accounts AS a
LEFT JOIN fees ON fees.account_id = a.account_id
LEFT JOIN cmp  ON cmp.account_id = a.account_id
WHERE a.tier = 'enterprise';
