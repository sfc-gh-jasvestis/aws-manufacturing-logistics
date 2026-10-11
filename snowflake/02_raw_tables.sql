-- Synthetic site-day observations for a fictional Singapore manufacturing logistics network.
-- Nothing is seeded as a prediction. Randomness is HASH-seeded, so every rebuild is
-- reproducible: per-site capacity, equipment age and disruption propensity, volume from
-- weekly seasonality and a quarter-end shipping peak, wear between preventive-maintenance
-- (PM) visits, category-weighted disruption causes, and two regional events.
USE DATABASE IDENTIFIER($DEMO_DB);
USE SCHEMA RAW;
USE WAREHOUSE IDENTIFIER($DEMO_WH);

CREATE TABLE RAW.SITES AS
WITH sites AS (
  SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1 AS SITE_INDEX
  FROM TABLE(GENERATOR(ROWCOUNT => 30))
), draws AS (
  SELECT SITE_INDEX,
         MOD(ABS(HASH(SITE_INDEX, 'sg-mfglog-age')), 1000000) / 1e6 AS U_AGE,
         MOD(ABS(HASH(SITE_INDEX, 'sg-mfglog-rate')), 1000000) / 1e6 AS U_RATE,
         MOD(ABS(HASH(SITE_INDEX, 'sg-mfglog-pm')), 1000000) / 1e6 AS U_PM,
         MOD(ABS(HASH(SITE_INDEX, 'sg-mfglog-discipline')), 1000000) / 1e6 AS U_DISCIPLINE,
         MOD(ABS(HASH(SITE_INDEX, 'sg-mfglog-capacity')), 1000000) / 1e6 AS U_CAPACITY
  FROM sites
)
SELECT 'LG-' || LPAD(SITE_INDEX::VARCHAR, 4, '0') AS ID,
       'Synthetic site ' || LPAD(SITE_INDEX::VARCHAR, 4, '0') AS NAME,
       -- Deterministic spread (7 and 5 are coprime): every planning area and site type is
       -- present, with Tuas the largest area.
       CASE MOD(SITE_INDEX, 7) WHEN 0 THEN 'Tuas' WHEN 1 THEN 'Tuas' WHEN 2 THEN 'Pasir Panjang'
            WHEN 3 THEN 'Woodlands' WHEN 4 THEN 'Changi' WHEN 5 THEN 'Seletar'
            ELSE 'Jurong East' END AS REGION,
       CASE MOD(SITE_INDEX, 5) WHEN 0 THEN 'Factory Dispatch Dock' WHEN 1 THEN 'Distribution Center'
            WHEN 2 THEN 'Port Terminal' WHEN 3 THEN 'Cross-Dock' ELSE 'Container Yard' END AS CATEGORY,
       SITE_INDEX,
       ROUND(1 + U_AGE * 14, 1) AS AGE_YEARS,
       -- Base daily disruption probability 0.5%-3.5%; ~15% of sites are chronic (x3).
       (0.005 + U_RATE * 0.03) * IFF(U_RATE > 0.85, 3, 1) AS BASE_DISRUPTION_RATE,
       7 * (1 + FLOOR(U_PM * 3)) AS PM_INTERVAL_DAYS,
       0.55 + U_DISCIPLINE * 0.45 AS PM_COMPLETION_PROB,
       ROUND(CASE MOD(SITE_INDEX, 5) WHEN 0 THEN 420 WHEN 1 THEN 680 WHEN 2 THEN 950
                  WHEN 3 THEN 540 ELSE 760 END * (0.8 + U_CAPACITY * 0.4)) AS DAILY_CAPACITY,
       'Active' AS STATUS
FROM draws;

