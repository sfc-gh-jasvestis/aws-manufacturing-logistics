# Demo Script: Supply Chain Command Center
## ~3-Minute Recorded Walkthrough
**Format**: Screen recording with voiceover
**Target**: Customer meeting / booth loop / social share
**Pre-requisites**: Data loaded, Streamlit deployed, QuickSight dashboard published, AWS Location Service tracker `mfg-vessels` provisioned

---

## Two Personas

| Persona | Role | Tool | What they care about |
|---|---|---|---|
| **Logistics Operator** | Day-to-day shipment control | Streamlit in Snowflake + Live Map (AWS Location) | Stuck containers, geofence breaches, carrier scorecards, downstream delay propagation |
| **VP Supply Chain** | Executive oversight | Amazon QuickSight + Amazon Q | Network on-time %, value-at-risk, alert fan-out timing, carrier mix |

---

## What's Built

| Layer | Component | Detail |
|---|---|---|
| **Ingest (AWS)** | Amazon S3 | `s3://sg-manufacturing-demos-2026/supply-chain/` — logistics docs + AIS feeds |
| **RAW** | 5 tables | CARRIERS (30), PORTS (20), WAREHOUSES (15), SHIPMENTS (50K), LOGISTICS_DOCS (100) |
| **CURATED** | 3 Dynamic Tables + 1 dim | SHIPMENT_STATUS, CARRIER_PERFORMANCE, PORT_CONGESTION, DIM_VESSEL_TRACK (10 vessels) |
| **AI** | Cortex Search + Semantic View + Agent | LOGISTICS_SEARCH (100 contracts), SUPPLY_CHAIN_SEMANTIC_VIEW |
| **ML** | FORECAST + ANOMALY | Carrier on-time forecasting + delay anomaly detection |
| **AWS Hero** | Location Service + EventBridge + SNS | Tracker `mfg-vessels`, geofence `singapore-psa-approach`, bus `mfg-supply-chain-bus`, topic `mfg-stuck-alerts` |
| **Consumption** | Streamlit | 8-page Supply Chain Command Center |
| | QuickSight | `mfg-supply-chain-dashboard` + Amazon Q topic `mfg-supply-chain-q` |

---

## Script

### [0:00–0:20] THE PROBLEM & ARCHITECTURE

**Show**: Streamlit Overview page, red incident banner

> "Three Pacific Express vessels stuck in the Singapore PSA approach. Twelve downstream shipments delayed. Three million dollars in goods sitting at anchor — and no one in your operations room saw it coming. This is exactly the kind of incident **Snowflake plus AWS** is built to catch in real time. Logistics docs and AIS feeds land in **Amazon S3**. Snowflake builds a curated layer with **Dynamic Tables** refreshing every 5 minutes. Vessel positions also publish to **AWS Location Service** with a geofence around the port. The moment a shipment turns STUCK, **EventBridge** fires and **SNS** fans the alert to mobile, Slack, and email — all in one rule. Let me show you."

### [0:20–0:45] PAGE 1: OVERVIEW

**Show**: KPI strip — 3 STUCK, 12 DELAYED, $3M at risk

**Tech**: Dynamic Tables (5-min refresh)

> "Six KPIs across 30 carriers, 20 ports, 50,000 shipments. Three STUCK, twelve DELAYED, three million at risk. No ETL job built this — it's one **Dynamic Table** refreshing every five minutes. The status pie tells you 0.6% of the network is on fire; the commodity bar tells you the most exposed value is electronics."

### [0:45–1:10] PAGE 2: STUCK SHIPMENTS

**Show**: Stuck table (3 rows) + Downstream Delayed (12 rows from Singapore PSA)

**Tech**: Dynamic Tables + correlated subquery

> "Three stuck containers — all Pacific Express, all Singapore PSA. And right under it, twelve shipments delayed *because of* Singapore congestion. The same Dynamic Table that flags the stuck shipment shows you the propagation. That's the cascading impact most ERPs hide."

