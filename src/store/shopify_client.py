"""
Shopify API client — orders, products, customers, webhooks.
All methods async. Handles rate limiting with exponential backoff.
"""

import hashlib
import hmac
import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-01")
SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")

BASE_URL = f"{SHOPIFY_STORE_URL}/admin/api/{SHOPIFY_API_VERSION}"
HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_orders(
    status: str = "any",
    limit: int = 250,
    since_id: int | None = None,
    created_at_min: str | None = None,
) -> list[dict]:
    """Fetch orders with pagination support."""
    params: dict[str, Any] = {"status": status, "limit": limit}
    if since_id:
        params["since_id"] = since_id
    if created_at_min:
        params["created_at_min"] = created_at_min

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/orders.json", headers=HEADERS, params=params
        )
        response.raise_for_status()
        return response.json().get("orders", [])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_products(limit: int = 250) -> list[dict]:
    """Fetch all active products."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/products.json",
            headers=HEADERS,
            params={"limit": limit, "status": "active"},
        )
        response.raise_for_status()
        return response.json().get("products", [])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_customers(limit: int = 250, since_id: int | None = None) -> list[dict]:
    """Fetch customers with optional pagination."""
    params: dict[str, Any] = {"limit": limit}
    if since_id:
        params["since_id"] = since_id

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/customers.json", headers=HEADERS, params=params
        )
        response.raise_for_status()
        return response.json().get("customers", [])


async def get_revenue_summary(created_at_min: str, created_at_max: str) -> dict:
    """Aggregate revenue metrics for a date range."""
    orders = await get_orders(
        status="paid",
        created_at_min=created_at_min,
    )
    total_revenue = sum(float(o["total_price"]) for o in orders)
    total_orders = len(orders)
    avg_order_value = total_revenue / total_orders if total_orders else 0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_orders": total_orders,
        "avg_order_value": round(avg_order_value, 2),
        "period_start": created_at_min,
        "period_end": created_at_max,
    }


def verify_webhook_signature(data: bytes, hmac_header: str) -> bool:
    """Verify Shopify webhook HMAC signature."""
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode("utf-8"), data, hashlib.sha256
    ).digest()
    import base64
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)
