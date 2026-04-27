-- Rejection Duration
-- Days between application submission and rejection for each rejected application

SELECT
    company,
    role,
    application_date,
    end_date,
    DATEDIFF('day', application_date, end_date)     AS days_to_rejection
FROM applications
WHERE status = 'rejected'
  AND application_date IS NOT NULL
  AND end_date IS NOT NULL
ORDER BY days_to_rejection
