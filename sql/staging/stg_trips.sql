-- ============================================================
-- Staging: stg_trips
-- ============================================================
-- Cleans, types, deduplicates, and validates raw taxi trip data.
-- Implements FR-10 through FR-13.
--
-- Idempotent: DROP + CREATE.
-- ============================================================

DROP TABLE IF EXISTS staging.stg_trips;

CREATE TABLE staging.stg_trips AS
WITH deduplicated AS (
    -- FR-12: Remove exact duplicate rows
    SELECT DISTINCT
        tpep_pickup_datetime,
        tpep_dropoff_datetime,
        passenger_count,
        trip_distance,
        PULocationID,
        DOLocationID,
        RatecodeID,
        store_and_fwd_flag,
        payment_type,
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        improvement_surcharge,
        total_amount,
        congestion_surcharge,
        airport_fee,
        _source_file,
        _loaded_at
    FROM raw.taxi_trips
),
-- FR-10 & FR-11: Cast types and rename to snake_case
typed AS (
    SELECT
        CAST(tpep_pickup_datetime AS TIMESTAMP)   AS pickup_datetime,
        CAST(tpep_dropoff_datetime AS TIMESTAMP)  AS dropoff_datetime,
        CAST(passenger_count AS INTEGER)           AS passenger_count,
        CAST(trip_distance AS DOUBLE)              AS trip_distance_miles,
        CAST(PULocationID AS INTEGER)              AS pickup_location_id,
        CAST(DOLocationID AS INTEGER)              AS dropoff_location_id,
        CAST(RatecodeID AS INTEGER)                AS rate_code_id,
        CAST(store_and_fwd_flag AS VARCHAR)        AS store_and_fwd_flag,
        CAST(payment_type AS INTEGER)              AS payment_type,
        CAST(fare_amount AS DECIMAL(10,2))         AS fare_amount,
        CAST(extra AS DECIMAL(10,2))               AS extra_amount,
        CAST(mta_tax AS DECIMAL(10,2))             AS mta_tax,
        CAST(tip_amount AS DECIMAL(10,2))          AS tip_amount,
        CAST(tolls_amount AS DECIMAL(10,2))        AS tolls_amount,
        CAST(improvement_surcharge AS DECIMAL(10,2)) AS improvement_surcharge,
        CAST(total_amount AS DECIMAL(10,2))        AS total_amount,
        CAST(congestion_surcharge AS DECIMAL(10,2)) AS congestion_surcharge,
        CAST(airport_fee AS DECIMAL(10,2))         AS airport_fee,
        -- Derived: trip duration in minutes
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

-- FR-13: Filter invalid trips
SELECT *
FROM typed
WHERE
    -- Positive fares
    fare_amount > 0
    -- Positive distance
    AND trip_distance_miles > 0
    -- Dropoff after pickup
    AND dropoff_datetime > pickup_datetime
    -- Passenger count within bounds
    AND passenger_count >= 0
    AND passenger_count <= 8
    -- Trip duration within reason (up to 12 hours)
    AND trip_duration_minutes > 0
    AND trip_duration_minutes <= 720
    -- Fare within plausible range
    AND fare_amount <= 1000
    -- Distance within plausible range
    AND trip_distance_miles <= 200;
