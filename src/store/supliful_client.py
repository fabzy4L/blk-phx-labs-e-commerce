"""
Supliful API client — Phase 1 dropship fulfillment.
Handles product catalog sync and order submission.
Phase 2: swap this for a private label 3PL integration.
"""

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

SUPLIFUL_API_KEY = os.getenv("SUPLIFUL_API_KEY")
BASE_URL = "https://api.supliful.com/v1"
HEADERS = {
    "Authorization": f"Bearer {SUPLIFUL_API_KEY}",
    "Content-Type": "application/json",
}

# Supliful → Shopify fulfillment status mapping
_STATUS_MAP = {
    "pending": "unfulfilled",
    "processing": "in_progress",
    "shipped": "fulfilled",
    "delivered": "fulfilled",
    "cancelled": "cancelled",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_products() -> list[dict]:
    """Fetch available Supliful products and variants."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/products", headers=HEADERS)
        response.raise_for_status()
        return response.json().get("products", [])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def create_order(
    shopify_order_id: str,
    line_items: list[dict],
    shipping_address: dict,
) -> dict:
    """
    Submit a Shopify order to Supliful for dropship fulfillment.

    Args:
        shopify_order_id: Shopify order ID used as external reference for deduplication
        line_items: List of {variant_id, quantity} dicts
        shipping_address: Customer shipping address dict

    Returns:
        Supliful order dict including supliful_order_id for status tracking.
    """
    payload: dict[str, Any] = {
        "external_id": shopify_order_id,
        "line_items": line_items,
        "shipping_address": shipping_address,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/orders", headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_order_status(supliful_order_id: str) -> dict:
    """Fetch fulfillment status and tracking info for a Supliful order."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/orders/{supliful_order_id}", headers=HEADERS
        )
        response.raise_for_status()
        return response.json()


async def sync_fulfillment_status(
    shopify_order_id: str,
    supliful_order_id: str,
) -> dict:
    """
    Check Supliful fulfillment status and return a normalized dict
    with Shopify-compatible status for display and alerting.
    """
    order = await get_order_status(supliful_order_id)
    supliful_status = order.get("status", "pending")

    return {
        "shopify_order_id": shopify_order_id,
        "supliful_order_id": supliful_order_id,
        "supliful_status": supliful_status,
        "shopify_status": _STATUS_MAP.get(supliful_status, "unfulfilled"),
        "tracking_number": order.get("tracking_number"),
        "tracking_url": order.get("tracking_url"),
        "carrier": order.get("carrier"),
    }
