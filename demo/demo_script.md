# Singapore Manufacturing Logistics Control Tower

**Singapore - Factory to Port Outbound Logistics**
Use case: On-time shipments, shipment traceability and disruption risk

> Logistics monitoring for Kestrel Strait Industries, a fictional Singapore-based precision manufacturer, and its network of 30 sites across 6 Singapore planning areas (factory dispatch docks, distribution centers, cross-docks, container yards and port terminals): dynamic tables, a holdout-evaluated disruption-risk classifier, a shipment-volume forecast and grounded AI answers.

## Why Snowflake

- **Dynamic tables** reconcile on-time shipments, exception moves and equipment uptime from RAW site data, with checks in `run_core.py`
- **Disruption-risk classification** gives a holdout-evaluated next-7-day disruption probability per site
- **Shipment-volume forecast** projects 14 days of network-wide shipment volume with prediction intervals
- **Grounded AI**: the Cortex Agent (Analyst over a semantic view, plus Search over SOPs) shows its SQL and SOP citations
- **Live telemetry**: a native simulator (Snowflake only) or IoT Core, S3 and Snowpipe (AWS build), then an alert and email

## What is built

| | |
|---|---|
| Dimension table | `RAW.SITES` (30 rows) |
| Fact table | `RAW.SITE_DAILY` (2,700 site-days, 90 days) |
| Curated layer | `CURATED.KPI_SUMMARY`, `PERFORMANCE_SUMMARY`, `DISRUPTION_CAUSES`, `TREND_ANALYSIS` |
| ML | `ML.DISRUPTION_RISK_SCORES`, `ML.DISRUPTION_RISK_HOLDOUT_METRICS`, `ML.VOLUME_FORECAST`, `ML.DWELL_ANOMALIES` |

Planning areas: Tuas (10 sites), Pasir Panjang, Jurong East, Woodlands, Changi, Seletar (4 sites each).
Site types: Factory Dispatch Dock, Distribution Center, Port Terminal, Cross-Dock, Container Yard.

## KPI cards (live from `CURATED.KPI_SUMMARY`; no fallback values)

| Card | Value from the seeded data |
|---|---|
| On-Time Shipments | 89.8% |
| Supply Disruptions | 243 |
| Exceptions per 1k Moves | 18.20 |
| Shipments Handled | 1,423,449 |
| Equipment Uptime | 98.7% |
| Sites Monitored | 30 |
| Equipment Readiness | 86.5% |

Values are synthetic. A rebuild reproduces them because the data is HASH-seeded; dates are relative to the build day.

## Demo flow

1. Executive Cockpit (Priya Nair): KPIs, daily on-time shipments, late shipments by disruption cause, site table with planning area
2. Predictive (Marcus Lim): holdout metrics, risk bands, 14-day shipment-volume forecast, shipment dwell-time anomalies
3. Site Health: equipment uptime, equipment readiness, PM compliance against on-time shipments, then generate the action memo
4. Live IoT: run `CALL APP.SIMULATE_TELEMETRY(20)` (Snowflake only) or `python aws/publish_telemetry.py --count 20` (AWS build). Then run `EXECUTE ALERT APP.LIVE_ALARM_ALERT` and show the alert log and email.
5. Ask AI: ask "What is the on-time rate by planning area?" The Cortex Agent answers through the semantic view and cites SOPs from Cortex Search. The SQL is shown.
6. QuickSight (AWS build): the same Snowflake tables through DIRECT_QUERY
7. Architecture: both builds side by side

## Talking points

- Per-site on-time rate ranges from 85.3% to 92.8%. Pasir Panjang is the lowest planning area, at 89.1%; Changi is the highest, at 90.7%.
- Quay crane outages make the most shipments late (5,832) of the 14 disruption causes.
- The risk model is evaluated on a time-based holdout: precision 0.52 and recall 0.42 at 0.5, against a 0.40 base rate. Present it as triage, not a guarantee.
- The Pasir Panjang squall berth suspension and the Woodlands checkpoint clearance outage are excluded from disruption labels, because they are area-wide events, not site-driven.
- Shipment traceability: SOPs require tagging affected shipments with their order and container IDs, and each site-day records on-time shipments and order fill rate.

## Business impact

Use only the sourced references in `README.md` (Business Impact).
