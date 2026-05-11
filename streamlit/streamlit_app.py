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

page = st.sidebar.radio("Navigation", ["Overview", "Carrier Performance", "Port Congestion", "Stuck Shipments", "Live Map", "Logistics Search", "Ask Supply Chain"], label_visibility="collapsed")
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
        delayed_sg = ship[(ship["STATUS"]=="DELAYED") & (ship["ORIGIN_PORT_NAME"]=="Singapore PSA")]
        st.error(f"INCIDENT: {stuck} shipments STUCK at Singapore PSA (Pacific Express Lines) \u2014 {len(delayed_sg)} downstream shipments DELAYED \u2014 {impact_at_risk/1e6:.1f}M impact at risk")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Shipments", f"{len(ship):,}")
    c2.metric("In Transit", f"{in_transit:,}")
    c3.metric("Delayed", f"{delayed:,}", delta=f"+{delayed} active", delta_color="inverse")
    c4.metric("Stuck", stuck, delta=f"{stuck} critical", delta_color="inverse")
    c5.metric("Total Value", f"${total_value/1e9:.1f}B")

    st.divider()
    cc1, cc2 = st.columns(2)
    with cc1:
        status_order = ["DELIVERED", "IN_TRANSIT", "DELAYED", "STUCK"]
        sc = ship["STATUS"].value_counts().reindex(status_order).fillna(0).astype(int).reset_index()
        sc.columns = ["STATUS", "COUNT"]
        bar_colors = [STATUS_COLORS.get(s, "#95A5A6") for s in sc["STATUS"].tolist()]
        fig = go.Figure(data=[go.Bar(
            y=[str(v) for v in sc["STATUS"].tolist()],
            x=[int(v) for v in sc["COUNT"].tolist()],
            orientation="h",
            marker_color=bar_colors,
            text=[f"{int(v):,}" for v in sc["COUNT"].tolist()],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Count: %{x:,}<extra></extra>",
        )])
        fig.update_layout(title="Shipments by Status", height=350, margin=dict(t=40, b=10, l=100, r=80), xaxis_title="Count", yaxis_title="", xaxis_type="log")
        st.plotly_chart(fig, use_container_width=True)
    with cc2:
        com = ship.groupby("COMMODITY_TYPE")["VALUE_USD"].sum().reset_index().sort_values("VALUE_USD", ascending=True)
        com["VALUE_M"] = com["VALUE_USD"] / 1e6
        top10 = com.tail(10)
        x_vals = [float(v) for v in top10["VALUE_M"].tolist()]
        y_vals = [str(v) for v in top10["COMMODITY_TYPE"].tolist()]
        fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, orientation="h", marker=dict(color=x_vals, colorscale="Blues"), hovertemplate="<b>%{y}</b><br>$%{x:.1f}M<extra></extra>")])
        fig.update_layout(title="Top 10 Commodities by Value ($M)", height=350, margin=dict(t=40, b=10), xaxis_title="$M", yaxis_title="")
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
    fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, orientation="h", marker=dict(color=x_vals, colorscale="RdYlGn", cmin=0, cmax=100), hovertemplate="<b>%{y}</b><br>On-Time: %{x:.1f}%<extra></extra>")])
    fig.add_vline(x=85, line_dash="dash", line_color="green", annotation_text="Target 85%")
    fig.update_layout(title="On-Time % by Carrier", height=600, margin=dict(t=40, b=10, l=180), xaxis_title="On-Time %", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    cc1, cc2 = st.columns(2)
    with cc1:
        top_vol = car.nlargest(15, "TOTAL_SHIPMENTS").sort_values("TOTAL_SHIPMENTS")
        x_vals = [float(v) for v in top_vol["TOTAL_SHIPMENTS"].tolist()]
        y_vals = [str(v) for v in top_vol["CARRIER_NAME"].tolist()]
        fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, orientation="h", marker=dict(color=x_vals, colorscale="Blues"), hovertemplate="<b>%{y}</b><br>Shipments: %{x:.0f}<extra></extra>")])
        fig.update_layout(title="Top 15 Carriers by Volume", height=450, margin=dict(t=40, b=10, l=180), xaxis_title="Shipments", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with cc2:
        worst10 = car.nsmallest(10, "ON_TIME_PCT").sort_values("AVG_DELAY_DAYS")
        x_vals = [float(v) for v in worst10["AVG_DELAY_DAYS"].tolist()]
        y_vals = [str(v) for v in worst10["CARRIER_NAME"].tolist()]
        fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, orientation="h", marker=dict(color=x_vals, colorscale="OrRd"), hovertemplate="<b>%{y}</b><br>Avg Delay: %{x:.1f} days<extra></extra>")])
        fig.update_layout(title="Avg Delay Days — 10 Worst Carriers", height=450, margin=dict(t=40, b=10, l=180), xaxis_title="Days", yaxis_title="")
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

    psorted = ports.sort_values("CURRENT_UTILIZATION_PCT", ascending=True)
    x_vals = [float(v) for v in psorted["CURRENT_UTILIZATION_PCT"].tolist()]
    y_vals = [str(v) for v in psorted["PORT_NAME"].tolist()]
    cong_levels = [str(v) for v in psorted["CONGESTION_LEVEL"].tolist()]
    bar_colors = [CONGESTION_COLORS.get(c, "#888") for c in cong_levels]
    stuck_vals = [int(v) if pd.notna(v) else 0 for v in psorted["STUCK_CONTAINERS"].tolist()]
    fig = go.Figure(data=[go.Bar(x=x_vals, y=y_vals, orientation="h", marker_color=bar_colors, customdata=list(zip(cong_levels, stuck_vals)), hovertemplate="<b>%{y}</b><br>Utilization: %{x:.1f}%<br>Level: %{customdata[0]}<br>Stuck: %{customdata[1]}<extra></extra>")])
    fig.add_vline(x=90, line_dash="dash", line_color="red", annotation_text="Critical 90%")
    fig.add_vline(x=80, line_dash="dash", line_color="orange", annotation_text="High 80%")
    fig.update_layout(title="Port Utilization %", height=520, margin=dict(t=40, b=10, l=180), xaxis_title="Utilization %", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Port Details")
    st.dataframe(ports[["PORT_NAME", "COUNTRY", "CURRENT_UTILIZATION_PCT", "CONTAINERS_AT_PORT", "STUCK_CONTAINERS", "INBOUND_SHIPMENTS", "AVG_DWELL_HOURS", "CONGESTION_LEVEL"]].sort_values("CURRENT_UTILIZATION_PCT", ascending=False).reset_index(drop=True), use_container_width=True)

elif page == "Stuck Shipments":
    st.title("Stuck & Delayed Shipments")
    st.caption("Active incidents requiring intervention")
    ship = load_shipments()
    stuck = ship[ship["STATUS"] == "STUCK"].sort_values("VALUE_USD", ascending=False)
    delayed_sg = ship[(ship["STATUS"] == "DELAYED") & (ship["ORIGIN_PORT_NAME"] == "Singapore PSA")].sort_values("DAYS_DELAYED", ascending=False).head(20)

    if not stuck.empty:
        stuck_val = stuck['VALUE_USD'].sum()/1e6
        stuck_impact = stuck['IMPACT_SCORE'].sum()/1e6
        st.error(f"{len(stuck)} STUCK shipments — total value {stuck_val:.1f}M, total impact {stuck_impact:.1f}M")
        st.dataframe(stuck[["SHIPMENT_ID", "CARRIER_NAME", "ORIGIN_PORT_NAME", "DEST_PORT_NAME", "COMMODITY_TYPE", "CONTAINER_COUNT", "VALUE_USD", "DAYS_DELAYED", "IMPACT_SCORE"]].reset_index(drop=True), use_container_width=True)
    else:
        st.success("No stuck shipments.")

    st.subheader("Downstream Delayed (origin Singapore PSA)")
    if not delayed_sg.empty:
        st.warning(f"{len(delayed_sg)} shipments delayed by Singapore congestion")
        st.dataframe(delayed_sg[["SHIPMENT_ID", "CARRIER_NAME", "DEST_PORT_NAME", "COMMODITY_TYPE", "DAYS_DELAYED", "VALUE_USD"]].reset_index(drop=True), use_container_width=True)

elif page == "Live Map":
    st.title("Live Vessel Map")
    st.caption("Real-time vessel positions from Snowflake")
    try:
        vessels = session.sql("SELECT VESSEL_NAME, CARRIER_NAME, LAT, LON, HEADING_DEG, SPEED_KTS, DESTINATION_PORT, STATUS FROM MANUFACTURING_SUPPLY_CHAIN.CURATED.VW_VESSEL_LIVE").to_pandas()
        ports = load_ports()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vessels Tracked", len(vessels))
        c2.metric("Stuck", int((vessels["STATUS"]=="STUCK").sum()))
        c3.metric("In Transit", int((vessels["STATUS"]=="IN_TRANSIT").sum()))
        c4.metric("Avg Speed (kts)", f"{vessels['SPEED_KTS'].astype(float).mean():.1f}")
        if int((vessels["STATUS"]=="STUCK").sum()) > 0:
            st.error("3 vessels of Pacific Express Lines stuck at Singapore PSA — loitering > 6 hours")
        st.markdown('<span style="font-size:14px;"><span style="color:#3498DB;">&#9679;</span> Port&nbsp;&nbsp;&nbsp;<span style="color:#2ECC71;">&#9679;</span> In Transit&nbsp;&nbsp;&nbsp;<span style="color:#E74C3C;">&#9679;</span> Stuck</span>', unsafe_allow_html=True)
        import pydeck as pdk
        color_map = {"STUCK": [231, 76, 60, 200], "IN_TRANSIT": [46, 204, 113, 200]}
        vessels["color"] = vessels["STATUS"].map(color_map).apply(lambda x: x if x else [149, 165, 166, 200])
        vessels["NAME"] = vessels["VESSEL_NAME"]
        vessels["DETAIL"] = vessels["CARRIER_NAME"] + " | " + vessels["STATUS"] + " | " + vessels["SPEED_KTS"].astype(str) + " kts → " + vessels["DESTINATION_PORT"]
        port_coords = ports.set_index("PORT_NAME")[["LAT", "LON"]].rename(columns={"LAT": "DEST_LAT", "LON": "DEST_LON"})
        vessels = vessels.merge(port_coords, left_on="DESTINATION_PORT", right_index=True, how="left")
        ports["NAME"] = ports["PORT_NAME"]
        ports["DETAIL"] = "Port | " + ports["COUNTRY"]
        vessel_layer = pdk.Layer(
            "ScatterplotLayer",
            data=vessels,
            get_position=["LON", "LAT"],
            get_fill_color="color",
            get_radius=60000,
            pickable=True,
        )
        route_layer = pdk.Layer(
            "ArcLayer",
            data=vessels[vessels["STATUS"] == "IN_TRANSIT"],
            get_source_position=["LON", "LAT"],
            get_target_position=["DEST_LON", "DEST_LAT"],
            get_source_color=[46, 204, 113, 160],
            get_target_color=[52, 152, 219, 160],
            get_width=2,
            pickable=False,
        )
        port_layer = pdk.Layer(
            "ScatterplotLayer",
            data=ports,
            get_position=["LON", "LAT"],
            get_fill_color=[52, 152, 219, 180],
            get_radius=50000,
            pickable=True,
        )
        view_state = pdk.ViewState(latitude=20, longitude=100, zoom=2, pitch=0)
        deck = pdk.Deck(
            layers=[port_layer, route_layer, vessel_layer],
            initial_view_state=view_state,
            tooltip={"html": "<b>{NAME}</b><br/>{DETAIL}", "style": {"backgroundColor": "#1a1a2e", "color": "white"}},
        )
        st.pydeck_chart(deck)

        st.subheader("Vessels")
        st.dataframe(vessels[["VESSEL_NAME", "CARRIER_NAME", "LAT", "LON", "HEADING_DEG", "SPEED_KTS", "DESTINATION_PORT", "STATUS"]].reset_index(drop=True), use_container_width=True)
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
            escaped_q = q.replace("\\", "\\\\").replace('"', '\\"')
            df = session.sql(f"""SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                'MANUFACTURING_SUPPLY_CHAIN.SEARCH.LOGISTICS_SEARCH',
                '{{"query": "{escaped_q}", "columns": ["TITLE", "CATEGORY", "CONTENT"], "limit": 5}}'
            ) AS R""").to_pandas()
            results = json.loads(df["R"].iloc[0]).get("results", [])
            for r in results:
                with st.expander(f"📄 {r.get('TITLE', 'Doc')} — *{r.get('CATEGORY', '')}*"):
                    content = r.get("CONTENT", "").replace("$", "\\$")
                    lines = content.split("\n")
                    formatted = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if line.endswith(":"):
                            formatted.append(f"**{line}**")
                        elif line[0].isdigit() and "." in line[:4]:
                            formatted.append(f"- {line}")
                        else:
                            formatted.append(line)
                    st.markdown("\n\n".join(formatted))
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


