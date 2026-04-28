-- Summary Stats
-- Key metadata about the application campaign

SELECT
    MIN(application_date)                           AS first_submission,
    MAX(application_date)                           AS latest_submission,
    COUNT(*) FILTER (WHERE status != 'open')        AS total_submitted,
    COUNT(*) FILTER (WHERE status = 'rejected')     AS total_rejected,
    COUNT(*) FILTER (WHERE status = 'ghosted')      AS total_ghosted,
    COUNT(*) FILTER (WHERE status = 'interviewing') AS total_interviewing,
    COUNT(*) FILTER (WHERE status = 'waiting')      AS total_waiting,
    COUNT(*) FILTER (WHERE status = 'open')         AS total_open
FROM applications
