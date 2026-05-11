# Demo Script: Supply Chain Command Center
## ~3:00 Recorded Walkthrough
**Format**: Screen recording with voiceover
**Target**: Customer meeting / booth loop / social share
**Pre-requisites**: Data loaded, Streamlit deployed, QuickSight dashboard published

---

## Two Personas

| Persona | Role | Tool | What they care about |
|---|---|---|---|
| **Logistics Operator** | Day-to-day shipment control | Streamlit in Snowflake | Stuck containers, carrier scorecards, downstream delay propagation |
| **VP Supply Chain** | Executive oversight | Amazon QuickSight + Amazon Q | Network on-time %, value-at-risk, alert fan-out timing, carrier mix |

---

## What's Built

| Layer | Component | Detail |
|---|---|---|
| **Ingest (AWS)** | Amazon S3 | `s3://sg-manufacturing-demos-2026/supply-chain/` — logistics docs + AIS feeds |
| **RAW** | 5 tables | CARRIERS (30), PORTS (20), WAREHOUSES (15), SHIPMENTS (50K), LOGISTICS_DOCS (100) |
| **CURATED** | 3 Dynamic Tables + 1 view | SHIPMENT_STATUS, CARRIER_PERFORMANCE, PORT_CONGESTION, VW_VESSEL_LIVE (10 vessels) |
| **AI** | Cortex Search + Semantic View + Agent | LOGISTICS_SEARCH (100 contracts), SUPPLY_CHAIN_SEMANTIC_VIEW |
| **ML** | FORECAST + ANOMALY | Carrier on-time forecasting + delay anomaly detection |
| **Consumption** | Streamlit | 6-page Supply Chain Command Center |
| | QuickSight | `mfg-supply-chain-dashboard` + Amazon Q topic `mfg-supply-chain-q` |

---

## Pre-Recording Checklist

- [ ] `SELECT COUNT(*) FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.SHIPMENT_STATUS WHERE STATUS='STUCK'` returns 3
- [ ] `SELECT COUNT(*) FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.SHIPMENT_STATUS WHERE STATUS='DELAYED'` returns 12
- [ ] `SELECT * FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.VW_VESSEL_LIVE WHERE STATUS='STUCK'` returns 3 Pacific Express Lines vessels
- [ ] Regional Container Lines on-time % ≈ 14.7 in `CARRIER_PERFORMANCE` (worst carrier)
- [ ] 5 CRITICAL ports, Antwerp-Bruges at 97.3% in `PORT_CONGESTION`
- [ ] Open Streamlit: https://app.snowflake.com/YOUR_ORG/sg_<YOUR_CONNECTION>/#/streamlit-apps/MANUFACTURING_SUPPLY_CHAIN.APP.SUPPLY_CHAIN_COMMAND_CENTER
- [ ] Open QuickSight: https://us-west-2.quicksight.aws.amazon.com/sn/dashboards/mfg-supply-chain-dashboard
- [ ] Audio: quiet room, external mic
- [ ] Resolution: 1920x1080

---

## Script

### [0:00–0:25] PAGE 1: OVERVIEW

**Show**: Streamlit Overview page — KPI strip, incident banner, status bar chart, commodity bar

**Tech**: Dynamic Tables (5-min refresh)

> "Fifty thousand shipments, forty billion dollars of cargo moving across 30 carriers and 20 ports. The incident banner fires immediately — three shipments stuck at Singapore PSA, twelve downstream delays already triggered, seven point four million dollars in impact accumulating right now. Three ships. That's all it takes to start a cascade. The status chart — forty-six thousand delivered, three thousand in transit, and those fifteen problem shipments flagged in red and orange. The commodity bar — pharmaceuticals at six point four billion is the highest value exposure, then electronics at six billion. One Dynamic Table refreshing every five minutes — no ETL, no scheduled jobs. This incident was caught in under five minutes."

### [0:25–0:55] PAGE 2: PORT CONGESTION

**Show**: Port Congestion page — Antwerp-Bruges at 97%, 5 Critical, 11 High Risk (combined), 1,018 stuck containers. Scroll to Port Details table.

**Tech**: Dynamic Tables

> "Five ports in CRITICAL status — all red on the chart. Antwerp-Bruges leads at ninety-seven percent utilization with 106 stuck containers. Singapore PSA at ninety-four percent. Jebel Ali, Hamburg, Ningbo — all above ninety. Eleven ports classified high risk or worse. Over a thousand containers stuck across the network. The color bands tell you severity at a glance — red is critical, orange is high risk, green is healthy. Scroll down — the details table gives you every port: utilization, containers at port, stuck count, average dwell hours, congestion level. All twenty ports, one Dynamic Table, updated every five minutes. This is why three stuck ships at Singapore become a network-wide problem."

### [0:50–1:15] PAGE 3: CARRIER PERFORMANCE

**Show**: Carrier Performance page — Regional Container Lines at 14.7%, 30 carriers ranked, 85% target line

**Tech**: Dynamic Tables + correlated metrics

