"""
Klaviyo API client.
Handles profile creation, event tracking, list management, segment pulls.
Uses Klaviyo API v2024-02.
"""

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

KLAVIYO_PRIVATE_KEY = os.getenv("KLAVIYO_PRIVATE_API_KEY")
KLAVIYO_LIST_ID_MAIN = os.getenv("KLAVIYO_LIST_ID_MAIN")

BASE_URL = "https://a.klaviyo.com/api"
HEADERS = {
    "Authorization": f"Klaviyo-API-Key {KLAVIYO_PRIVATE_KEY}",
    "Content-Type": "application/json",
    "revision": "2024-02-15",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def track_event(
    event_name: str,
    email: str,
    properties: dict[str, Any],
    profile_properties: dict[str, Any] | None = None,
) -> dict:
    """
    Track a Klaviyo event for a profile.
    Triggers flows downstream automatically.

    Events used in BLK PHX flows:
    - quiz_completed: quiz funnel → product recommendation flow
    - product_purchased: post-purchase education sequence
    - subscription_started: subscription onboarding flow
    - subscription_cancelled: win-back flow trigger
    - churn_risk_flagged: intervention flow trigger
    """
    payload: dict[str, Any] = {
        "data": {
            "type": "event",
            "attributes": {
                "metric": {"data": {"type": "metric", "attributes": {"name": event_name}}},
                "profile": {
                    "data": {
                        "type": "profile",
                        "attributes": {"email": email, **(profile_properties or {})},
                    }
                },
                "properties": properties,
            },
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/events/", headers=HEADERS, json=payload
        )
        response.raise_for_status()
        return {"status": "tracked", "event": event_name, "email": email}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def upsert_profile(email: str, properties: dict[str, Any]) -> dict:
    """Create or update a Klaviyo profile."""
    payload = {
        "data": {
            "type": "profile",
            "attributes": {"email": email, **properties},
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/profile-import/", headers=HEADERS, json=payload
        )
        response.raise_for_status()
        return response.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def add_to_list(email: str, list_id: str | None = None) -> dict:
    """Add a profile to a Klaviyo list."""
    target_list = list_id or KLAVIYO_LIST_ID_MAIN
    payload = {
        "data": [{"type": "profile", "attributes": {"email": email}}]
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/lists/{target_list}/relationships/profiles/",
            headers=HEADERS,
            json=payload,
        )
        response.raise_for_status()
        return {"status": "added", "list_id": target_list, "email": email}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_list_profiles(list_id: str) -> list[dict]:
    """Fetch all profiles in a list (paginated)."""
    profiles = []
    url = f"{BASE_URL}/lists/{list_id}/profiles/"

    async with httpx.AsyncClient() as client:
        while url:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            profiles.extend(data.get("data", []))
            url = data.get("links", {}).get("next")

    return profiles


async def get_list_size(list_id: str) -> int:
    """Quick count of profiles in a list."""
    profiles = await get_list_profiles(list_id)
    return len(profiles)
