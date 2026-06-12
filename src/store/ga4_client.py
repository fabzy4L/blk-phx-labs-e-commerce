"""
Google Analytics 4 Data API client.
Pulls funnel metrics, traffic sources, and conversion data.
Requires GA4_PROPERTY_ID and GA4_SERVICE_ACCOUNT_JSON_PATH in .env.
"""

import asyncio
import os

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)

GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "")
GA4_CREDENTIALS_PATH = os.getenv("GA4_SERVICE_ACCOUNT_JSON_PATH", "")


def _get_client() -> BetaAnalyticsDataClient:
    """Build GA4 client. Uses service account file if path set, else GOOGLE_APPLICATION_CREDENTIALS."""
    if GA4_CREDENTIALS_PATH and os.path.exists(GA4_CREDENTIALS_PATH):
        return BetaAnalyticsDataClient.from_service_account_file(GA4_CREDENTIALS_PATH)
    return BetaAnalyticsDataClient()


def _run_report(request: RunReportRequest) -> list[dict]:
    """Execute a GA4 RunReport and return rows as list of dicts."""
    client = _get_client()
    response = client.run_report(request)

    dimension_names = [d.name for d in response.dimension_headers]
    metric_names = [m.name for m in response.metric_headers]

    rows = []
    for row in response.rows:
        record = {}
        for i, dim in enumerate(row.dimension_values):
            record[dimension_names[i]] = dim.value
        for i, met in enumerate(row.metric_values):
            record[metric_names[i]] = met.value
        rows.append(record)

    return rows


async def get_traffic_sources(
    start_date: str = "30daysAgo",
    end_date: str = "today",
) -> list[dict]:
    """
    Get session counts and conversions by traffic source/medium.
    Returns [{sessionSource, sessions, conversions, totalRevenue}, ...]
    """
    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[
            Dimension(name="sessionSource"),
            Dimension(name="sessionMedium"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="conversions"),
            Metric(name="totalRevenue"),
        ],
    )
    return await asyncio.to_thread(_run_report, request)


async def get_funnel_metrics(
    start_date: str = "30daysAgo",
    end_date: str = "today",
) -> dict:
    """
    Get top-level funnel conversion rates: sessions → quiz → purchase.
    Maps GA4 event counts to funnel stages.
    """
    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="eventCount")],
    )
    rows = await asyncio.to_thread(_run_report, request)
    event_map = {row["eventName"]: int(row["eventCount"]) for row in rows}

    sessions = event_map.get("session_start", 0)
    quiz_starts = event_map.get("quiz_started", 0)
    quiz_completions = event_map.get("quiz_completed", 0)
    purchases = event_map.get("purchase", 0)

    return {
        "sessions": sessions,
        "quiz_starts": quiz_starts,
        "quiz_completions": quiz_completions,
        "purchases": purchases,
        "session_to_quiz_rate": round(quiz_starts / sessions, 4) if sessions else 0.0,
        "quiz_completion_rate": round(quiz_completions / quiz_starts, 4) if quiz_starts else 0.0,
        "quiz_to_purchase_rate": round(purchases / quiz_completions, 4) if quiz_completions else 0.0,
        "overall_conversion_rate": round(purchases / sessions, 4) if sessions else 0.0,
        "period": {"start": start_date, "end": end_date},
    }


async def get_top_pages(
    start_date: str = "30daysAgo",
    end_date: str = "today",
    limit: int = 10,
) -> list[dict]:
    """Get top pages by sessions with bounce rate and avg session duration."""
    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
        limit=limit,
    )
    return await asyncio.to_thread(_run_report, request)
