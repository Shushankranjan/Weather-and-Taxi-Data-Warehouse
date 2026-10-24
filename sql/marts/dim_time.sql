-- ============================================================
-- Marts: dim_time
-- ============================================================
-- Time-of-day dimension at hourly grain.
-- Implements FR-17.
--
-- Idempotent: DROP + CREATE.
-- ============================================================

DROP TABLE IF EXISTS marts.dim_time;

CREATE TABLE marts.dim_time AS
SELECT
    hour_24 AS time_key,
    hour_24,
    CASE
        WHEN hour_24 = 0  THEN '12 AM'
        WHEN hour_24 < 12 THEN CAST(hour_24 AS VARCHAR) || ' AM'
        WHEN hour_24 = 12 THEN '12 PM'
        ELSE CAST(hour_24 - 12 AS VARCHAR) || ' PM'
    END AS hour_label,
    CASE
        WHEN hour_24 >= 5  AND hour_24 < 12 THEN 'morning'
        WHEN hour_24 >= 12 AND hour_24 < 17 THEN 'afternoon'
        WHEN hour_24 >= 17 AND hour_24 < 21 THEN 'evening'
        ELSE 'night'
    END AS time_of_day_bucket
FROM (
    SELECT UNNEST(generate_series(0, 23)) AS hour_24
);
