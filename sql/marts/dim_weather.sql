-- ============================================================
-- Marts: dim_weather
-- ============================================================
-- Weather dimension at hourly grain.
-- Implements FR-20. Surrogate keys via row_number (FR-22).
--
-- Idempotent: DROP + CREATE.
-- ============================================================

DROP TABLE IF EXISTS marts.dim_weather;

CREATE TABLE marts.dim_weather AS
WITH weather_records AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY observation_hour) AS weather_key,
        observation_hour,
        temperature_c,
        precipitation_mm,
        rain_mm,
        snowfall_cm,
        wind_speed_kmh,
        weather_category
    FROM staging.stg_weather
),
unknown_weather AS (
    SELECT
        0 AS weather_key,
        CAST(NULL AS TIMESTAMP) AS observation_hour,
        CAST(NULL AS DOUBLE)    AS temperature_c,
        CAST(NULL AS DOUBLE)    AS precipitation_mm,
        CAST(NULL AS DOUBLE)    AS rain_mm,
        CAST(NULL AS DOUBLE)    AS snowfall_cm,
        CAST(NULL AS DOUBLE)    AS wind_speed_kmh,
        'unknown'               AS weather_category
)
SELECT * FROM unknown_weather
UNION ALL
SELECT * FROM weather_records
ORDER BY weather_key;
