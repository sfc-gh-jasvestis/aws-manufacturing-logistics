-- Supply Chain Command Center: Cortex Agent
USE SCHEMA MANUFACTURING_SUPPLY_CHAIN.AI;

CREATE OR REPLACE CORTEX AGENT SUPPLY_CHAIN_COMMAND_AGENT
    COMMENT = 'AI assistant for supply chain visibility and recommendations'
    MODEL = 'claude-3-5-sonnet'
    TOOLS = (
        'MANUFACTURING_SUPPLY_CHAIN.AI.SUPPLY_CHAIN_SEMANTIC_VIEW' AS SupplyChainAnalyst,
        'MANUFACTURING_SUPPLY_CHAIN.SEARCH.LOGISTICS_SEARCH' AS LogisticsSearch,
        'snowflake.cortex.data_to_chart' AS ChartGenerator
    )
    SYSTEM_PROMPT = 'You are a supply chain intelligence assistant. Help logistics professionals identify disruptions, analyze carrier performance, and recommend rerouting strategies. Always provide specific numbers and actionable recommendations.';
