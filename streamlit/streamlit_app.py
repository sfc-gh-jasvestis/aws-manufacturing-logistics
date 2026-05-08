import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import _snowflake
from snowflake.snowpark.context import get_active_session

session = get_active_session()

def coerce_numeric(df, cols=None):
    """Force Decimal/object cols to float64 so plotly renders them numerically (not as categorical)."""
    if df is None or len(df) == 0:
        return df
    target = cols or [c for c in df.columns if df[c].dtype == "object"]
    for c in target:
        try:
            df[c] = pd.Series([float(x) if x is not None else None for x in df[c]], index=df.index, dtype="float64")
        except (TypeError, ValueError):
            pass
    return df
st.set_page_config(page_title="Supply Chain Command Center", layout="wide", page_icon="ship")

STATUS_COLORS = {"DELIVERED": "#2ECC71", "IN_TRANSIT": "#3498DB", "DELAYED": "#F39C12", "STUCK": "#E74C3C", "CANCELLED": "#95A5A6"}
CONGESTION_COLORS = {"NORMAL": "#2ECC71", "MODERATE": "#3498DB", "HIGH": "#F39C12", "CRITICAL": "#E74C3C"}

page = st.sidebar.radio("Navigation", ["Overview", "Carrier Performance", "Port Congestion", "Stuck Shipments", "Live Map (AWS Location)", "Logistics Search", "Ask Supply Chain"], label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.markdown("### Supply Chain Command")
st.sidebar.caption("Real-time logistics monitoring across 30 carriers, 20 ports, 15 warehouses")


@st.cache_data(ttl=60)
def load_shipments():
    df = coerce_numeric(session.sql("SELECT STATUS, CARRIER_NAME, COMMODITY_TYPE, VALUE_USD, DAYS_DELAYED, IMPACT_SCORE, ORIGIN_PORT_NAME, DEST_PORT_NAME, CONTAINER_COUNT, SHIPMENT_ID FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.SHIPMENT_STATUS").to_pandas())
    for c in ["VALUE_USD", "DAYS_DELAYED", "IMPACT_SCORE", "CONTAINER_COUNT"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(ttl=60)
def load_carriers():
    df = coerce_numeric(session.sql("SELECT * FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.CARRIER_PERFORMANCE WHERE TOTAL_SHIPMENTS > 0").to_pandas())
    for c in ["ON_TIME_PCT", "TOTAL_SHIPMENTS", "DELIVERED_COUNT", "DELAYED_COUNT", "STUCK_COUNT", "IN_TRANSIT_COUNT", "AVG_DELAY_DAYS", "TOTAL_VALUE_USD", "TOTAL_CONTAINERS"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(ttl=60)
def load_ports():
    df = coerce_numeric(session.sql("SELECT * FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.PORT_CONGESTION").to_pandas())
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
        labels = [str(x) for x in sc["STATUS"].tolist()]
        values = [int(x) for x in sc["COUNT"].tolist()]
        colors = [STATUS_COLORS.get(l, "#888") for l in labels]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4, marker=dict(colors=colors), sort=False, textinfo="label+percent")])
        fig.update_layout(title="Shipments by Status", height=350, margin=dict(t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with cc2:
        com = session.sql("SELECT COMMODITY_TYPE, (SUM(VALUE_USD)/1e6)::FLOAT AS VALUE_M FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.SHIPMENT_STATUS GROUP BY COMMODITY_TYPE ORDER BY VALUE_M ASC LIMIT 10").to_pandas()
        x_vals = [float(v) for v in com["VALUE_M"].tolist()]
        y_vals = [str(v) for v in com["COMMODITY_TYPE"].tolist()]
        fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, orientation="h", marker=dict(color=x_vals, colorscale="Blues"))])
        fig.update_layout(title="Top 10 Commodities by Value ($M)", height=350, margin=dict(t=40, b=10), xaxis_title="VALUE_M", yaxis_title="COMMODITY_TYPE")
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
    x_vals = [float(v) for v in car_sorted["ON_TIME_PCT"].tolist()]
    y_vals = [str(v) for v in car_sorted["CARRIER_NAME"].tolist()]
    fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, orientation="h", marker=dict(color=x_vals, colorscale="RdYlGn", cmin=60, cmax=95, colorbar=dict(title="On-Time %")), hovertemplate="<b>%{y}</b><br>On-Time: %{x:.1f}%<extra></extra>")])
    fig.add_vline(x=85, line_dash="dash", line_color="green", annotation_text="Target 85%")
    fig.update_layout(title="On-Time % by Carrier", height=600, margin=dict(t=40, b=10, l=180), xaxis_title="On-Time %", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    cc1, cc2 = st.columns(2)
    with cc1:
        top_vol = car.nlargest(15, "TOTAL_SHIPMENTS").sort_values("TOTAL_SHIPMENTS")
        x_vals = [int(v) for v in top_vol["TOTAL_SHIPMENTS"].tolist()]
        y_vals = [str(v) for v in top_vol["CARRIER_NAME"].tolist()]
        fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, orientation="h", marker=dict(color=x_vals, colorscale="Blues"), hovertemplate="<b>%{y}</b><br>Shipments: %{x:,}<extra></extra>")])
        fig.update_layout(title="Top 15 Carriers by Volume", height=450, margin=dict(t=40, b=10, l=180), xaxis_title="Total Shipments", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with cc2:
        worst10 = car.nsmallest(10, "ON_TIME_PCT").sort_values("AVG_DELAY_DAYS")
        x_vals = [float(v) for v in worst10["AVG_DELAY_DAYS"].tolist()]
        y_vals = [str(v) for v in worst10["CARRIER_NAME"].tolist()]
        fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, orientation="h", marker=dict(color=x_vals, colorscale="OrRd"), hovertemplate="<b>%{y}</b><br>Avg Delay: %{x:.2f} days<extra></extra>")])
        fig.update_layout(title="Avg Delay Days — 10 Worst Carriers", height=450, margin=dict(t=40, b=10, l=180), xaxis_title="Avg Delay Days", yaxis_title="")
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
    labels, parents, values, colors, customdata = ["Global"], [""], [0], [None], [[0, 0.0]]
    for country in sorted(tm["COUNTRY"].dropna().unique()):
        labels.append(str(country)); parents.append("Global"); values.append(0); colors.append(None); customdata.append([0, 0.0])
    for _, r in tm.iterrows():
        labels.append(str(r["PORT_NAME"]))
        parents.append(str(r["COUNTRY"]))
        values.append(int(r["CONTAINERS_AT_PORT"]))
        colors.append(float(r["CURRENT_UTILIZATION_PCT"]))
        customdata.append([int(r["STUCK_CONTAINERS"]), float(r["CURRENT_UTILIZATION_PCT"])])
    fig = go.Figure(go.Treemap(labels=labels, parents=parents, values=values, branchvalues="total", marker=dict(colors=colors, colorscale="RdYlGn_r", cmin=60, cmax=95, showscale=True, colorbar=dict(title="Util %")), customdata=customdata, hovertemplate="<b>%{label}</b><br>Containers: %{value:,}<br>Utilization: %{customdata[1]:.1f}%<br>Stuck: %{customdata[0]:,}<extra></extra>"))
    fig.update_layout(title="Port Congestion Treemap (size = containers at port, color = utilization %)", height=420, margin=dict(t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    ports_sorted = ports.sort_values("CURRENT_UTILIZATION_PCT", ascending=True)
    x_vals = [float(v) for v in ports_sorted["CURRENT_UTILIZATION_PCT"].tolist()]
    y_vals = [str(v) for v in ports_sorted["PORT_NAME"].tolist()]
    bar_colors = [CONGESTION_COLORS.get(str(c), "#888") for c in ports_sorted["CONGESTION_LEVEL"].tolist()]
    stuck_cd = [[int(s), int(c)] for s, c in zip(ports_sorted["STUCK_CONTAINERS"].tolist(), ports_sorted["CONTAINERS_AT_PORT"].tolist())]
    fig2 = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, orientation="h", marker=dict(color=bar_colors), customdata=stuck_cd, hovertemplate="<b>%{y}</b><br>Utilization: %{x:.1f}%<br>Stuck: %{customdata[0]:,}<br>Containers: %{customdata[1]:,}<extra></extra>")])
    fig2.add_vline(x=90, line_dash="dash", line_color="red", annotation_text="Critical 90%")
    fig2.add_vline(x=80, line_dash="dash", line_color="orange", annotation_text="High 80%")
    fig2.update_layout(title="Port Utilization %", height=520, margin=dict(t=40, b=10, l=180), xaxis_title="Utilization %", yaxis_title="")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Port Details")
    st.dataframe(ports[["PORT_NAME", "COUNTRY", "CURRENT_UTILIZATION_PCT", "CONTAINERS_AT_PORT", "STUCK_CONTAINERS", "INBOUND_SHIPMENTS", "AVG_DWELL_HOURS", "CONGESTION_LEVEL"]].sort_values("CURRENT_UTILIZATION_PCT", ascending=False).reset_index(drop=True), use_container_width=True)

