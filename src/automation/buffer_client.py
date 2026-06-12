"""
Buffer API client — schedule social media posts across channels.
Supports TikTok, Instagram, LinkedIn via Buffer profile IDs in .env.
"""

import os
from datetime import datetime
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

BUFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN")
BASE_URL = "https://api.bufferapp.com/1"
HEADERS = {"Authorization": f"Bearer {BUFFER_ACCESS_TOKEN}"}

PROFILE_MAP = {
    "tiktok": os.getenv("BUFFER_PROFILE_IDS_TIKTOK", ""),
    "instagram": os.getenv("BUFFER_PROFILE_IDS_INSTAGRAM", ""),
    "linkedin": os.getenv("BUFFER_PROFILE_IDS_LINKEDIN", ""),
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_profiles() -> list[dict]:
    """Fetch all connected Buffer social profiles."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/profiles.json", headers=HEADERS)
        response.raise_for_status()
        return response.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def schedule_post(
    text: str,
    platforms: list[str],
    scheduled_at: str | None = None,
    media_url: str | None = None,
    now: bool = False,
) -> list[dict]:
    """
    Schedule a post to one or more platforms.

    Args:
        text: Post copy (should be compliance-checked before calling)
        platforms: List of 'tiktok', 'instagram', 'linkedin'
        scheduled_at: ISO 8601 timestamp (None = add to end of queue)
        media_url: Optional image or video URL to attach
        now: Post immediately instead of queuing

    Returns:
        Buffer API response (list of update objects, one per profile).
    """
    profile_ids = [PROFILE_MAP[p] for p in platforms if PROFILE_MAP.get(p)]
    if not profile_ids:
        raise ValueError(f"No Buffer profile IDs configured for platforms: {platforms}")

    payload: dict[str, Any] = {"text": text}
    for i, pid in enumerate(profile_ids):
        payload[f"profile_ids[{i}]"] = pid

    if scheduled_at:
        dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        payload["scheduled_at"] = dt.isoformat()
    if now:
        payload["now"] = "true"
    if media_url:
        payload["media[link]"] = media_url

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/updates/create.json",
            headers=HEADERS,
            data=payload,
        )
        response.raise_for_status()
        return response.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_pending_posts(profile_id: str) -> list[dict]:
    """Fetch scheduled (pending) posts for a given profile."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/profiles/{profile_id}/updates/pending.json",
            headers=HEADERS,
        )
        response.raise_for_status()
        return response.json().get("updates", [])


async def schedule_weekly_content(posts: list[dict]) -> dict:
    """
    Batch-schedule a week of content from a list of post dicts.
    Each dict must have: text, platforms. Optional: scheduled_at, media_url.

    Returns summary: {scheduled, failed, errors}.
    """
    results: dict[str, Any] = {"scheduled": 0, "failed": 0, "errors": []}

    for post in posts:
        try:
            await schedule_post(
                text=post["text"],
                platforms=post["platforms"],
                scheduled_at=post.get("scheduled_at"),
                media_url=post.get("media_url"),
            )
            results["scheduled"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(str(e))

    return results
