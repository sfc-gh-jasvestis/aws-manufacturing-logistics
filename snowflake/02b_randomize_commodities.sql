-- Re-randomize SHIPMENTS commodity distribution + tier-based VALUE_USD
-- Replaces the uniform/flat S3 seed with realistic commodity skew:
--  Electronics & Consumer Goods dominate volume; Pharma/Medical skew highest unit value;
--  Agricultural/Raw Materials lowest. Result: ~95x spread between top and bottom commodity.
-- Hash-based deterministic randomness so reruns are stable.

USE SCHEMA MANUFACTURING_SUPPLY_CHAIN.RAW;

CREATE OR REPLACE TABLE SHIPMENTS AS
WITH tiered AS (
  SELECT
    SHIPMENT_ID, ORIGIN_PORT, DEST_PORT, CARRIER_ID, STATUS, ETD, ETA, ACTUAL_ARRIVAL, CONTAINER_COUNT,
    ABS(HASH(SHIPMENT_ID, 'commodity')) % 1000 AS r_com,
    70 + (ABS(HASH(SHIPMENT_ID, 'value')) % 61) AS r_val_pct
  FROM SHIPMENTS
),
mapped AS (
  SELECT
    SHIPMENT_ID, ORIGIN_PORT, DEST_PORT, CARRIER_ID, STATUS, ETD, ETA, ACTUAL_ARRIVAL, CONTAINER_COUNT,
    CASE
      WHEN r_com < 220 THEN 'Consumer Goods'
      WHEN r_com < 380 THEN 'Electronics'
      WHEN r_com < 500 THEN 'Automotive Parts'
      WHEN r_com < 600 THEN 'Steel & Metals'
      WHEN r_com < 685 THEN 'Food & Beverage'
      WHEN r_com < 760 THEN 'Textiles'
      WHEN r_com < 820 THEN 'Chemicals'
      WHEN r_com < 870 THEN 'Furniture'
      WHEN r_com < 910 THEN 'Machinery'
      WHEN r_com < 940 THEN 'Plastics'
      WHEN r_com < 960 THEN 'Paper & Pulp'
      WHEN r_com < 975 THEN 'Raw Materials'
      WHEN r_com < 988 THEN 'Agricultural Products'
      WHEN r_com < 996 THEN 'Medical Equipment'
      ELSE 'Pharmaceuticals'
    END AS COMMODITY_TYPE,
    r_val_pct / 100.0 AS r_val_jitter
  FROM tiered
)
SELECT
  SHIPMENT_ID, ORIGIN_PORT, DEST_PORT, CARRIER_ID, STATUS, ETD, ETA, ACTUAL_ARRIVAL, CONTAINER_COUNT,
  (ROUND(CONTAINER_COUNT * r_val_jitter * CASE COMMODITY_TYPE
    WHEN 'Pharmaceuticals'       THEN 95000
    WHEN 'Medical Equipment'     THEN 78000
    WHEN 'Machinery'             THEN 62000
    WHEN 'Electronics'           THEN 52000
    WHEN 'Automotive Parts'      THEN 38000
    WHEN 'Chemicals'             THEN 22000
    WHEN 'Steel & Metals'        THEN 18000
    WHEN 'Consumer Goods'        THEN 16000
    WHEN 'Plastics'              THEN 14000
    WHEN 'Food & Beverage'       THEN 11000
    WHEN 'Furniture'             THEN 9000
    WHEN 'Textiles'              THEN 7500
    WHEN 'Agricultural Products' THEN 7000
    WHEN 'Raw Materials'         THEN 6500
    WHEN 'Paper & Pulp'          THEN 5500
  END, 2))::FLOAT AS VALUE_USD,
  COMMODITY_TYPE
FROM mapped;

ALTER DYNAMIC TABLE MANUFACTURING_SUPPLY_CHAIN.CURATED.SHIPMENT_STATUS REFRESH;
