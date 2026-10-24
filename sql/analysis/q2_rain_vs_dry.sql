-- ============================================================
-- Q2: Do trip counts drop or rise on rainy days vs dry days?
-- ============================================================

SELECT
    dw.weather_category,
    COUNT(*) AS trip_count,
    ROUND(AVG(f.fare_amount), 2) AS avg_fare,
    ROUND(AVG(f.trip_distance_miles), 2) AS avg_distance_miles,
    ROUND(AVG(f.trip_duration_minutes), 2) AS avg_duration_minutes,
    ROUND(AVG(f.tip_amount), 2) AS avg_tip
FROM marts.fact_trips f
JOIN marts.dim_weather dw ON f.weather_key = dw.weather_key
GROUP BY dw.weather_category
ORDER BY trip_count DESC;