elif page == "Stuck Shipments":
    st.title("Stuck & Delayed Shipments")
    st.caption("Active incidents requiring intervention")
    ship = load_shipments()
    stuck = ship[ship["STATUS"] == "STUCK"].sort_values("VALUE_USD", ascending=False)
    delayed_sg = ship[(ship["STATUS"] == "DELAYED") & (ship["ORIGIN_PORT_NAME"] == "Singapore PSA")].sort_values("DAYS_DELAYED", ascending=False).head(20)

    if not stuck.empty:
        st.error(f"{len(stuck)} STUCK shipments — total value \${stuck['VALUE_USD'].sum()/1e6:.1f}M, total impact \${stuck['IMPACT_SCORE'].sum()/1e6:.1f}M")
        st.dataframe(stuck[["SHIPMENT_ID", "CARRIER_NAME", "ORIGIN_PORT_NAME", "DEST_PORT_NAME", "COMMODITY_TYPE", "CONTAINER_COUNT", "VALUE_USD", "DAYS_DELAYED", "IMPACT_SCORE"]].reset_index(drop=True), use_container_width=True)
    else:
        st.success("No stuck shipments.")

    st.subheader("Downstream Delayed (origin Singapore PSA)")
    if not delayed_sg.empty:
        st.warning(f"{len(delayed_sg)} shipments delayed by Singapore congestion")
        st.dataframe(delayed_sg[["SHIPMENT_ID", "CARRIER_NAME", "DEST_PORT_NAME", "COMMODITY_TYPE", "DAYS_DELAYED", "VALUE_USD"]].reset_index(drop=True), use_container_width=True)

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
        st.dataframe(vessels.reset_index(drop=True), use_container_width=True)

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
                                st.dataframe(session.sql(sql).to_pandas().reset_index(drop=True), use_container_width=True)
                            except Exception:
                                pass
                else:
                    st.error(parsed)
            except Exception as e:
                st.error(f"Error: {e}")

