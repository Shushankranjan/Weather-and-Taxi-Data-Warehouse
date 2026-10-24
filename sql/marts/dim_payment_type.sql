-- ============================================================
-- Marts: dim_payment_type
-- ============================================================
-- Payment type dimension with code-to-description mapping.
-- Implements FR-19.
--
-- Idempotent: DROP + CREATE.
-- ============================================================

DROP TABLE IF EXISTS marts.dim_payment_type;

CREATE TABLE marts.dim_payment_type AS
SELECT * FROM (
    VALUES
        (0, 0, 'Unknown / Not specified'),
        (1, 1, 'Credit card'),
        (2, 2, 'Cash'),
        (3, 3, 'No charge'),
        (4, 4, 'Dispute'),
        (5, 5, 'Unknown'),
        (6, 6, 'Voided trip')
) AS t(payment_type_key, payment_type_code, payment_type_description);
