"""
BLK PHX LABS — Unified Data Pipeline
Pulls Shopify orders + Klaviyo profiles into local DB.
Computes: revenue, AOV, LTV, cohort retention, churn signals.
Runs on schedule (cron or APScheduler). Idempotent — safe to re-run.
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from src.store.shopify_client import get_orders, get_customers
from src.automation.klaviyo_client import get_list_size, track_event

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

DB_PATH = "blkphx.db"
CHURN_ALERT_THRESHOLD = 0.05  # 5% weekly subscription cancellation rate
CHURN_INACTIVE_DAYS = int(os.getenv("CHURN_INACTIVE_DAYS", "45"))


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            total_price REAL,
            customer_email TEXT,
            financial_status TEXT,
            fulfillment_status TEXT,
            line_items TEXT,
            synced_at TEXT
        );

        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            email TEXT,
            first_name TEXT,
            last_name TEXT,
            orders_count INTEGER,
            total_spent REAL,
            created_at TEXT,
            synced_at TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_metrics (
            date TEXT PRIMARY KEY,
            revenue REAL,
            orders INTEGER,
            new_customers INTEGER,
            aov REAL,
            email_list_size INTEGER,
            computed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS cohort_metrics (
            cohort_month TEXT,
            months_since_first_order INTEGER,
            customers INTEGER,
            retained INTEGER,
            retention_rate REAL,
            avg_ltv REAL,
            computed_at TEXT,
            PRIMARY KEY (cohort_month, months_since_first_order)
        );

        CREATE TABLE IF NOT EXISTS subscription_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            email TEXT NOT NULL,
            product_title TEXT,
            cancellation_reason TEXT,
            occurred_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fulfillment_jobs (
            shopify_order_id TEXT PRIMARY KEY,
            supliful_order_id TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        );
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized.")


async def sync_orders(days_back: int = 7):
    """Pull recent orders from Shopify into local DB."""
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    orders = await get_orders(status="paid", created_at_min=since)

    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()

    for order in orders:
        conn.execute("""
            INSERT OR REPLACE INTO orders
            (id, created_at, total_price, customer_email,
             financial_status, fulfillment_status, line_items, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(order["id"]),
            order["created_at"],
            float(order["total_price"]),
            order.get("email", ""),
            order["financial_status"],
            order.get("fulfillment_status", ""),
            json.dumps(order.get("line_items", [])),
            now,
        ))

    conn.commit()
    conn.close()
    logger.info(f"Synced {len(orders)} orders.")
    return len(orders)


async def sync_customers(days_back: int = 30):
    """Pull customers updated in the last days_back days from Shopify into local DB."""
    updated_since = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    customers = await get_customers(limit=250, updated_at_min=updated_since)

    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()

    for customer in customers:
        conn.execute("""
            INSERT OR REPLACE INTO customers
            (id, email, first_name, last_name, orders_count, total_spent, created_at, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(customer["id"]),
            customer.get("email", ""),
            customer.get("first_name", ""),
            customer.get("last_name", ""),
            customer.get("orders_count", 0),
            float(customer.get("total_spent", 0)),
            customer["created_at"],
            now,
        ))

    conn.commit()
    conn.close()
    logger.info(f"Synced {len(customers)} customers.")


async def compute_daily_metrics(date: str | None = None):
    """Compute and store daily business metrics."""
    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_db()

    df = pd.read_sql_query(
        "SELECT * FROM orders WHERE DATE(created_at) = ? AND financial_status = 'paid'",
        conn,
        params=(target_date,),
    )

    revenue = df["total_price"].sum() if not df.empty else 0.0
    orders = len(df)
    aov = revenue / orders if orders > 0 else 0.0

    new_customers_df = pd.read_sql_query(
        "SELECT COUNT(*) as cnt FROM customers WHERE DATE(created_at) = ?",
        conn,
        params=(target_date,),
    )
    new_customers = new_customers_df["cnt"].iloc[0] if not new_customers_df.empty else 0

    try:
        list_size = await get_list_size(os.getenv("KLAVIYO_LIST_ID_MAIN", ""))
    except Exception:
        list_size = 0

    conn.execute("""
        INSERT OR REPLACE INTO daily_metrics
        (date, revenue, orders, new_customers, aov, email_list_size, computed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        target_date,
        round(revenue, 2),
        orders,
        new_customers,
        round(aov, 2),
        list_size,
        datetime.now(timezone.utc).isoformat(),
    ))

    conn.commit()
    conn.close()

    metrics = {
        "date": target_date,
        "revenue": round(revenue, 2),
        "orders": orders,
        "aov": round(aov, 2),
        "new_customers": new_customers,
        "email_list_size": list_size,
    }
    logger.info(f"Daily metrics computed: {metrics}")
    return metrics


