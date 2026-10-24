-- ============================================================
-- Q3: How does temperature affect average trip distance and fare?
-- ============================================================

SELECT
    -- Bucket temperatures into 5°C bands
    FLOOR(dw.temperature_c / 5) * 5 AS temp_bucket_c,
    CONCAT(
        CAST(FLOOR(dw.temperature_c / 5) * 5 AS VARCHAR),
        '°C to ',
        CAST(FLOOR(dw.temperature_c / 5) * 5 + 5 AS VARCHAR),
        '°C'
    ) AS temp_range,
    COUNT(*) AS trip_count,
    ROUND(AVG(f.trip_distance_miles), 2) AS avg_distance_miles,
    ROUND(AVG(f.fare_amount), 2) AS avg_fare,
    ROUND(AVG(f.trip_duration_minutes), 2) AS avg_duration_minutes
FROM marts.fact_trips f
JOIN marts.dim_weather dw ON f.weather_key = dw.weather_key
WHERE dw.temperature_c IS NOT NULL
GROUP BY temp_bucket_c, temp_range
ORDER BY temp_bucket_c;
