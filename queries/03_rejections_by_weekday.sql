-- Rejections by Weekday
-- Number of rejections received per day of the week (ordered Mon–Sun)

SELECT
    CASE EXTRACT('isodow' FROM end_date)
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
        WHEN 7 THEN 'Sunday'
    END                                         AS weekday,
    COUNT(*)                                    AS count,
    MIN(EXTRACT('isodow' FROM end_date))        AS sort_order
FROM applications
WHERE status = 'rejected'
  AND end_date IS NOT NULL
GROUP BY EXTRACT('isodow' FROM end_date)
ORDER BY sort_order
