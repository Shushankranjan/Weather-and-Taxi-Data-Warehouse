-- ============================================================
-- Data Quality Checks
-- ============================================================
-- Each check returns a result row. If any "Must" check returns
-- a non-zero failure count, the pipeline should fail (FR-28).
--
-- The Python runner executes these and inspects the results.
-- ============================================================


-- CHECK 1: No nulls in fact_trips primary key (FR-23)
-- Expected: 0 failures
SELECT
    'fact_trips_pk_not_null' AS check_name,
    'Must' AS priority,
    COUNT(*) AS failures
FROM marts.fact_trips
WHERE trip_key IS NULL;

-- CHECK 2: No nulls in required foreign keys (FR-23)
-- Expected: 0 failures
SELECT
    'fact_trips_fk_not_null' AS check_name,
    'Must' AS priority,
    COUNT(*) AS failures
FROM marts.fact_trips
WHERE pickup_date_key IS NULL
   OR pickup_time_key IS NULL
   OR pickup_location_key IS NULL
   OR dropoff_location_key IS NULL
   OR payment_type_key IS NULL;

-- CHECK 3: Unique dimension keys (FR-24)
-- dim_date
SELECT
    'dim_date_unique_key' AS check_name,
    'Must' AS priority,
    COUNT(*) - COUNT(DISTINCT date_key) AS failures
FROM marts.dim_date;

-- dim_time
SELECT
    'dim_time_unique_key' AS check_name,
    'Must' AS priority,
    COUNT(*) - COUNT(DISTINCT time_key) AS failures
FROM marts.dim_time;

-- dim_location
SELECT
    'dim_location_unique_key' AS check_name,
    'Must' AS priority,
    COUNT(*) - COUNT(DISTINCT location_key) AS failures
FROM marts.dim_location;

-- dim_payment_type
SELECT
    'dim_payment_type_unique_key' AS check_name,
    'Must' AS priority,
    COUNT(*) - COUNT(DISTINCT payment_type_key) AS failures
FROM marts.dim_payment_type;

-- dim_weather
SELECT
    'dim_weather_unique_key' AS check_name,
    'Must' AS priority,
    COUNT(*) - COUNT(DISTINCT weather_key) AS failures
FROM marts.dim_weather;

-- CHECK 4: Referential integrity — pickup_date_key (FR-25)
SELECT
    'fk_pickup_date_key' AS check_name,
    'Must' AS priority,
    COUNT(*) AS failures
FROM marts.fact_trips f
WHERE NOT EXISTS (
    SELECT 1 FROM marts.dim_date d
    WHERE d.date_key = f.pickup_date_key
);

-- CHECK 5: Referential integrity — pickup_time_key
SELECT
    'fk_pickup_time_key' AS check_name,
    'Must' AS priority,
    COUNT(*) AS failures
FROM marts.fact_trips f
WHERE NOT EXISTS (
    SELECT 1 FROM marts.dim_time t
    WHERE t.time_key = f.pickup_time_key
);

-- CHECK 6: Referential integrity — pickup_location_key
SELECT
    'fk_pickup_location_key' AS check_name,
    'Must' AS priority,
    COUNT(*) AS failures
FROM marts.fact_trips f
WHERE NOT EXISTS (
    SELECT 1 FROM marts.dim_location l
    WHERE l.location_key = f.pickup_location_key
);

-- CHECK 7: Referential integrity — payment_type_key
SELECT
    'fk_payment_type_key' AS check_name,
    'Must' AS priority,
    COUNT(*) AS failures
FROM marts.fact_trips f
WHERE NOT EXISTS (
    SELECT 1 FROM marts.dim_payment_type p
    WHERE p.payment_type_key = f.payment_type_key
);

-- CHECK 7b: Referential integrity — weather_key
SELECT
    'fk_weather_key' AS check_name,
    'Must' AS priority,
    COUNT(*) AS failures
FROM marts.fact_trips f
WHERE NOT EXISTS (
    SELECT 1 FROM marts.dim_weather w
    WHERE w.weather_key = f.weather_key
);

-- CHECK 8: Row count reconciliation (FR-26)
-- raw (deduplicated) = staging + rejected
SELECT
    'row_count_reconciliation' AS check_name,
    'Must' AS priority,
    ABS(
        (SELECT COUNT(DISTINCT (
            tpep_pickup_datetime, tpep_dropoff_datetime,
            passenger_count, trip_distance, fare_amount, total_amount
        )) FROM raw.taxi_trips)
        -
        (SELECT COUNT(*) FROM staging.stg_trips)
        -
        (SELECT COUNT(*) FROM staging.rejected_trips)
    ) AS failures;

-- CHECK 9: Value range — fare (FR-27)
SELECT
    'fare_in_range' AS check_name,
    'Should' AS priority,
    COUNT(*) AS failures
FROM marts.fact_trips
WHERE fare_amount <= 0 OR fare_amount > 1000;

-- CHECK 10: Value range — distance (FR-27)
SELECT
    'distance_in_range' AS check_name,
    'Should' AS priority,
    COUNT(*) AS failures
FROM marts.fact_trips
WHERE trip_distance_miles <= 0 OR trip_distance_miles > 200;
