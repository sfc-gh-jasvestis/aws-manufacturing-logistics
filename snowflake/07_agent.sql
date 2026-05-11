-- Supply Chain Command Center: Cortex Agent
USE SCHEMA MANUFACTURING_SUPPLY_CHAIN.AI;

CREATE OR REPLACE AGENT SUPPLY_CHAIN_COMMAND_AGENT
    COMMENT = 'Supply Chain Command Center Agent for logistics analytics and policy search'
    PROFILE = '{"display_name": "Supply Chain Command Center", "color": "blue"}'
    FROM SPECIFICATION
    $$
    models:
      orchestration: auto

    orchestration:
      budget:
        seconds: 30
        tokens: 16000

    instructions:
      response: "You are a supply chain operations expert. Provide concise, actionable insights about shipments, carriers, port congestion, and logistics policies. When reporting delays or issues, quantify the impact in terms of value at risk and days delayed."
      orchestration: "For data questions about shipments, carriers, ports, delays, or performance metrics, use SupplyChainAnalyst. For questions about policies, contracts, routing guides, safety procedures, or compliance, use LogisticsSearch."
      system: "You are the Supply Chain Command Center AI assistant. You help logistics managers monitor shipment status, identify bottlenecks, assess carrier performance, and find relevant policies."
      sample_questions:
        - question: "What shipments are currently stuck?"
          answer: "I'll check the shipment data for stuck shipments and their impact."
        - question: "Which carriers have the worst on-time performance?"
          answer: "I'll look up the carrier performance metrics."
        - question: "What is our policy for port congestion?"
          answer: "I'll search the logistics documentation for port congestion policies."

    tools:
      - tool_spec:
          type: "cortex_analyst_text_to_sql"
          name: "SupplyChainAnalyst"
          description: "Analyzes structured supply chain data including shipment status, carrier performance, port congestion, delays, value at risk, and container metrics. Use for any quantitative questions about operations data."
      - tool_spec:
          type: "cortex_search"
          name: "LogisticsSearch"
          description: "Searches logistics documentation including shipping policies, carrier contracts, routing guides, safety procedures, and compliance standards. Use for questions about rules, procedures, contracts, or best practices."
      - tool_spec:
          type: "data_to_chart"
          name: "data_to_chart"
          description: "Generates visualizations from query results to display charts and graphs."

    tool_resources:
      SupplyChainAnalyst:
        semantic_view: "MANUFACTURING_SUPPLY_CHAIN.AI.SUPPLY_CHAIN_SEMANTIC_VIEW"
      LogisticsSearch:
        name: "MANUFACTURING_SUPPLY_CHAIN.SEARCH.LOGISTICS_SEARCH"
        max_results: "5"
        title_column: "TITLE"
        id_column: "DOC_ID"
    $$;