> "Thirty carriers ranked by on-time percentage. The dashed line is the target: eighty-five percent. Regional Container Lines at the bottom — fourteen point seven percent on-time across 716 shipments. SM Line next at twenty-two percent. Twenty-one carriers below the eighty-five percent target — that's seventy percent of your carrier base underperforming. The same Dynamic Table scoring each carrier updates every five minutes. When a carrier like Pacific Express Lines triggers the Singapore incident, this scorecard immediately reflects it. That's the data you need to renegotiate a contract or terminate one."

### [1:15–1:40] PAGE 4: STUCK SHIPMENTS — the cascade

**Show**: Stuck Shipments page — "3 STUCK shipments — total value 3.1M, total impact 4.7M" banner, table showing SHP-006851/52/53 all Pacific Express Lines originating Singapore PSA, heading to Hong Kong, Shenzhen, Guangzhou. Scroll to "Downstream Delayed" section — 12 shipments delayed by Singapore congestion, heading to Shanghai, Ningbo, Busan, and beyond.

**Tech**: Dynamic Tables + incident correlation

> "Here's the cascade in detail. Three stuck shipments — all Pacific Express Lines, all originating Singapore PSA. Three point one million in value, four point seven million in impact. SHP-006851 heading to Hong Kong with eight containers of electronics. 006852 to Shenzhen. 006853 to Guangzhou with automotive parts. Scroll down — twelve downstream delays. And look at the carrier column — Pacific Express Lines again. They're not just stuck at Singapore, they're the carrier for the downstream shipments too. Busan, Yokohama, Colombo — all waiting. One carrier, one port, network-wide impact. This is why you need correlated data — the stuck ships AND the delayed ships are the same carrier's problem. One Dynamic Table connecting the dots."

### [1:40–1:55] PAGE 5: LIVE MAP

**Show**: Live Vessel Map page — KPIs (10 tracked, 3 stuck, 7 in transit), stuck alert banner, vessel table

**Tech**: Snowflake vessel tracking view (VW_VESSEL_LIVE)

> "Ten vessels tracked in real time. Three are stuck at Singapore PSA — all Pacific Express Lines, loitering over six hours. The same three ships from the Stuck Shipments page, now on the map. Seven in transit heading to Shanghai, Busan, Rotterdam, Shenzhen. The vessel table gives you carrier, heading, speed, destination, status — all from one Snowflake view refreshing with the Dynamic Tables."

### [1:55–2:10] PAGE 6: LOGISTICS SEARCH

**Show**: Logistics Policy Search page — Cortex Search interface

**Tech**: Cortex Search over 100 contracts

> "Back in Snowflake — Cortex Search across 100 shipping contracts and logistics policies. Type demurrage charges and the right clause surfaces in under a second. No vector database to operate — Snowflake manages the index, the embeddings, and the retrieval."

### [2:10–2:30] PAGE 7: ASK SUPPLY CHAIN — Cortex Analyst

**Show**: Ask Supply Chain page — type: "which destinations have stuck or delayed shipments from Singapore and what's the value in USD?"

**Tech**: Cortex Analyst (Semantic View — 11 dims, 9 metrics)

> "Now the power move. Natural language question: which destinations have stuck or delayed shipments from Singapore and what's the value in USD? Cortex Analyst generates the SQL, queries the same governed data, returns the answer — twelve destination ports, total value exposure. Hong Kong, Shenzhen, Guangzhou — all downstream of Singapore. Same question, same data. Watch."

### [2:30–3:00] QUICKSIGHT + AMAZON Q — the executive lens

**Show**: QuickSight dashboard — KPIs (4), Top 10 Carriers bar, Value by Origin Port bar, Shipments by Destination Port bar, Status donut. Scroll through visuals to show the audience the same data. Point out Singapore as top origin port, stuck/delayed status colors. Then click the **Q icon inside the dashboard** and ask: "which destinations have stuck or delayed shipments from Singapore and what's the value in USD?"

**Tech**: QuickSight Snowflake direct query + Amazon Q (dashboard context sees port columns via visuals)

> "Same governed data, executive view. QuickSight live-queries Snowflake — same fifty thousand shipments, same three stuck, same twelve delayed. Singapore at the top of the origin port chart. Destination ports — Hong Kong, Shenzhen, Guangzhou — all waiting on Singapore. Now — Amazon Q, same question: which destinations have stuck or delayed shipments from Singapore and what's the value in USD? Same answer. Two AI assistants, one governed truth. Cortex for the operator, Q for the VP — same numbers, one data layer. Three ships. Five minutes to detect. That's the Supply Chain Command Center."

---

## Key Demo Differentiators

1. **Early detection narrative** — "3 ships → 12 downstream delays → 5 critical ports → $7.4M impact" is a real supply chain cascade story, not synthetic drama.
2. **Cascading impact view** — port congestion directly correlates to stuck containers in one view.
3. **Dynamic Tables** — zero-ETL operational layer refreshing every 5 minutes, catching incidents before they cascade.
4. **Cortex Search** — unstructured document retrieval without external vector DB.
5. **Cortex Analyst + QuickSight Q** — two AI assistants, same governed data, same answer.
