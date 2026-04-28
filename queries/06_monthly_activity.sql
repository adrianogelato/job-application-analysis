-- Monthly Activity
-- Applications submitted and rejections received per calendar month

WITH monthly_submissions AS (
    SELECT
        DATE_TRUNC('month', application_date)   AS month,
        COUNT(*)                                AS submissions
    FROM applications
    WHERE status != 'open'
      AND application_date IS NOT NULL
    GROUP BY 1
),
monthly_rejections AS (
    SELECT
        DATE_TRUNC('month', end_date)           AS month,
        COUNT(*)                                AS rejections
    FROM applications
    WHERE status = 'rejected'
      AND end_date IS NOT NULL
    GROUP BY 1
),
all_months AS (
    SELECT month FROM monthly_submissions
    UNION
    SELECT month FROM monthly_rejections
)
SELECT
    a.month,
    COALESCE(ma.submissions, 0)               AS submissions,
    COALESCE(mr.rejections, 0)                 AS rejections
FROM all_months a
LEFT JOIN monthly_submissions ma ON a.month = ma.month
LEFT JOIN monthly_rejections    mr ON a.month = mr.month
ORDER BY a.month
