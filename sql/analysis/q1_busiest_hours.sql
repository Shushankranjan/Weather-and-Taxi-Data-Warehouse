-- ============================================================
-- Q1: Busiest hours and days of the week for taxi trips
-- ============================================================

SELECT
    dd.day_name,
    dd.day_of_week,
    dt.hour_label,
    dt.time_of_day_bucket,
    COUNT(*) AS trip_count,
    ROUND(AVG(f.fare_amount), 2) AS avg_fare,
    ROUND(AVG(f.trip_distance_miles), 2) AS avg_distance
FROM marts.fact_trips f
JOIN marts.dim_date dd ON f.pickup_date_key = dd.date_key
JOIN marts.dim_time dt ON f.pickup_time_key = dt.time_key
GROUP BY dd.day_name, dd.day_of_week, dt.hour_label, dt.time_of_day_bucket, dt.hour_24
ORDER BY trip_count DESC
LIMIT 20;
