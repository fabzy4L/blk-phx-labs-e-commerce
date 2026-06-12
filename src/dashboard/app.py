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

@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
def load_cohort_metrics() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            "SELECT * FROM cohort_metrics ORDER BY cohort_month, months_since_first_order",
            conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_subscription_health() -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()

        cancellations = conn.execute(
            """SELECT COUNT(*) FROM subscription_events
               WHERE event_type = 'subscription_cancelled' AND occurred_at >= ?""",
            (week_ago,),
        ).fetchone()[0]

        total_subscribers = conn.execute(
            "SELECT COUNT(DISTINCT email) FROM subscription_events WHERE event_type = 'subscription_started'",
        ).fetchone()[0]

        conn.close()

        rate = cancellations / total_subscribers if total_subscribers > 0 else 0.0
        return {
            "cancellations_this_week": cancellations,
            "total_subscribers": total_subscribers,
            "weekly_churn_rate": rate,
            "alert": rate > 0.05,
        }
    except Exception:
        return {"cancellations_this_week": 0, "total_subscribers": 0, "weekly_churn_rate": 0.0, "alert": False}


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
    st.metric("Revenue", f"${total_revenue:,.2f}")
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

# ── COHORT RETENTION ──────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("Cohort Retention")

cohort_df = load_cohort_metrics()

if not cohort_df.empty:
    pivot = cohort_df.pivot(
        index="cohort_month",
        columns="months_since_first_order",
        values="retention_rate",
    )

    z_vals = pivot.values * 100
    text_vals = [
        [f"{v:.0f}%" if not pd.isna(v) else "" for v in row]
        for row in z_vals
    ]

    fig_cohort = go.Figure(data=go.Heatmap(
        z=z_vals,
        x=[f"Month +{c}" for c in pivot.columns],
        y=pivot.index.tolist(),
        colorscale="YlOrRd",
        text=text_vals,
        texttemplate="%{text}",
        showscale=True,
        colorbar=dict(title="Retention %"),
    ))
    fig_cohort.update_layout(
        plot_bgcolor="#1a1a2e", paper_bgcolor="#0a0a0a",
        font_color="#ffffff",
        xaxis_title="Months Since First Order",
        yaxis_title="Acquisition Cohort",
    )
    st.plotly_chart(fig_cohort, use_container_width=True)

    # LTV by cohort at Month +1
    m1 = cohort_df[cohort_df["months_since_first_order"] == 1]
    if not m1.empty:
        fig_ltv = px.bar(
            m1, x="cohort_month", y="avg_ltv",
            color_discrete_sequence=["#c8a96e"],
            labels={"avg_ltv": "Avg LTV ($)", "cohort_month": "Cohort"},
            title="Avg Cumulative LTV at Month +1 by Cohort",
        )
        fig_ltv.update_layout(
            plot_bgcolor="#1a1a2e", paper_bgcolor="#0a0a0a",
            font_color="#ffffff", showlegend=False,
        )
        st.plotly_chart(fig_ltv, use_container_width=True)
else:
    st.info("No cohort data yet. Run the pipeline to compute retention metrics.")

# ── SUBSCRIPTION HEALTH ───────────────────────────────────────────────────────

st.markdown("---")
st.subheader("Subscription Health")

sub_health = load_subscription_health()
churn_rate_pct = sub_health["weekly_churn_rate"] * 100

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    st.metric("Weekly Cancellations", sub_health["cancellations_this_week"])
with col_s2:
    st.metric("Total Subscribers", sub_health["total_subscribers"])
with col_s3:
    delta_color = "inverse" if sub_health["alert"] else "normal"
    st.metric(
        "Weekly Churn Rate",
        f"{churn_rate_pct:.1f}%",
        delta=f"{'⚠ ALERT' if sub_health['alert'] else 'OK'} (threshold: 5%)",
        delta_color=delta_color,
    )

if sub_health["alert"]:
    st.error(
        f"Churn rate {churn_rate_pct:.1f}% exceeds 5% threshold. "
        "Check Klaviyo win-back flow and review cancellation reasons."
    )

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
except Exception:
    st.info("Run the pipeline to check phase triggers.")
