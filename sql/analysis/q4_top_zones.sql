-- ============================================================
-- Q4: Which pickup zones generate the most trips and revenue?
-- ============================================================

SELECT
    dl.borough,
    dl.zone,
    COUNT(*) AS trip_count,
    ROUND(SUM(f.total_amount), 2) AS total_revenue,
    ROUND(AVG(f.fare_amount), 2) AS avg_fare,
    ROUND(AVG(f.tip_amount), 2) AS avg_tip,
    ROUND(AVG(f.trip_distance_miles), 2) AS avg_distance
FROM marts.fact_trips f
JOIN marts.dim_location dl ON f.pickup_location_key = dl.location_key
GROUP BY dl.borough, dl.zone
ORDER BY trip_count DESC
LIMIT 20;