### [1:10–1:35] PAGE 3: LIVE MAP — AWS Location Service

**Show**: Click `Live Map (AWS Location)` page, zoom to Singapore

**Tech**: AWS Location Service tracker + Plotly mapbox

> "Same data — different lens. Three red pins inside the Singapore approach geofence. Ten vessels total, color-coded by status. The lat/lon you see in Snowflake is the *same* lat/lon publishing to **AWS Location Service** tracker `mfg-vessels`. Geofence `singapore-psa-approach` flags any vessel that loiters more than six hours. That's how the alert gets started — not by a human, by AWS."

### [1:35–2:00] EVENTBRIDGE + SNS — the AWS payoff

**Show**: Pick stuck shipment, click **Raise alert**, expand JSON output

**Tech**: Stored proc returns EventBridge `PutEvents` payload

> "Click *Raise alert*. Snowflake's stored proc bundles the shipment context — carrier, route, value, days delayed — and returns the **EventBridge** `PutEvents` payload that bus `mfg-supply-chain-bus` would receive. Rule `mfg-stuck-shipment-rule` fans this to **SNS** topic `mfg-stuck-alerts` — mobile push for the on-call operator, Slack channel for the carrier desk, email for the regional VP. One alert, three audiences, sub-second."

**Action**: Switch to AWS Location Service console — show tracker `mfg-vessels` with the three pins; switch to EventBridge — show rule `mfg-stuck-shipment-rule` with target `mfg-stuck-alerts`.

### [2:00–2:25] PAGE 4: ASK THE DATA + LOGISTICS SEARCH

**Show**: Type "Which carrier has the most delayed shipments?" — confirm answer = Pacific Express

**Tech**: Cortex Analyst + Semantic View

> "Natural language. **Cortex Analyst** over `SUPPLY_CHAIN_SEMANTIC_VIEW` translates plain English to SQL — Pacific Express Lines, 1,000 shipments, 62% on-time. And Logistics Search runs **Cortex Search** over 100 contracts — type 'port congestion diversion policy' and the right clause surfaces in under a second. No vector DB to operate."

### [2:25–2:50] QUICKSIGHT + AMAZON Q — the executive lens

**Show**: Switch to QuickSight dashboard `mfg-supply-chain-dashboard`

**Tech**: QuickSight Snowflake direct query + Amazon Q topic

> "Same governed data, executive view. **QuickSight** dashboard `mfg-supply-chain-dashboard` live-queries Snowflake — KPIs, top carriers, value-at-risk by region. And **Amazon Q topic** `mfg-supply-chain-q` answers the VP's question — 'Which ports are above 85% utilization?' — from any device, no SQL."

### [2:50–3:10] CLOSE

> "Recap. Logistics docs and AIS feeds land in **Amazon S3**. Snowflake builds the operational truth with **Dynamic Tables**, semantic search, and Cortex Analyst. **AWS Location Service** geofences the ports; **EventBridge** detects the breach; **SNS** fans the alert. **QuickSight** and **Amazon Q** give leadership the executive view. Six Snowflake capabilities, four AWS services, one geo-aware control tower. From an AIS ping at sea to an SNS push on the operator's phone — under a minute, every time. That's the **Supply Chain Command Center** on Snowflake and AWS."

---

## Key Demo Differentiators (vs other AWS demos)

1. **AWS Location Service** — most demos stop at S3; this one uses Location Service as a real-time geo trigger.
2. **EventBridge + SNS fan-out** — alert plumbing the customer is already paying for, finally connected to operational truth.
3. **Geofence-driven incidents** — the demo's hero "incident" is automatically reproducible because the geofence keeps firing.
4. **Cascading impact view** — single click reveals downstream delay propagation, not just the originating event.
5. **Q topic answers** to try: "Which ports are above 85% utilization?" / "What's the value-at-risk for Pacific Express?" / "Which carriers haven't met SLA this month?"
