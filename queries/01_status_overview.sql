-- Status Overview
-- Count and percentage share of each status, excluding 'open' (not yet submitted)

WITH all_statuses (status, sort_order) AS (
    VALUES
        ('open',         1),
        ('waiting',      2),
        ('interviewing', 3),
        ('rejected',     4),
        ('ghosted',      5)
),
counts AS (
    SELECT status, COUNT(*) AS count
    FROM applications
    GROUP BY status
)
SELECT
    a.status,
    COALESCE(c.count, 0)                                                        AS count,
    ROUND(100.0 * COALESCE(c.count, 0) / SUM(COALESCE(c.count, 0)) OVER (), 1) AS percentage
FROM all_statuses a
LEFT JOIN counts c ON a.status = c.status
ORDER BY a.sort_order