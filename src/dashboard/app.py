"""
BLK PHX LABS — Analytics Dashboard
Streamlit app. Shows funnel metrics, revenue trends, cohort retention, churn signals.
Run: streamlit run src/dashboard/app.py
"""

import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = "blkphx.db"

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BLK PHX LABS — Analytics",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
    .main { background-color: #0a0a0a; }
    .metric-card { background: #1a1a2e; padding: 1rem; border-radius: 8px; border-left: 3px solid #c8a96e; }
    h1, h2, h3 { color: #c8a96e; }
    </style>
""", unsafe_allow_html=True)


# ── DATA LOADERS ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)  # refresh every 5 min
def load_daily_metrics(days: int = 30) -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            "SELECT * FROM daily_metrics ORDER BY date DESC LIMIT ?",
            conn, params=(days,)
        )
        conn.close()
        return df.sort_values("date")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_orders(days: int = 30) -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH)
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = pd.read_sql_query(
            "SELECT * FROM orders WHERE created_at >= ? AND financial_status = 'paid'",
            conn, params=(since,)
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_customers() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM customers", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://via.placeholder.com/200x60/0a0a0a/c8a96e?text=BLK+PHX+LABS", width=200)
    st.markdown("---")
    date_range = st.selectbox("Date Range", ["Last 7 days", "Last 30 days", "Last 90 days"])
    days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}
    days = days_map[date_range]

    st.markdown("---")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption("BLK PHX LABS Analytics v1.0")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")


# ── MAIN DASHBOARD ────────────────────────────────────────────────────────────

st.title("🔥 BLK PHX LABS — Command Center")

daily_df = load_daily_metrics(days)
orders_df = load_orders(days)
customers_df = load_customers()

# ── TOP METRICS ───────────────────────────────────────────────────────────────

col1, col2, col3, col4, col5 = st.columns(5)

total_revenue = daily_df["revenue"].sum() if not daily_df.empty else 0
total_orders = daily_df["orders"].sum() if not daily_df.empty else 0
avg_aov = daily_df["aov"].mean() if not daily_df.empty else 0
email_list = daily_df["email_list_size"].iloc[-1] if not daily_df.empty else 0
total_customers = len(customers_df) if not customers_df.empty else 0

with col1:
    st.metric("Revenue", f"${total_revenue:,.2f}", delta=None)
with col2:
    st.metric("Orders", f"{int(total_orders):,}")
with col3:
    st.metric("Avg Order Value", f"${avg_aov:.2f}")
with col4:
    st.metric("Email List", f"{int(email_list):,}")
with col5:
    st.metric("Total Customers", f"{total_customers:,}")

st.markdown("---")

# ── REVENUE TREND ─────────────────────────────────────────────────────────────

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Revenue Trend")
    if not daily_df.empty:
        fig = px.area(
            daily_df, x="date", y="revenue",
            color_discrete_sequence=["#c8a96e"],
            labels={"revenue": "Revenue ($)", "date": "Date"},
        )
        fig.update_layout(
            plot_bgcolor="#1a1a2e", paper_bgcolor="#0a0a0a",
            font_color="#ffffff", showlegend=False,
            xaxis=dict(gridcolor="#333333"),
            yaxis=dict(gridcolor="#333333"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No revenue data yet. Run the pipeline to populate metrics.")

with col_right:
    st.subheader("Phase Status")

    if total_revenue > 0:
        phase_progress = min(total_revenue / 5000 * 100, 100)
        st.progress(phase_progress / 100)
        st.caption(f"Phase 3 trigger: ${total_revenue:,.0f} / $5,000/mo")
    else:
        st.progress(0.0)
        st.caption("Phase 1 — Validation")

    st.markdown("---")
    st.subheader("Email List Growth")
    if not daily_df.empty and "email_list_size" in daily_df.columns:
        fig2 = px.line(
            daily_df, x="date", y="email_list_size",
            color_discrete_sequence=["#4fc3f7"],
        )
        fig2.update_layout(
            plot_bgcolor="#1a1a2e", paper_bgcolor="#0a0a0a",
            font_color="#ffffff", showlegend=False, height=200,
            margin=dict(l=0, r=0, t=0, b=0),
        )
        st.plotly_chart(fig2, use_container_width=True)

# ── ORDERS TABLE ──────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("Recent Orders")

if not orders_df.empty:
    display_cols = ["id", "created_at", "total_price", "customer_email", "fulfillment_status"]
    available_cols = [c for c in display_cols if c in orders_df.columns]
    st.dataframe(
        orders_df[available_cols].head(20),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No orders synced yet.")

# ── CUSTOMER LTV ──────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("Customer LTV Distribution")

if not customers_df.empty and "total_spent" in customers_df.columns:
    ltv_df = customers_df[customers_df["total_spent"] > 0]
    if not ltv_df.empty:
        fig3 = px.histogram(
            ltv_df, x="total_spent", nbins=20,
            color_discrete_sequence=["#c8a96e"],
            labels={"total_spent": "Total Spent ($)"},
        )
        fig3.update_layout(
            plot_bgcolor="#1a1a2e", paper_bgcolor="#0a0a0a",
            font_color="#ffffff", showlegend=False,
        )
        st.plotly_chart(fig3, use_container_width=True)

        avg_ltv = ltv_df["total_spent"].mean()
        repeat_customers = len(ltv_df[ltv_df["orders_count"] > 1]) if "orders_count" in ltv_df.columns else 0
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Avg Customer LTV", f"${avg_ltv:.2f}")
        with col_b:
            st.metric("Repeat Customers", f"{repeat_customers:,}")
else:
    st.info("No customer data yet.")

# ── PHASE TRIGGERS ────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("⚡ Phase Triggers")

try:
    import sys
    sys.path.insert(0, ".")
    from src.pipeline.run import check_phase_triggers
    triggers = check_phase_triggers()
    if triggers:
        for t in triggers:
            st.warning(f"**{t['trigger'].upper()}**: {t['message']}")
    else:
        st.success("No phase triggers active. Continue Phase 1 validation.")
except Exception as e:
    st.info(f"Run the pipeline to check phase triggers.")
