import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import _snowflake
from snowflake.snowpark.context import get_active_session

session = get_active_session()
st.set_page_config(page_title="Supply Chain Command Center", layout="wide", page_icon="ship")

STATUS_COLORS = {"DELIVERED": "#2ECC71", "IN_TRANSIT": "#3498DB", "DELAYED": "#F39C12", "STUCK": "#E74C3C", "CANCELLED": "#95A5A6"}
CONGESTION_COLORS = {"NORMAL": "#2ECC71", "MODERATE": "#3498DB", "HIGH": "#F39C12", "CRITICAL": "#E74C3C"}

page = st.sidebar.radio("Navigation", ["Overview", "Carrier Performance", "Port Congestion", "Stuck Shipments", "Live Map (AWS Location)", "Logistics Search", "Ask Supply Chain", "AWS Architecture"], label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.markdown("### Supply Chain Command")
st.sidebar.caption("Real-time logistics monitoring across 30 carriers, 20 ports, 15 warehouses")


@st.cache_data(ttl=60)
def load_shipments():
    df = session.sql("SELECT STATUS, CARRIER_NAME, COMMODITY_TYPE, VALUE_USD, DAYS_DELAYED, IMPACT_SCORE, ORIGIN_PORT_NAME, DEST_PORT_NAME, CONTAINER_COUNT, SHIPMENT_ID FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.SHIPMENT_STATUS").to_pandas()
    for c in ["VALUE_USD", "DAYS_DELAYED", "IMPACT_SCORE", "CONTAINER_COUNT"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(ttl=60)
def load_carriers():
    df = session.sql("SELECT * FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.CARRIER_PERFORMANCE WHERE TOTAL_SHIPMENTS > 0").to_pandas()
    for c in ["ON_TIME_PCT", "TOTAL_SHIPMENTS", "DELIVERED_COUNT", "DELAYED_COUNT", "STUCK_COUNT", "IN_TRANSIT_COUNT", "AVG_DELAY_DAYS", "TOTAL_VALUE_USD", "TOTAL_CONTAINERS"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(ttl=60)
def load_ports():
    df = session.sql("SELECT * FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.PORT_CONGESTION").to_pandas()
    for c in ["LAT", "LON", "CAPACITY_TEU", "CURRENT_UTILIZATION_PCT", "CONTAINERS_AT_PORT", "STUCK_CONTAINERS", "INBOUND_SHIPMENTS", "AVG_DWELL_HOURS"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["LAT", "LON"])


if page == "Overview":
    st.title("Supply Chain Command Center")
    st.caption("Real-time shipment tracking, carrier performance, and port congestion")
    ship = load_shipments()
    stuck = int((ship["STATUS"] == "STUCK").sum())
    delayed = int((ship["STATUS"] == "DELAYED").sum())
    in_transit = int((ship["STATUS"] == "IN_TRANSIT").sum())
    total_value = ship["VALUE_USD"].sum()
    impact_at_risk = ship[ship["STATUS"].isin(["STUCK", "DELAYED"])]["IMPACT_SCORE"].sum()

    if stuck > 0:
        st.error(f"INCIDENT: {stuck} shipments STUCK at Singapore PSA (Pacific Express Lines) — 12 downstream shipments DELAYED — \${impact_at_risk/1e6:.1f}M impact at risk")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Shipments", f"{len(ship):,}")
    c2.metric("In Transit", f"{in_transit:,}")
    c3.metric("Delayed", f"{delayed:,}", delta=f"+{delayed} active", delta_color="inverse")
    c4.metric("Stuck", stuck, delta=f"{stuck} critical", delta_color="inverse")
    c5.metric("Total Value", f"${total_value/1e9:.1f}B")

    st.divider()
    cc1, cc2 = st.columns(2)
    with cc1:
        sc = session.sql("SELECT STATUS, COUNT(*)::INT AS COUNT FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.SHIPMENT_STATUS GROUP BY STATUS ORDER BY COUNT DESC").to_pandas()
        sc["COUNT"] = sc["COUNT"].astype(float)
        fig = px.pie(sc, names="STATUS", values="COUNT", title="Shipments by Status", color="STATUS", color_discrete_map=STATUS_COLORS, hole=0.4)
        fig.update_traces(textinfo="label+percent", sort=False)
        fig.update_layout(height=350, margin=dict(t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with cc2:
        com = session.sql("SELECT COMMODITY_TYPE, (SUM(VALUE_USD)/1e6)::FLOAT AS VALUE_M FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.SHIPMENT_STATUS GROUP BY COMMODITY_TYPE ORDER BY VALUE_M DESC LIMIT 10").to_pandas()
        com["VALUE_M"] = com["VALUE_M"].astype(float)
        com = com.sort_values("VALUE_M", ascending=True)
        fig = px.bar(com, x="VALUE_M", y="COMMODITY_TYPE", orientation="h", title="Top 10 Commodities by Value ($M)", color="VALUE_M", color_continuous_scale="Blues")
        fig.update_layout(height=350, margin=dict(t=40, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

elif page == "Carrier Performance":
    st.title("Carrier Performance")
    st.caption("On-time performance, delays, and volume across 30 carriers")
    car = load_carriers()
    if car.empty:
        st.info("No carrier data."); st.stop()

    worst = car.nsmallest(1, "ON_TIME_PCT").iloc[0]
    st.warning(f"Worst performer: {worst['CARRIER_NAME']} at {worst['ON_TIME_PCT']:.1f}% on-time ({int(worst['STUCK_COUNT'])} stuck, {int(worst['DELAYED_COUNT'])} delayed)")

    c1, c2, c3 = st.columns(3)
    c1.metric("Carriers", len(car))
    c2.metric("Avg On-Time %", f"{car['ON_TIME_PCT'].mean():.1f}%")
    c3.metric("Below 80% target", int((car["ON_TIME_PCT"] < 80).sum()))

    car_sorted = car.sort_values("ON_TIME_PCT")
    fig = px.bar(car_sorted, x="ON_TIME_PCT", y="CARRIER_NAME", orientation="h", color="ON_TIME_PCT", color_continuous_scale="RdYlGn", range_color=[60, 95], title="On-Time % by Carrier")
    fig.add_vline(x=85, line_dash="dash", line_color="green", annotation_text="Target 85%")
    fig.update_layout(height=600, margin=dict(t=40, b=10, l=180), coloraxis_colorbar=dict(title="On-Time %"))
    st.plotly_chart(fig, use_container_width=True)

    cc1, cc2 = st.columns(2)
    with cc1:
        top_vol = car.nlargest(15, "TOTAL_SHIPMENTS")
        fig = px.bar(top_vol.sort_values("TOTAL_SHIPMENTS"), x="TOTAL_SHIPMENTS", y="CARRIER_NAME", orientation="h", title="Top 15 Carriers by Volume", color="TOTAL_SHIPMENTS", color_continuous_scale="Blues")
        fig.update_layout(height=450, margin=dict(t=40, b=10, l=180), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with cc2:
        worst10 = car.nsmallest(10, "ON_TIME_PCT")
        fig = px.bar(worst10.sort_values("AVG_DELAY_DAYS"), x="AVG_DELAY_DAYS", y="CARRIER_NAME", orientation="h", title="Avg Delay Days — 10 Worst Carriers", color="AVG_DELAY_DAYS", color_continuous_scale="OrRd")
        fig.update_layout(height=450, margin=dict(t=40, b=10, l=180), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

elif page == "Port Congestion":
    st.title("Port Congestion")
    st.caption("Global port utilization and container dwell")
    ports = load_ports()
    if ports.empty:
        st.info("No port data."); st.stop()

    crit = ports[ports["CONGESTION_LEVEL"] == "CRITICAL"]
    if not crit.empty:
        c = crit.iloc[0]
        st.error(f"CRITICAL: {c['PORT_NAME']} ({c['COUNTRY']}) at {c['CURRENT_UTILIZATION_PCT']:.0f}% utilization — {int(c['STUCK_CONTAINERS'])} stuck containers")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ports", len(ports))
    c2.metric("Critical", int((ports["CONGESTION_LEVEL"] == "CRITICAL").sum()))
    c3.metric("High Risk", int(ports["CONGESTION_LEVEL"].isin(["HIGH", "CRITICAL"]).sum()))
    c4.metric("Stuck Containers", f"{int(ports['STUCK_CONTAINERS'].sum()):,}")

    tm = ports.copy()
    tm["CONTAINERS_AT_PORT"] = tm["CONTAINERS_AT_PORT"].fillna(1).clip(lower=1)
    fig = px.treemap(tm, path=[px.Constant("Global"), "COUNTRY", "PORT_NAME"], values="CONTAINERS_AT_PORT", color="CURRENT_UTILIZATION_PCT", color_continuous_scale="RdYlGn_r", range_color=[60, 95], hover_data={"STUCK_CONTAINERS": True, "CURRENT_UTILIZATION_PCT": ":.1f"}, title="Port Congestion Treemap (size = containers at port, color = utilization %)")
    fig.update_layout(height=420, margin=dict(t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(ports.sort_values("CURRENT_UTILIZATION_PCT", ascending=True), x="CURRENT_UTILIZATION_PCT", y="PORT_NAME", orientation="h", color="CONGESTION_LEVEL", color_discrete_map=CONGESTION_COLORS, title="Port Utilization %", hover_data=["STUCK_CONTAINERS", "CONTAINERS_AT_PORT"])
    fig2.add_vline(x=90, line_dash="dash", line_color="red", annotation_text="Critical 90%")
    fig2.add_vline(x=80, line_dash="dash", line_color="orange", annotation_text="High 80%")
    fig2.update_layout(height=520, margin=dict(t=40, b=10, l=180))
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Port Details")
    st.dataframe(ports[["PORT_NAME", "COUNTRY", "CURRENT_UTILIZATION_PCT", "CONTAINERS_AT_PORT", "STUCK_CONTAINERS", "INBOUND_SHIPMENTS", "AVG_DWELL_HOURS", "CONGESTION_LEVEL"]].sort_values("CURRENT_UTILIZATION_PCT", ascending=False), use_container_width=True)

elif page == "Stuck Shipments":
    st.title("Stuck & Delayed Shipments")
    st.caption("Active incidents requiring intervention")
    ship = load_shipments()
    stuck = ship[ship["STATUS"] == "STUCK"].sort_values("VALUE_USD", ascending=False)
    delayed_sg = ship[(ship["STATUS"] == "DELAYED") & (ship["ORIGIN_PORT_NAME"] == "Singapore PSA")].sort_values("DAYS_DELAYED", ascending=False).head(20)

    if not stuck.empty:
        st.error(f"{len(stuck)} STUCK shipments — total value \${stuck['VALUE_USD'].sum()/1e6:.1f}M, total impact \${stuck['IMPACT_SCORE'].sum()/1e6:.1f}M")
        st.dataframe(stuck[["SHIPMENT_ID", "CARRIER_NAME", "ORIGIN_PORT_NAME", "DEST_PORT_NAME", "COMMODITY_TYPE", "CONTAINER_COUNT", "VALUE_USD", "DAYS_DELAYED", "IMPACT_SCORE"]], use_container_width=True)
    else:
        st.success("No stuck shipments.")

    st.subheader("Downstream Delayed (origin Singapore PSA)")
    if not delayed_sg.empty:
        st.warning(f"{len(delayed_sg)} shipments delayed by Singapore congestion")
        st.dataframe(delayed_sg[["SHIPMENT_ID", "CARRIER_NAME", "DEST_PORT_NAME", "COMMODITY_TYPE", "DAYS_DELAYED", "VALUE_USD"]], use_container_width=True)

elif page == "Live Map (AWS Location)":
    st.title("Live Vessel Map")
    st.caption("Real-time vessel positions — Snowflake DIM_VESSEL_TRACK + Amazon Location Service tracker `mfg-vessels`")
    try:
        vessels = session.sql("SELECT VESSEL_NAME, CARRIER_NAME, LAT, LON, SPEED_KTS, DESTINATION_PORT, STATUS FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.VW_VESSEL_LIVE").to_pandas()
        ports = load_ports()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vessels Tracked", len(vessels))
        c2.metric("Stuck", int((vessels["STATUS"]=="STUCK").sum()))
        c3.metric("In Transit", int((vessels["STATUS"]=="IN_TRANSIT").sum()))
        c4.metric("Avg Speed (kts)", f"{vessels['SPEED_KTS'].astype(float).mean():.1f}")
        if int((vessels["STATUS"]=="STUCK").sum()) > 0:
            st.error("Geofence breach: 3 vessels of Pacific Express Lines stuck in the Singapore PSA approach geofence. EventBridge rule `mfg-stuck-shipment-rule` fires SNS topic `mfg-stuck-alerts`.")
        fig = go.Figure()
        fig.add_trace(go.Scattermapbox(lat=ports["LAT"], lon=ports["LON"], mode="markers", marker=dict(size=12, color="#3498DB"), name="Ports", text=ports["PORT_NAME"], hoverinfo="text"))
        sc = {"STUCK": "#E74C3C", "IN_TRANSIT": "#2ECC71"}
        for status, sub in vessels.groupby("STATUS"):
            fig.add_trace(go.Scattermapbox(lat=sub["LAT"], lon=sub["LON"], mode="markers", marker=dict(size=14, color=sc.get(status, "#95A5A6")), name=f"Vessels - {status}", text=sub["VESSEL_NAME"]+" -> "+sub["DESTINATION_PORT"], hoverinfo="text"))
        fig.update_layout(mapbox_style="open-street-map", mapbox_center={"lat": 20, "lon": 100}, mapbox_zoom=2, height=520, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("Vessels")
        st.dataframe(vessels, use_container_width=True)

        st.divider()
        st.subheader("Trigger EventBridge Alert")
        st.caption("Calls `SP_RAISE_STUCK_ALERT` which returns the EventBridge `PutEvents` payload that the customer's bus `mfg-supply-chain-bus` would receive (target: SNS `mfg-stuck-alerts`).")
        ship = load_shipments()
        stuck_ids = ship[ship["STATUS"]=="STUCK"]["SHIPMENT_ID"].tolist()
        if stuck_ids:
            sid = st.selectbox("Stuck shipment", stuck_ids)
            if st.button("Raise alert"):
                with st.spinner("Generating EventBridge payload..."):
                    sql = f"CALL MANUFACTURING_SUPPLY_CHAIN.AI.SP_RAISE_STUCK_ALERT('{sid}')"
                    res = session.sql(sql).to_pandas()
                    payload = res.iloc[0, 0]
                    st.success("EventBridge PutEvents payload:")
                    st.code(payload, language="json")
        else:
            st.info("No stuck shipments to alert on.")
    except Exception as e:
        st.error(f"Live map error: {e}")

elif page == "Logistics Search":
    st.title("Logistics Policy Search")
    st.caption("Cortex Search across shipping policies, contracts, and procedures")
    samples = ["port congestion diversion policy", "force majeure clauses", "stuck container escalation"]
    sample = st.selectbox("Sample searches:", [""] + samples)
    q = st.text_input("Search:", value=sample, placeholder="e.g., demurrage charges")
    if q:
        try:
            df = session.sql(f"SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('MANUFACTURING_SUPPLY_CHAIN.SEARCH.LOGISTICS_SEARCH', '{q.replace(chr(39), chr(39)+chr(39))}', 5) AS R").to_pandas()
            results = json.loads(df["R"].iloc[0]).get("results", [])
            for r in results:
                with st.expander(f"{r.get('TITLE', 'Doc')} - {r.get('CATEGORY', '')}"):
                    st.write(r.get("CONTENT", ""))
        except Exception as e:
            st.error(f"Search error: {e}")

elif page == "Ask Supply Chain":
    st.title("Ask the Data")
    st.caption("Natural language questions powered by Cortex Analyst")
    samples = ["Which carrier has the most delayed shipments?", "What is the total value of stuck shipments?", "Which ports are above 85% utilization?"]
    sample = st.selectbox("Sample questions:", [""] + samples)
    q = st.text_input("Or type your question:", value=sample)
    if q:
        with st.spinner("Cortex Analyst..."):
            try:
                body = {"messages": [{"role": "user", "content": [{"type": "text", "text": q}]}], "semantic_view": "MANUFACTURING_SUPPLY_CHAIN.AI.SUPPLY_CHAIN_SEMANTIC_VIEW"}
                resp = _snowflake.send_snow_api_request("POST", "/api/v2/cortex/analyst/message", {}, {}, body, None, 30000)
                parsed = json.loads(resp["content"])
                if resp["status"] < 400:
                    for block in parsed.get("message", {}).get("content", []):
                        if block.get("type") == "text":
                            st.markdown(block.get("text", ""))
                        elif block.get("type") == "sql":
                            sql = block.get("statement", "")
                            with st.expander("SQL"):
                                st.code(sql, language="sql")
                            try:
                                st.dataframe(session.sql(sql).to_pandas(), use_container_width=True)
                            except Exception:
                                pass
                else:
                    st.error(parsed)
            except Exception as e:
                st.error(f"Error: {e}")

elif page == "AWS Architecture":
    st.title("AWS Architecture - Geo-aware Logistics Control Tower")
    st.caption("Snowflake + Amazon Location Service + EventBridge + SNS + QuickSight")
    a, b, c, d = st.columns(4)
    a.metric("AWS Hero", "Location Service")
    b.metric("Event Bus", "mfg-supply-chain-bus")
    c.metric("Tracker", "mfg-vessels")
    d.metric("SNS Topic", "mfg-stuck-alerts")
    st.markdown(
        """
**Data flow**

1. **S3** (`s3://sg-manufacturing-demos-2026/supply-chain/`) lands raw logistics docs and AIS feeds.
2. **Snowflake** Dynamic Tables (`SHIPMENT_STATUS`, `CARRIER_PERFORMANCE`, `PORT_CONGESTION`, `DIM_VESSEL_TRACK`) refresh every 5 minutes.
3. **Amazon Location Service** tracker `mfg-vessels` consumes the same lat/lon, geofence `singapore-psa-approach` flags any vessel that loiters > 6 h.
4. When a Snowflake shipment goes `STUCK`, `SP_RAISE_STUCK_ALERT` returns an EventBridge `PutEvents` payload to bus `mfg-supply-chain-bus`.
5. EventBridge rule `mfg-stuck-shipment-rule` fans out to SNS topic `mfg-stuck-alerts` (mobile push + email + Slack).
6. **QuickSight** dashboard `mfg-supply-chain-dashboard` live-queries Snowflake for the executive view; **Amazon Q topic** `mfg-supply-chain-q` powers natural-language Q&A.

**ARNs (account __AWS_ACCOUNT_ID__ / us-west-2)**

- `arn:aws:geo:us-west-2:__AWS_ACCOUNT_ID__:tracker/mfg-vessels`
- `arn:aws:geo:us-west-2:__AWS_ACCOUNT_ID__:geofence-collection/singapore-psa`
- `arn:aws:events:us-west-2:__AWS_ACCOUNT_ID__:event-bus/mfg-supply-chain-bus`
- `arn:aws:sns:us-west-2:__AWS_ACCOUNT_ID__:mfg-stuck-alerts`
        """
    )
