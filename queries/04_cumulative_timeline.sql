-- Cumulative Timeline
-- Running totals of applications submitted, rejections received, and interviews started over time

WITH events AS (
    SELECT application_date   AS event_date, 'application'  AS event_type
    FROM applications
    WHERE status != 'open'
      AND application_date IS NOT NULL

    UNION ALL

    SELECT end_date           AS event_date, 'rejection'    AS event_type
    FROM applications
    WHERE status = 'rejected'
      AND end_date IS NOT NULL

    UNION ALL

    SELECT interview_date     AS event_date, 'interview'    AS event_type
    FROM applications
    WHERE interview_date IS NOT NULL
),

daily_counts AS (
    SELECT
        event_date,
        COUNT(*) FILTER (WHERE event_type = 'application')  AS applications,
        COUNT(*) FILTER (WHERE event_type = 'rejection')    AS rejections,
        COUNT(*) FILTER (WHERE event_type = 'interview')    AS interviews
    FROM events
    GROUP BY event_date
)

SELECT
    event_date,
    SUM(applications)   OVER (ORDER BY event_date)  AS cumulative_applications,
    SUM(rejections)     OVER (ORDER BY event_date)  AS cumulative_rejections,
    SUM(interviews)     OVER (ORDER BY event_date)  AS cumulative_interviews
FROM daily_counts
ORDER BY event_date
