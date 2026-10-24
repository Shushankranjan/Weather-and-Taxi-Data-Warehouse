-- ============================================================
-- Marts: dim_location
-- ============================================================
-- Location dimension from the taxi zone lookup.
-- Implements FR-18.
--
-- Idempotent: DROP + CREATE.
-- ============================================================

DROP TABLE IF EXISTS marts.dim_location;

CREATE TABLE marts.dim_location AS
WITH base_locations AS (
    SELECT
        CAST(LocationID AS INTEGER) AS location_key,
        CAST(LocationID AS INTEGER) AS location_id,
        Borough                     AS borough,
        Zone                        AS zone,
        service_zone                AS service_zone
    FROM raw.zones
),
unknown_location AS (
    SELECT
        0 AS location_key,
        0 AS location_id,
        'Unknown' AS borough,
        'Unknown' AS zone,
        'Unknown' AS service_zone
)
SELECT * FROM base_locations
UNION ALL
SELECT * FROM unknown_location
WHERE NOT EXISTS (SELECT 1 FROM base_locations WHERE location_key = 0)
ORDER BY location_key;