def compute_cohort_metrics():
    """
    Compute month-over-month cohort retention from order history.
    Builds cohort_metrics table: for each acquisition-month cohort, tracks
    how many customers ordered again in each subsequent month and their LTV.
    """
    conn = get_db()

    orders_df = pd.read_sql_query(
        """SELECT customer_email, created_at, total_price
           FROM orders
           WHERE financial_status = 'paid' AND customer_email != ''""",
        conn,
    )

    if orders_df.empty:
        conn.close()
        logger.info("No orders available for cohort computation.")
        return

    orders_df["order_date"] = pd.to_datetime(orders_df["created_at"], utc=True)
    orders_df["order_month"] = orders_df["order_date"].dt.to_period("M")

    first_orders = (
        orders_df.groupby("customer_email")["order_date"]
        .min()
        .reset_index()
        .rename(columns={"order_date": "first_order_at"})
    )
    first_orders["cohort_month"] = first_orders["first_order_at"].dt.to_period("M")

    merged = orders_df.merge(
        first_orders[["customer_email", "cohort_month"]], on="customer_email"
    )
    merged["months_since_first_order"] = (
        merged["order_month"].apply(lambda p: p.ordinal)
        - merged["cohort_month"].apply(lambda p: p.ordinal)
    )

    now = datetime.now(timezone.utc).isoformat()
    rows = []

    for cohort_month, cohort_group in merged.groupby("cohort_month"):
        cohort_size = cohort_group["customer_email"].nunique()

        for months_offset, period_group in cohort_group.groupby("months_since_first_order"):
            retained = period_group["customer_email"].nunique()
            retention_rate = retained / cohort_size if cohort_size > 0 else 0.0

            cumulative = merged[
                (merged["cohort_month"] == cohort_month)
                & (merged["months_since_first_order"] <= months_offset)
            ]
            avg_ltv_val = cumulative.groupby("customer_email")["total_price"].sum().mean()

            rows.append((
                str(cohort_month),
                int(months_offset),
                cohort_size,
                retained,
                round(retention_rate, 4),
                round(float(avg_ltv_val) if not pd.isna(avg_ltv_val) else 0.0, 2),
                now,
            ))

    for row in rows:
        conn.execute("""
            INSERT OR REPLACE INTO cohort_metrics
            (cohort_month, months_since_first_order, customers, retained,
             retention_rate, avg_ltv, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, row)

    conn.commit()
    conn.close()
    logger.info(f"Cohort metrics: {len(rows)} data points across {len(merged['cohort_month'].unique())} cohorts.")


async def detect_churn_risks(days_inactive: int = CHURN_INACTIVE_DAYS) -> list[dict]:
    """
    Find customers with no paid order in the last days_inactive days.
    Fires 'churn_risk_flagged' Klaviyo event to trigger win-back flow.
    Uses orders table as source of truth — works even if customers table is incomplete.
    """
    conn = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_inactive)).isoformat()

    at_risk_df = pd.read_sql_query(
        """SELECT o.customer_email AS email,
                  c.first_name,
                  MAX(o.created_at) AS last_order_at,
                  COUNT(o.id) AS orders_count,
                  SUM(o.total_price) AS total_spent
           FROM orders o
           LEFT JOIN customers c ON o.customer_email = c.email
           WHERE o.financial_status = 'paid' AND o.customer_email != ''
           GROUP BY o.customer_email
           HAVING last_order_at < ?""",
        conn,
        params=(cutoff,),
    )
    conn.close()

    if at_risk_df.empty:
        return []

    flagged = []
    for _, row in at_risk_df.iterrows():
        try:
            await track_event(
                event_name="churn_risk_flagged",
                email=row["email"],
                properties={
                    "last_order_at": row["last_order_at"],
                    "days_inactive": days_inactive,
                    "orders_count": int(row["orders_count"]),
                    "total_spent": float(row["total_spent"]),
                },
            )
            flagged.append({"email": row["email"], "last_order_at": row["last_order_at"]})
        except Exception as e:
            logger.error(f"Churn flag failed for {row['email']}: {e}")

    if flagged:
        logger.warning(f"Churn risk: {len(flagged)} customers flagged inactive for {days_inactive}+ days.")
    return flagged


def check_weekly_churn_rate() -> dict:
    """
    Compute subscription cancellation rate for the past 7 days.
    Fires alert log if rate exceeds CHURN_ALERT_THRESHOLD (5%).
    Requires subscription events to be logged by the Recharge webhook handler.
    """
    conn = get_db()
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

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
    alert = rate > CHURN_ALERT_THRESHOLD

    result = {
        "cancellations_this_week": cancellations,
        "total_subscribers": total_subscribers,
        "weekly_churn_rate": round(rate, 4),
        "alert": alert,
    }

    if alert:
        logger.warning(
            f"CHURN ALERT: Weekly rate {rate:.1%} exceeds {CHURN_ALERT_THRESHOLD:.0%} threshold — "
            f"{cancellations} cancellations / {total_subscribers} subscribers."
        )

    return result


def check_phase_triggers():
    """
    Check if phase upgrade conditions are met.
    Phase 2 trigger: any product >50 units/month
    Phase 3 trigger: $5,000/month gross for 60 days
    """
    conn = get_db()

    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    orders_df = pd.read_sql_query(
        "SELECT line_items FROM orders WHERE created_at >= ? AND financial_status = 'paid'",
        conn,
        params=(thirty_days_ago,),
    )
    conn.close()

    product_counts: dict[str, int] = {}
    for _, row in orders_df.iterrows():
        try:
            items = json.loads(row["line_items"])
            for item in items:
                pid = str(item.get("product_id", ""))
                product_counts[pid] = product_counts.get(pid, 0) + item.get("quantity", 1)
        except Exception:
            continue

    triggers = []
    for pid, count in product_counts.items():
        if count > 50:
            triggers.append({
                "trigger": "phase_2",
                "product_id": pid,
                "units_last_30_days": count,
                "message": f"Product {pid} hit {count} units — evaluate for private label.",
            })
            logger.warning(f"PHASE 2 TRIGGER: Product {pid} → {count} units/month")

    return triggers


async def run_pipeline():
    """Full pipeline run. Called by scheduler."""
    logger.info("Pipeline starting...")
    init_db()
    await sync_orders(days_back=7)
    await sync_customers(days_back=30)
    await compute_daily_metrics()
    compute_cohort_metrics()
    churn_risks = await detect_churn_risks()
    churn_rate = check_weekly_churn_rate()
    triggers = check_phase_triggers()

    if triggers:
        for t in triggers:
            logger.warning(f"TRIGGER: {t}")

    logger.info("Pipeline complete.")
    return {
        "triggers": triggers,
        "churn_risks_flagged": len(churn_risks),
        "weekly_churn_rate": churn_rate,
    }


if __name__ == "__main__":
    asyncio.run(run_pipeline())