CREATE TABLE RAW.SITE_DAILY AS
WITH days AS (
  SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1 AS DAY_INDEX
  FROM TABLE(GENERATOR(ROWCOUNT => 90))
), regional_events AS (
  -- Two area-wide events in the window.
  SELECT * FROM VALUES (27, 'Pasir Panjang', 'Squall berth suspension', 8.0),
                       (61, 'Woodlands', 'Checkpoint clearance outage', 7.0)
    AS o(DAY_INDEX, REGION, EVENT_CAUSE, HOURS)
), base AS (
  SELECT h.ID AS ENTITY_ID, h.SITE_INDEX, h.CATEGORY, h.REGION, h.AGE_YEARS,
         h.BASE_DISRUPTION_RATE, h.PM_INTERVAL_DAYS, h.PM_COMPLETION_PROB, h.DAILY_CAPACITY,
         d.DAY_INDEX,
         DATEADD('day', d.DAY_INDEX - 89, CURRENT_DATE()) AS EVENT_DATE,
         24.0 AS PLANNED_HOURS,
         MOD(d.DAY_INDEX + h.SITE_INDEX * 3, h.PM_INTERVAL_DAYS) AS DAYS_SINCE_PM,
         MOD(ABS(HASH(h.ID, d.DAY_INDEX, 'sg-mfglog-dis')), 1000000) / 1e6 AS U_DIS,
         MOD(ABS(HASH(h.ID, d.DAY_INDEX, 'sg-mfglog-down')), 1000000) / 1e6 + 1e-6 AS U_DOWN,
         MOD(ABS(HASH(h.ID, d.DAY_INDEX, 'sg-mfglog-cause')), 1000000) / 1e6 AS U_CAUSE,
         MOD(ABS(HASH(h.ID, d.DAY_INDEX, 'sg-mfglog-pmdone')), 1000000) / 1e6 AS U_PMDONE,
         MOD(ABS(HASH(h.ID, d.DAY_INDEX, 'sg-mfglog-volume')), 1000000) / 1e6 AS U_VOLUME,
         MOD(ABS(HASH(h.ID, d.DAY_INDEX, 'sg-mfglog-noise')), 1000000) / 1e6 AS U_NOISE,
         MOD(ABS(HASH(h.ID, d.DAY_INDEX, 'sg-mfglog-hit')), 1000000) / 1e6 AS U_HIT,
         e.EVENT_CAUSE, e.HOURS AS EVENT_HOURS
  FROM RAW.SITES h CROSS JOIN days d
  LEFT JOIN regional_events e ON e.DAY_INDEX = d.DAY_INDEX AND e.REGION = h.REGION
), loaded AS (
  SELECT *,
         IFF(DAYS_SINCE_PM = 0, 1, 0) AS PM_DUE,
         IFF(DAYS_SINCE_PM = 0 AND U_PMDONE < PM_COMPLETION_PROB, 1, 0) AS PM_COMPLETED,
         -- Handling equipment wear rises between PM visits; weak PM discipline carries wear over.
         DAYS_SINCE_PM / PM_INTERVAL_DAYS + (1 - PM_COMPLETION_PROB) AS WEAR,
         -- Backlog stress episode: 8 of every 25 days per site (staggered), e.g. a booking surge.
         IFF(MOD(DAY_INDEX + SITE_INDEX * 7, 25) < 8, 1, 0) AS STRESS,
         -- Volume: weekly low day and a quarter-end shipping peak on day 52 (+55%) easing over 3 days.
         ROUND(DAILY_CAPACITY * (0.68 + 0.27 * U_VOLUME)
               * IFF(MOD(DAY_INDEX, 7) = 6, 0.70, 1.0)
               * CASE DAY_INDEX - 52 WHEN 0 THEN 1.55 WHEN 1 THEN 1.35 WHEN 2 THEN 1.15 ELSE 1.0 END) AS SHIPMENTS
  FROM base
), disruptions AS (
  SELECT *, SHIPMENTS / DAILY_CAPACITY AS LOAD_RATIO,
         LEAST(0.5, BASE_DISRUPTION_RATE * (0.4 + 1.6 * WEAR) * (0.3 + SHIPMENTS / DAILY_CAPACITY)
                    * (1 + AGE_YEARS / 25) * (1 + 2.5 * STRESS)) AS P_DIS
  FROM loaded
), counted AS (
  SELECT *,
         CASE WHEN EVENT_HOURS IS NOT NULL THEN 1
              WHEN U_DIS < P_DIS / 4 THEN 2
              WHEN U_DIS < P_DIS THEN 1
              ELSE 0 END AS DISRUPTION_COUNT
  FROM disruptions
), timed AS (
  SELECT *,
         -- Handling or dispatch downtime: exponential, mean depends on site type.
         CASE WHEN DISRUPTION_COUNT = 0 THEN 0.0
              WHEN EVENT_HOURS IS NOT NULL THEN EVENT_HOURS
              ELSE LEAST(20.0, ROUND(DISRUPTION_COUNT * (0.5 - LN(U_DOWN) *
                   CASE CATEGORY WHEN 'Factory Dispatch Dock' THEN 2.5 WHEN 'Distribution Center' THEN 2.0
                                 WHEN 'Port Terminal' THEN 4.0 WHEN 'Cross-Dock' THEN 1.8 ELSE 3.0 END), 1))
         END AS DOWNTIME_HOURS,
         -- On-time rate (shipments that met the committed delivery window): base by site type,
         -- minus wear and overload, minus the disruption hit.
         LEAST(0.995, GREATEST(0.50,
           CASE CATEGORY WHEN 'Factory Dispatch Dock' THEN 0.950 WHEN 'Distribution Center' THEN 0.945
                         WHEN 'Port Terminal' THEN 0.915 WHEN 'Cross-Dock' THEN 0.955 ELSE 0.930 END
           - 0.03 * WEAR - 0.05 * GREATEST(0, LOAD_RATIO - 0.9) - 0.008 * U_NOISE
           - DISRUPTION_COUNT * (0.07 + 0.13 * U_HIT))) AS ON_TIME_RATE
  FROM counted
)
SELECT ENTITY_ID || '-' || TO_CHAR(EVENT_DATE, 'YYYYMMDD') AS EVENT_ID,
       ENTITY_ID, EVENT_DATE, PLANNED_HOURS, DOWNTIME_HOURS,
       PLANNED_HOURS - DOWNTIME_HOURS AS OPERATING_HOURS,
       DISRUPTION_COUNT,
       CASE WHEN DISRUPTION_COUNT = 0 THEN 'None'
            WHEN EVENT_CAUSE IS NOT NULL THEN EVENT_CAUSE
            WHEN CATEGORY = 'Factory Dispatch Dock' THEN IFF(U_CAUSE < 0.45, 'Forklift breakdown', IFF(U_CAUSE < 0.75, 'Late production release', 'Pick list error'))
            WHEN CATEGORY = 'Distribution Center' THEN IFF(U_CAUSE < 0.5, 'Conveyor fault', IFF(U_CAUSE < 0.8, 'Labour shortfall', 'WMS sync failure'))
            WHEN CATEGORY = 'Port Terminal' THEN IFF(U_CAUSE < 0.55, 'Vessel berth delay', 'Quay crane outage')
            WHEN CATEGORY = 'Cross-Dock' THEN IFF(U_CAUSE < 0.6, 'Trailer no-show', 'Dock door fault')
            ELSE IFF(U_CAUSE < 0.55, 'Reach stacker breakdown', 'Container documentation hold') END AS ROOT_CAUSE,
       PM_DUE, PM_COMPLETED,
       SHIPMENTS,
       FLOOR(SHIPMENTS * ON_TIME_RATE) AS ON_TIME_SHIPMENTS,
       ROUND(SHIPMENTS * (2.2 + U_VOLUME * 1.2)) AS HANDLING_MOVES,
       ROUND(SHIPMENTS * (2.2 + U_VOLUME * 1.2) * (0.008 + 0.009 * WEAR + 0.022 * DISRUPTION_COUNT + 0.005 * U_NOISE)) AS EXCEPTION_MOVES,
       ROUND(5.0 + 3.0 * WEAR + 4.0 * GREATEST(0, LOAD_RATIO - 0.8) + 2.2 * STRESS + 4.5 * DISRUPTION_COUNT + U_NOISE * 1.1, 2) AS DWELL_HOURS,
       ROUND(LEAST(100, 100 * LOAD_RATIO * (0.84 + 0.11 * U_NOISE) + 6 * STRESS + 5 * DISRUPTION_COUNT), 1) AS EQUIPMENT_LOAD_PCT,
       ROUND(88.0 + 10.5 * ON_TIME_RATE + 1.2 * U_NOISE, 1) AS ORDER_FILL_PCT,
       CURRENT_TIMESTAMP() AS LOADED_AT
FROM timed;

-- Handling equipment readiness per site (snapshot): units required versus on hand.
CREATE TABLE RAW.EQUIPMENT_READINESS AS
SELECT ID AS ENTITY_ID,
       CASE CATEGORY WHEN 'Factory Dispatch Dock' THEN 'Forklift' WHEN 'Distribution Center' THEN 'Reach truck'
                     WHEN 'Port Terminal' THEN 'Quay crane' WHEN 'Cross-Dock' THEN 'Dock door'
                     ELSE 'Reach stacker' END AS EQUIPMENT_TYPE,
       8 + MOD(ABS(HASH(ID, 'sg-mfglog-req')), 27) AS REQUIRED_QTY,
       FLOOR((8 + MOD(ABS(HASH(ID, 'sg-mfglog-req')), 27)) * (0.72 + MOD(ABS(HASH(ID, 'sg-mfglog-avail')), 1000) / 1000 * 0.33)) AS ON_HAND_QTY,
       MOD(ABS(HASH(ID, 'sg-mfglog-order')), 4) AS ON_ORDER_QTY,
       CURRENT_DATE() AS SNAPSHOT_DATE
FROM RAW.SITES;
