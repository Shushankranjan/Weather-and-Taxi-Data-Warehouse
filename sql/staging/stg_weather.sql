-- ============================================================
-- Staging: stg_weather
-- ============================================================
-- Cleans and standardizes raw weather data.
-- Timestamps are already in America/New_York from the API call,
-- so we validate and type them here (FR-14).
--
-- Idempotent: DROP + CREATE.
-- ============================================================

DROP TABLE IF EXISTS staging.stg_weather;

CREATE TABLE staging.stg_weather AS
SELECT
    CAST(observation_time AS TIMESTAMP) AS observation_hour,
    CAST(temperature_c AS DOUBLE)      AS temperature_c,
    CAST(precipitation_mm AS DOUBLE)   AS precipitation_mm,
    CAST(rain_mm AS DOUBLE)            AS rain_mm,
    CAST(snowfall_cm AS DOUBLE)        AS snowfall_cm,
    CAST(wind_speed_kmh AS DOUBLE)     AS wind_speed_kmh,
    CAST(weather_code AS INTEGER)      AS weather_code,
    -- Weather category (FR-20 / Section 8.3 rules)
    CASE
        WHEN COALESCE(CAST(snowfall_cm AS DOUBLE), 0) > 0 THEN 'snow'
        WHEN COALESCE(CAST(precipitation_mm AS DOUBLE), 0) > 0.1 THEN 'rain'
        ELSE 'clear'
    END AS weather_category
FROM raw.weather
WHERE observation_time IS NOT NULL;
