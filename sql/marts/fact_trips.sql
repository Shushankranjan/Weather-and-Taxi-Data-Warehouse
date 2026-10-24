-- ============================================================
-- Marts: fact_trips
-- ============================================================
-- Fact table at one-row-per-trip grain with foreign keys
-- to all dimensions and numeric measures.
-- Implements FR-21 and FR-22.
--
-- Idempotent: DROP + CREATE.
-- ============================================================

DROP TABLE IF EXISTS marts.fact_trips;

CREATE TABLE marts.fact_trips AS
SELECT
    -- Surrogate primary key
    ROW_NUMBER() OVER (ORDER BY t.pickup_datetime, t.dropoff_datetime) AS trip_key,

    -- Foreign keys to dimensions (mapped with COALESCE to default 0 unknown record)
    CAST(STRFTIME(t.pickup_datetime, '%Y%m%d') AS INTEGER) AS pickup_date_key,
    EXTRACT(HOUR FROM t.pickup_datetime)                   AS pickup_time_key,
    COALESCE(dl_pu.location_key, 0)                        AS pickup_location_key,
    COALESCE(dl_do.location_key, 0)                        AS dropoff_location_key,
    COALESCE(dp.payment_type_key, 0)                       AS payment_type_key,
    COALESCE(dw.weather_key, 0)                            AS weather_key,

    -- Timestamps
    t.pickup_datetime,
    t.dropoff_datetime,

    -- Measures
    t.passenger_count,
    t.trip_distance_miles,
    t.trip_duration_minutes,
    t.fare_amount,
    t.tip_amount,
    t.total_amount

FROM staging.stg_trips t

-- Dimension key lookups
LEFT JOIN marts.dim_location dl_pu
    ON t.pickup_location_id = dl_pu.location_id
LEFT JOIN marts.dim_location dl_do
    ON t.dropoff_location_id = dl_do.location_id
LEFT JOIN marts.dim_payment_type dp
    ON t.payment_type = dp.payment_type_code
LEFT JOIN marts.dim_weather dw
    ON DATE_TRUNC('hour', t.pickup_datetime) = dw.observation_hour;
