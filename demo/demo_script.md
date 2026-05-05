# Demo Script: Supply Chain Command Center
## ~70-second walkthrough — AWS + Snowflake

---

## The Story
Three shipments stuck at Singapore PSA. Twelve more delayed downstream. $3M in goods sitting in port. Pacific Express Lines at 62% on-time. Resolve it in under a minute.

---

## Personas

| Persona | Tool | What they care about |
|---|---|---|
| Logistics Operator | Streamlit on Snowflake | Live shipment tracking, stuck containers, carrier scorecards |
| Supply Chain VP | Amazon QuickSight + Amazon Q | Network KPIs, carrier mix, value-at-risk |

---

## Script

### [0:00–0:10] HOOK
> "Three shipments stuck at Singapore PSA. Twelve more delayed downstream. Pacific Express Lines at 62% on-time. Let's resolve it in under a minute."

### [0:10–0:35] SNOWFLAKE — STREAMLIT
> Open `MANUFACTURING_SUPPLY_CHAIN.APP.SUPPLY_CHAIN_COMMAND_CENTER`.
> "Overview page — red banner flags Singapore at 94% utilization, Pacific Express the worst carrier. Stuck Shipments page lists each one, with the 12 downstream Singapore origins right under it. Carrier Performance shows Pareto volume: Maersk 6,300 shipments at 91%, Pacific Express 1,000 at 62%. Three Dynamic Tables — `SHIPMENT_STATUS`, `CARRIER_PERFORMANCE`, `PORT_CONGESTION` — refresh every five minutes."

### [0:35–0:50] CORTEX AI
> "Ask the Data: 'Which carrier has the most delayed shipments?' Cortex Analyst over `SUPPLY_CHAIN_SEMANTIC_VIEW` returns the SQL and the answer. Logistics Search runs Cortex Search over 100 contracts — type 'port congestion diversion policy' and the right clauses surface."

### [0:50–1:05] AWS
> "Switch to QuickSight. `mfg-supply-chain-dashboard` live-queries the same Snowflake data: KPIs for stuck/delayed/value, top carriers, status mix. S3 stage `s3://sg-manufacturing-demos-2026/supply-chain/` lands the raw logistics docs. Amazon Q topic `mfg-supply-chain-q`: 'Which ports are above 85% utilization?' answers instantly."

### [1:05–1:10] CLOSE
> "Snowflake powers the operations room. AWS gives leadership the executive view. Same governed data, two consumption patterns."

---

## Pre-Recording Checklist
- [ ] Verify 3 STUCK at Singapore PSA in `SHIPMENT_STATUS`
- [ ] Verify Pacific Express Lines at 62% on-time, 1,000 shipments
- [ ] Open https://app.snowflake.com/YOUR_ORG/sg_<YOUR_CONNECTION>/#/streamlit-apps/MANUFACTURING_SUPPLY_CHAIN.APP.SUPPLY_CHAIN_COMMAND_CENTER
- [ ] Open https://us-west-2.quicksight.aws.amazon.com/sn/dashboards/mfg-supply-chain-dashboard
