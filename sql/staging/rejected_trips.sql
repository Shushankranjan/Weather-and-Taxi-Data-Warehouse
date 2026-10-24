-- ============================================================
-- Staging: rejected_trips
-- ============================================================
-- Captures rows filtered out during staging with rejection reasons.
-- Implements FR-15.
--
-- Idempotent: DROP + CREATE.
-- ============================================================

DROP TABLE IF EXISTS staging.rejected_trips;

CREATE TABLE staging.rejected_trips AS
WITH deduplicated AS (
    SELECT DISTINCT
        tpep_pickup_datetime,
        tpep_dropoff_datetime,
        passenger_count,
        trip_distance,
        PULocationID,
        DOLocationID,
        payment_type,
        fare_amount,
        tip_amount,
        total_amount,
        _source_file,
        _loaded_at
    FROM raw.taxi_trips
),
typed AS (
    SELECT
        CAST(tpep_pickup_datetime AS TIMESTAMP)   AS pickup_datetime,
        CAST(tpep_dropoff_datetime AS TIMESTAMP)  AS dropoff_datetime,
        CAST(passenger_count AS INTEGER)           AS passenger_count,
        CAST(trip_distance AS DOUBLE)              AS trip_distance_miles,
        CAST(PULocationID AS INTEGER)              AS pickup_location_id,
        CAST(DOLocationID AS INTEGER)              AS dropoff_location_id,
        CAST(payment_type AS INTEGER)              AS payment_type,
        CAST(fare_amount AS DECIMAL(10,2))         AS fare_amount,
        CAST(tip_amount AS DECIMAL(10,2))          AS tip_amount,
        CAST(total_amount AS DECIMAL(10,2))        AS total_amount,
        ROUND(
            EXTRACT(EPOCH FROM (
                CAST(tpep_dropoff_datetime AS TIMESTAMP)
                - CAST(tpep_pickup_datetime AS TIMESTAMP)
            )) / 60.0,
            2
        ) AS trip_duration_minutes,
        _source_file,
        _loaded_at
    FROM deduplicated
)

SELECT
    *,
    CASE
        WHEN fare_amount <= 0 THEN 'non_positive_fare'
        WHEN trip_distance_miles <= 0 THEN 'zero_or_negative_distance'
        WHEN dropoff_datetime <= pickup_datetime THEN 'dropoff_before_pickup'
        WHEN passenger_count < 0 OR passenger_count > 8 THEN 'invalid_passenger_count'
        WHEN trip_duration_minutes <= 0 OR trip_duration_minutes > 720 THEN 'invalid_duration'
        WHEN fare_amount > 1000 THEN 'excessive_fare'
        WHEN trip_distance_miles > 200 THEN 'excessive_distance'
        ELSE 'unknown'
    END AS rejection_reason
FROM typed
WHERE
    fare_amount <= 0
    OR trip_distance_miles <= 0
    OR dropoff_datetime <= pickup_datetime
    OR passenger_count < 0
    OR passenger_count > 8
    OR trip_duration_minutes <= 0
    OR trip_duration_minutes > 720
    OR fare_amount > 1000
    OR trip_distance_miles > 200;
