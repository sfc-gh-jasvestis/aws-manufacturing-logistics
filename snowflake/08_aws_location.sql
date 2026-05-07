-- ============================================================================
-- 08_aws_location.sql
-- AWS hero: Amazon Location Service + EventBridge + SNS
-- ----------------------------------------------------------------------------
-- Adds:
--   * DIM_VESSEL_TRACK: synthetic AIS-style vessel positions for the Live Map
--   * VW_VESSEL_LIVE: latest position per vessel for st.map / Plotly mapbox
--   * SP_RAISE_STUCK_ALERT: returns the EventBridge PutEvents payload that
--     would be posted to bus `mfg-supply-chain-bus`, fanning out to
--     SNS topic arn:aws:sns:us-west-2:__AWS_ACCOUNT_ID__:mfg-stuck-alerts
-- ============================================================================
USE DATABASE MANUFACTURING_SUPPLY_CHAIN;
USE SCHEMA CURATED;

CREATE OR REPLACE TABLE DIM_VESSEL_TRACK (
    VESSEL_ID         STRING,
    VESSEL_NAME       STRING,
    CARRIER_NAME      STRING,
    LAT               FLOAT,
    LON               FLOAT,
    HEADING_DEG       NUMBER,
    SPEED_KTS         FLOAT,
    DESTINATION_PORT  STRING,
    ETA               TIMESTAMP_NTZ,
    STATUS            STRING,
    CAPTURED_AT       TIMESTAMP_NTZ
);

INSERT INTO DIM_VESSEL_TRACK VALUES
    ('IMO9811000','MV Pacific Pioneer','Pacific Express Lines',1.27,103.85,90,0.2,'Singapore PSA',DATEADD('hour', 24, CURRENT_TIMESTAMP()),'STUCK',CURRENT_TIMESTAMP()),
    ('IMO9811001','MV Pacific Voyager','Pacific Express Lines',1.30,103.83,180,0.0,'Singapore PSA',DATEADD('hour', 18, CURRENT_TIMESTAMP()),'STUCK',CURRENT_TIMESTAMP()),
    ('IMO9811002','MV Pacific Star',   'Pacific Express Lines',1.25,103.87,270,0.5,'Singapore PSA',DATEADD('hour', 22, CURRENT_TIMESTAMP()),'STUCK',CURRENT_TIMESTAMP()),
    ('IMO9811003','MV Maersk Sentinel','Maersk Line',         30.63,122.07,180,12.4,'Shanghai Yangshan',DATEADD('hour', 36, CURRENT_TIMESTAMP()),'IN_TRANSIT',CURRENT_TIMESTAMP()),
    ('IMO9811004','MV CMA Vega',       'CMA CGM',             35.075,128.88,135,14.1,'Busan New Port',DATEADD('hour', 28, CURRENT_TIMESTAMP()),'IN_TRANSIT',CURRENT_TIMESTAMP()),
    ('IMO9811005','MV Hapag Wave',     'Hapag-Lloyd',         51.95,4.13,90,11.8,'Rotterdam Europoort',DATEADD('hour', 48, CURRENT_TIMESTAMP()),'IN_TRANSIT',CURRENT_TIMESTAMP()),
    ('IMO9811006','MV Evergreen Crest','Evergreen Marine',    22.57,114.28,225,13.0,'Shenzhen Yantian',DATEADD('hour', 12, CURRENT_TIMESTAMP()),'IN_TRANSIT',CURRENT_TIMESTAMP()),
    ('IMO9811007','MV ONE Tide',       'ONE',                 35.44,139.65,45,10.2,'Yokohama',DATEADD('hour', 30, CURRENT_TIMESTAMP()),'IN_TRANSIT',CURRENT_TIMESTAMP()),
    ('IMO9811008','MV COSCO Galaxy',   'COSCO Shipping',      31.23,121.47,200,9.9,'Shanghai Yangshan',DATEADD('hour', 8,  CURRENT_TIMESTAMP()),'IN_TRANSIT',CURRENT_TIMESTAMP()),
    ('IMO9811009','MV Yang Ming Pulse','Yang Ming',           24.93,118.62,160,11.5,'Shenzhen Yantian',DATEADD('hour', 16, CURRENT_TIMESTAMP()),'IN_TRANSIT',CURRENT_TIMESTAMP());

CREATE OR REPLACE VIEW CURATED.VW_VESSEL_LIVE AS
SELECT VESSEL_ID, VESSEL_NAME, CARRIER_NAME, LAT, LON, HEADING_DEG, SPEED_KTS,
       DESTINATION_PORT, ETA, STATUS, CAPTURED_AT
FROM DIM_VESSEL_TRACK;

-- ----------------------------------------------------------------------------
-- SP_RAISE_STUCK_ALERT
-- Returns the EventBridge PutEvents JSON we would post for a STUCK shipment.
-- Real wiring: aws events put-events --entries file://payload.json
-- Bus:       mfg-supply-chain-bus
-- Rule:      mfg-stuck-shipment-rule  (filter detail-type = 'StuckShipment')
-- Target:    arn:aws:sns:us-west-2:__AWS_ACCOUNT_ID__:mfg-stuck-alerts
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE AI.SP_RAISE_STUCK_ALERT(SHIPMENT_ID STRING)
RETURNS VARIANT
LANGUAGE SQL
AS
$$
DECLARE
    rec     VARIANT;
    payload VARIANT;
BEGIN
    SELECT OBJECT_CONSTRUCT(
        'shipment_id', SHIPMENT_ID,
        'carrier',     CARRIER_NAME,
        'origin',      ORIGIN_PORT_NAME,
        'destination', DEST_PORT_NAME,
        'value_usd',   VALUE_USD,
        'days_delayed',DAYS_DELAYED,
        'commodity',   COMMODITY_TYPE
    ) INTO :rec
    FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.SHIPMENT_STATUS
    WHERE SHIPMENT_ID = :SHIPMENT_ID
    LIMIT 1;

    payload := OBJECT_CONSTRUCT(
        'Entries', ARRAY_CONSTRUCT(OBJECT_CONSTRUCT(
            'Source',       'snowflake.supply_chain',
            'DetailType',   'StuckShipment',
            'EventBusName', 'mfg-supply-chain-bus',
            'Time',         CURRENT_TIMESTAMP()::STRING,
            'Detail',       :rec::STRING,
            'Resources', ARRAY_CONSTRUCT(
                'arn:aws:sns:us-west-2:__AWS_ACCOUNT_ID__:mfg-stuck-alerts',
                'arn:aws:geo:us-west-2:__AWS_ACCOUNT_ID__:tracker/mfg-vessels'
            )
        ))
    );
    RETURN payload;
END;
$$;
