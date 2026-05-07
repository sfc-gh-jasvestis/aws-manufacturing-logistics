# Demo Script: Geo-aware Logistics Control Tower
## ~70-second walkthrough — Snowflake + Amazon Location Service + EventBridge + SNS + QuickSight

---

## The Story
Three Pacific Express vessels stuck in the Singapore PSA approach geofence. Twelve downstream shipments delayed. EventBridge fires the alert; SNS pushes it to ops. Resolve the incident before the next shift change.

---

## Personas

| Persona | Tool | What they care about |
|---|---|---|
| Logistics Operator | Streamlit on Snowflake + Live Map (AWS Location Service) | Geofence breaches, stuck containers, carrier scorecards |
| Supply Chain VP | Amazon QuickSight + Amazon Q | Network KPIs, value-at-risk, alert fan-out |

---

## Script

### [0:00–0:10] HOOK
> "Three vessels stuck in the Singapore PSA geofence. Twelve downstream shipments delayed. AWS Location Service fired the alert; let's resolve it in under a minute."

### [0:10–0:30] STREAMLIT — Live Map (AWS Location Service)
> Open `MANUFACTURING_SUPPLY_CHAIN.APP.SUPPLY_CHAIN_COMMAND_CENTER` -> page **Live Map (AWS Location)**.
> "Three red pins inside the Singapore approach. Ports in blue, vessels colored by status. The same lat/lon publishes to AWS Location Service tracker `mfg-vessels`; geofence `singapore-psa-approach` flags any vessel that loiters > 6 h."

### [0:30–0:45] EVENT BRIDGE + SNS ALERT
> "Pick a stuck shipment, click **Raise alert** — the stored proc returns the EventBridge `PutEvents` payload that bus `mfg-supply-chain-bus` would receive. Rule `mfg-stuck-shipment-rule` fans it to SNS topic `mfg-stuck-alerts` — mobile push, email, Slack, all in one fan-out."

### [0:45–1:00] CORTEX AI + QUICKSIGHT
> "Ask the Data: 'Which carrier has the most delayed shipments?' Cortex Analyst over `SUPPLY_CHAIN_SEMANTIC_VIEW` returns Pacific Express. QuickSight dashboard `mfg-supply-chain-dashboard` live-queries Snowflake; Amazon Q topic `mfg-supply-chain-q` answers natural-language questions for the VP."

### [1:00–1:10] CLOSE
> "Snowflake is the control tower; AWS Location Service is the radar; EventBridge + SNS are the dispatcher. One governed dataset, three AWS surfaces, zero copies."

---

## Pre-Recording Checklist
- [ ] Confirm 3 STUCK at Singapore PSA in `SHIPMENT_STATUS`
- [ ] Confirm 3 STUCK rows in `DIM_VESSEL_TRACK`
- [ ] Run `CALL AI.SP_RAISE_STUCK_ALERT('<id>')` — verify EventBridge payload
- [ ] Live Map renders all 10 vessels
- [ ] Open https://app.snowflake.com/YOUR_ORG/sg_<YOUR_CONNECTION>/#/streamlit-apps/MANUFACTURING_SUPPLY_CHAIN.APP.SUPPLY_CHAIN_COMMAND_CENTER
- [ ] Open https://us-west-2.quicksight.aws.amazon.com/sn/dashboards/mfg-supply-chain-dashboard
