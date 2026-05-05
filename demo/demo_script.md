# Supply Chain Command Center — Demo Script

## Story

You're Sarah Chen, Global Logistics Director at a major manufacturer. Your morning begins with an alert: containers are stuck at Singapore. Within 3.5 minutes, you'll discover the disruption, trace its cascading impact across 12 downstream shipments, identify the underperforming carrier, and get an AI-recommended rerouting strategy.

## Personas

| Persona | Title | Goal |
|---------|-------|------|
| **Sarah Chen** | Global Logistics Director | Real-time disruption response, carrier accountability |
| **James Park** | VP Supply Chain | Portfolio-level visibility, strategic carrier decisions |

## What's Built

| Layer | Object | Purpose |
|-------|--------|---------|
| Data | 50K shipments, 100K containers, 30 carriers, 20 ports | Global logistics network |
| Dynamic Tables | SHIPMENT_STATUS, CARRIER_PERFORMANCE, PORT_CONGESTION | Real-time curated views |
| ML | Transit Time Forecast, Delay Anomaly Detection | Predictive intelligence |
| Search | LOGISTICS_SEARCH (100 docs) | Procedure & policy retrieval |
| Semantic View | SUPPLY_CHAIN_SEMANTIC_VIEW | Natural language analytics |
| Agent | SUPPLY_CHAIN_COMMAND_AGENT | Conversational AI assistant |
| Streamlit | SUPPLY_CHAIN_COMMAND_CENTER | Executive dashboard |

## Narrative Arc

```
ALERT → DISCOVER → TRACE → DIAGNOSE → RECOMMEND → RESOLVE
  │         │         │         │           │          │
  ▼         ▼         ▼         ▼           ▼          ▼
Stuck    Singapore  12 ships   Pacific     Reroute   Work
containers  94%     delayed   Express 62%  via alt   order
  (3)     util.              on-time      port     created
```

## Timed Script (3.5 minutes)

### Opening — Dashboard Overview (0:00–0:20)
- Open Streamlit app — SUPPLY_CHAIN_COMMAND_CENTER
- "I'm Sarah Chen, running global logistics for our manufacturing network"
- Show KPI cards: 50K shipments | 3 stuck | 12 delayed | 62% worst carrier
- **Key visual:** Red alert banner on Singapore congestion

### Beat 1 — Discover the Disruption (0:20–0:45)
- Click into Port Congestion view
- "Singapore PSA is at 94% utilization — that's critical"
- Show 3 containers stuck, carrier Pacific Express Lines
- "These containers hold components for our Electronics line"
- **Number:** 94% utilization, 3 stuck containers

### Beat 2 — Trace Cascading Impact (0:45–1:15)
- Navigate to Shipment Status tab
- Filter: STATUS = 'DELAYED', ORIGIN = 'Singapore'
- "12 downstream shipments are now delayed because of this bottleneck"
- Show delay hours ranging from 24 to 96
- **Number:** 12 delayed shipments, up to 96 hours delay

### Beat 3 — Diagnose the Carrier (1:15–1:50)
- Switch to Carrier Performance view
- "Pacific Express Lines — 62% on-time rate. That's our worst performer"
- Compare against fleet average (~87%)
- "This is a pattern, not an incident. 3 stuck shipments from the same carrier"
- **Number:** 62% on-time vs 87% fleet average

### Beat 4 — Ask the AI Agent (1:50–2:30)
- Open AI Assistant tab
- Type: "What are my options for the 3 stuck containers at Singapore?"
- Agent responds with: reroute via Port Klang (78% util), negotiate expedited customs, escalate to Pacific Express management
- "The agent is cross-referencing our logistics docs and real-time data"
- **Key moment:** AI provides actionable 3-option recommendation

### Beat 5 — Search Logistics Procedures (2:30–3:00)
- Type: "What's our SLA with Pacific Express Lines?"
- Cortex Search retrieves contract terms
- "We're within rights to invoke the penalty clause — 3 consecutive misses"
- Show relevant document snippet
- **Number:** SLA threshold: 85% on-time required

### Closing — Strategic Decision (3:00–3:30)
- Return to dashboard overview
- "In under 4 minutes, I went from alert to action plan"
- "Reroute the 3 containers, flag Pacific Express for contract review"
- "This is the power of having your entire supply chain in one intelligent platform"
- **Tagline:** "From disruption to decision in minutes, not days"

## Pre-Recording Checklist

- [ ] Streamlit app loaded and responsive
- [ ] Singapore showing 94% utilization, 3 STUCK
- [ ] Pacific Express Lines at 62% visible in carrier table
- [ ] 12 DELAYED shipments filterable
- [ ] Agent responding with reroute recommendations
- [ ] Search returning SLA documents
- [ ] All KPI cards rendering correctly
- [ ] Warehouse CORTEX is STARTED

## Key Questions to Anticipate

1. **"How fresh is this data?"** — Dynamic Tables refresh every 60 seconds from S3 stage
2. **"Can this handle more shipments?"** — Architecture scales to millions; Snowflake elastic compute
3. **"How does the AI know about our procedures?"** — Cortex Search indexes 100 logistics documents; agent retrieves relevant context
4. **"What about multi-modal carriers?"** — Data model supports air, sea, rail, road — just add carrier records
5. **"Is this real-time?"** — Near real-time: 1-minute target lag on Dynamic Tables, streaming ingest possible via Snowpipe
