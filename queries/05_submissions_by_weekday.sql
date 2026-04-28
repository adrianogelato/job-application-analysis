-- Submissions by Weekday
-- Number of applications submitted per day of the week (ordered Mon–Sun)

SELECT
    CASE EXTRACT('isodow' FROM application_date)
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
        WHEN 7 THEN 'Sunday'
    END                                         AS weekday,
    COUNT(*)                                    AS count,
    MIN(EXTRACT('isodow' FROM application_date))        AS sort_order
FROM applications
WHERE status != 'open'
  AND application_date IS NOT NULL
GROUP BY EXTRACT('isodow' FROM application_date)
ORDER BY sort_order
