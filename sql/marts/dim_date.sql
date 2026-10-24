-- ============================================================
-- Marts: dim_date
-- ============================================================
-- Date dimension covering the full date range from taxi trips.
-- Implements FR-16.
--
-- Idempotent: DROP + CREATE.
-- ============================================================

DROP TABLE IF EXISTS marts.dim_date;

CREATE TABLE marts.dim_date AS
WITH date_range AS (
    SELECT
        CAST(MIN(pickup_datetime) AS DATE) AS min_date,
        CAST(MAX(pickup_datetime) AS DATE) AS max_date
    FROM staging.stg_trips
),
date_spine AS (
    SELECT
        UNNEST(
            generate_series(
                (SELECT min_date FROM date_range),
                (SELECT max_date FROM date_range),
                INTERVAL '1 day'
            )
        ) AS full_date
)

SELECT
    -- Surrogate key: YYYYMMDD integer
    CAST(STRFTIME(full_date, '%Y%m%d') AS INTEGER) AS date_key,
    CAST(full_date AS DATE)                        AS full_date,
    EXTRACT(DOW FROM full_date)                    AS day_of_week,
    DAYNAME(full_date)                             AS day_name,
    EXTRACT(WEEK FROM full_date)                   AS week_of_year,
    EXTRACT(MONTH FROM full_date)                  AS month,
    MONTHNAME(full_date)                           AS month_name,
    EXTRACT(QUARTER FROM full_date)                AS quarter,
    EXTRACT(YEAR FROM full_date)                   AS year,
    CASE
        WHEN EXTRACT(DOW FROM full_date) IN (0, 6) THEN TRUE
        ELSE FALSE
    END AS is_weekend
FROM date_spine
ORDER BY full_date;
