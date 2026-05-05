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

page = st.sidebar.radio("Navigation", ["Overview", "Carrier Performance", "Port Congestion", "Stuck Shipments", "Logistics Search", "Ask Supply Chain"], label_visibility="collapsed")
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
        st.error(f"INCIDENT: {stuck} shipments STUCK at Singapore PSA (Pacific Express Lines) — 12 downstream shipments DELAYED — ${impact_at_risk/1e6:.1f}M impact at risk")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Shipments", f"{len(ship):,}")
    c2.metric("In Transit", f"{in_transit:,}")
    c3.metric("Delayed", f"{delayed:,}", delta=f"+{delayed} active", delta_color="inverse")
    c4.metric("Stuck", stuck, delta=f"{stuck} critical", delta_color="inverse")
    c5.metric("Total Value", f"${total_value/1e9:.1f}B")

    st.divider()
    cc1, cc2 = st.columns(2)
    with cc1:
        sc = ship["STATUS"].value_counts().reset_index()
        sc.columns = ["STATUS", "COUNT"]
        fig = px.pie(sc, names="STATUS", values="COUNT", title="Shipments by Status", color="STATUS", color_discrete_map=STATUS_COLORS, hole=0.4)
        fig.update_layout(height=350, margin=dict(t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with cc2:
        com = ship.groupby("COMMODITY_TYPE")["VALUE_USD"].sum().reset_index().sort_values("VALUE_USD", ascending=True)
        com["VALUE_M"] = com["VALUE_USD"] / 1e6
        fig = px.bar(com.tail(10), x="VALUE_M", y="COMMODITY_TYPE", orientation="h", title="Top 10 Commodities by Value ($M)", color="VALUE_M", color_continuous_scale="Blues")
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

    fig = px.scatter_geo(ports, lat="LAT", lon="LON", size="CONTAINERS_AT_PORT", color="CONGESTION_LEVEL", color_discrete_map=CONGESTION_COLORS, hover_name="PORT_NAME", hover_data={"COUNTRY": True, "CURRENT_UTILIZATION_PCT": ":.1f", "STUCK_CONTAINERS": True, "LAT": False, "LON": False}, size_max=35, title="Global Port Congestion Map")
    fig.update_layout(height=450, margin=dict(t=40, b=10), geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth", landcolor="#f5f5f5", oceancolor="#e8f4fd", showocean=True, showcountries=True, countrycolor="#dddddd"))
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(ports.sort_values("CURRENT_UTILIZATION_PCT", ascending=True), x="CURRENT_UTILIZATION_PCT", y="PORT_NAME", orientation="h", color="CONGESTION_LEVEL", color_discrete_map=CONGESTION_COLORS, title="Port Utilization %", hover_data=["STUCK_CONTAINERS", "CONTAINERS_AT_PORT"])
    fig2.add_vline(x=90, line_dash="dash", line_color="red", annotation_text="Critical 90%")
    fig2.add_vline(x=80, line_dash="dash", line_color="orange", annotation_text="High 80%")
    fig2.update_layout(height=520, margin=dict(t=40, b=10, l=180))
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Port Details")
    st.dataframe(ports[["PORT_NAME", "COUNTRY", "CURRENT_UTILIZATION_PCT", "CONTAINERS_AT_PORT", "STUCK_CONTAINERS", "INBOUND_SHIPMENTS", "AVG_DWELL_HOURS", "CONGESTION_LEVEL"]].sort_values("CURRENT_UTILIZATION_PCT", ascending=False), use_container_width=True, hide_index=True)

elif page == "Stuck Shipments":
    st.title("Stuck & Delayed Shipments")
    st.caption("Active incidents requiring intervention")
    ship = load_shipments()
    stuck = ship[ship["STATUS"] == "STUCK"].sort_values("VALUE_USD", ascending=False)
    delayed_sg = ship[(ship["STATUS"] == "DELAYED") & (ship["ORIGIN_PORT_NAME"] == "Singapore PSA")].sort_values("DAYS_DELAYED", ascending=False).head(20)

    if not stuck.empty:
        st.error(f"{len(stuck)} STUCK shipments — total value ${stuck['VALUE_USD'].sum()/1e6:.1f}M, total impact ${stuck['IMPACT_SCORE'].sum()/1e6:.1f}M")
        st.dataframe(stuck[["SHIPMENT_ID", "CARRIER_NAME", "ORIGIN_PORT_NAME", "DEST_PORT_NAME", "COMMODITY_TYPE", "CONTAINER_COUNT", "VALUE_USD", "DAYS_DELAYED", "IMPACT_SCORE"]], use_container_width=True, hide_index=True)
    else:
        st.success("No stuck shipments.")

    st.subheader("Downstream Delayed (origin Singapore PSA)")
    if not delayed_sg.empty:
        st.warning(f"{len(delayed_sg)} shipments delayed by Singapore congestion")
        st.dataframe(delayed_sg[["SHIPMENT_ID", "CARRIER_NAME", "DEST_PORT_NAME", "COMMODITY_TYPE", "DAYS_DELAYED", "VALUE_USD"]], use_container_width=True, hide_index=True)

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
                                st.dataframe(session.sql(sql).to_pandas(), use_container_width=True, hide_index=True)
                            except Exception:
                                pass
                else:
                    st.error(parsed)
            except Exception as e:
                st.error(f"Error: {e}")
