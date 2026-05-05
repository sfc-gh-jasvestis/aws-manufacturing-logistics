-- Supply Chain Command Center: Cortex Search
USE SCHEMA MANUFACTURING_SUPPLY_CHAIN.SEARCH;

CREATE OR REPLACE CORTEX SEARCH SERVICE LOGISTICS_SEARCH
    ON (
        SELECT
            DOC_ID,
            TITLE,
            CATEGORY,
            CONTENT
        FROM RAW.SUPPLY_CHAIN_DOCS
    )
    WAREHOUSE = CORTEX
    TARGET_LAG = '1 hour'
    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
    AS (
        SEARCH_COLUMN => 'CONTENT',
        COLUMNS => ['DOC_ID', 'TITLE', 'CATEGORY', 'CONTENT']
    );
