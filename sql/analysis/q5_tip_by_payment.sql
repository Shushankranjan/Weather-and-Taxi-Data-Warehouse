-- ============================================================
-- Q5: Average tip percentage by payment type
-- ============================================================

SELECT
    dp.payment_type_description,
    COUNT(*) AS trip_count,
    ROUND(AVG(f.tip_amount), 2) AS avg_tip,
    ROUND(AVG(f.fare_amount), 2) AS avg_fare,
    ROUND(
        AVG(
            CASE
                WHEN f.fare_amount > 0
                THEN (f.tip_amount / f.fare_amount) * 100
                ELSE 0
            END
        ),
        2
    ) AS avg_tip_percentage
FROM marts.fact_trips f
JOIN marts.dim_payment_type dp ON f.payment_type_key = dp.payment_type_key
GROUP BY dp.payment_type_description
ORDER BY avg_tip_percentage DESC;
