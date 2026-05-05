-- Supply Chain Command Center: Semantic View
USE SCHEMA MANUFACTURING_SUPPLY_CHAIN.AI;

CREATE OR REPLACE SEMANTIC VIEW SUPPLY_CHAIN_SEMANTIC_VIEW
    COMMENT = 'Supply chain analytics: shipments, carriers, ports'
AS
    TABLES (
        CURATED.SHIPMENT_STATUS AS shipments
            COLUMNS (
                SHIPMENT_ID AS shipment_id COMMENT 'Unique shipment identifier',
                STATUS AS status COMMENT 'Current status: IN_TRANSIT, DELIVERED, STUCK, DELAYED',
                DELAY_HOURS AS delay_hours COMMENT 'Hours delayed beyond expected arrival',
                CARGO_VALUE AS cargo_value COMMENT 'Value of cargo in USD',
                COMMODITY_TYPE AS commodity_type COMMENT 'Type of goods shipped',
                CARRIER_NAME AS carrier_name COMMENT 'Name of shipping carrier',
                ORIGIN_PORT AS origin_port COMMENT 'Port of origin',
                DESTINATION_PORT AS destination_port COMMENT 'Destination port',
                IMPACT_SCORE AS impact_level COMMENT 'Delay severity: CRITICAL, HIGH, MEDIUM, ON_TIME'
            ),
        CURATED.CARRIER_PERFORMANCE AS carriers
            COLUMNS (
                CARRIER_NAME AS carrier_name COMMENT 'Carrier company name',
                ON_TIME_RATE AS on_time_rate COMMENT 'Percentage of shipments delivered on time',
                TOTAL_SHIPMENTS AS total_shipments COMMENT 'Total number of shipments handled',
                DELAYED_SHIPMENTS AS delayed_count COMMENT 'Number of delayed shipments',
                STUCK_SHIPMENTS AS stuck_count COMMENT 'Number of stuck shipments',
                AVG_DELAY_HOURS AS avg_delay COMMENT 'Average delay in hours'
            ),
        CURATED.PORT_CONGESTION AS ports
            COLUMNS (
                PORT_NAME AS port_name COMMENT 'Name of the port',
                COUNTRY AS country COMMENT 'Country where port is located',
                CURRENT_UTILIZATION AS utilization_pct COMMENT 'Current capacity utilization percentage',
                CONGESTION_LEVEL AS congestion_level COMMENT 'CRITICAL, HIGH, MEDIUM, LOW',
                STUCK_CONTAINERS AS stuck_containers COMMENT 'Number of containers stuck at port',
                DELAYED_SHIPMENTS AS port_delayed_shipments COMMENT 'Number of delayed shipments at port'
            )
    );
