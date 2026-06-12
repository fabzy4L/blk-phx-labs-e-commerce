"""
BLK PHX LABS — Webhook Server
Receives and processes events from Shopify, Typeform, Recharge.
Triggers Klaviyo flows automatically on each event.
Run: uvicorn src.automation.webhooks:app --host 0.0.0.0 --port 8000
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, Response

load_dotenv()

from src.store.shopify_client import verify_webhook_signature
from src.automation.klaviyo_client import track_event, upsert_profile, add_to_list
from src.ai.support import handle_inquiry, generate_product_recommendation

logger = logging.getLogger(__name__)
app = FastAPI(title="BLK PHX LABS Webhook Server")

RECHARGE_WEBHOOK_SECRET = os.getenv("RECHARGE_WEBHOOK_SECRET", "")
TYPEFORM_WEBHOOK_SECRET = os.getenv("TYPEFORM_WEBHOOK_SECRET", "")
DB_PATH = "blkphx.db"


# ── SHOPIFY WEBHOOKS ──────────────────────────────────────────────────────────

@app.post("/webhooks/shopify/orders-paid")
async def shopify_order_paid(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
):
    """
    Fires when an order is paid.
    → Tracks 'product_purchased' event in Klaviyo
    → Triggers post-purchase education sequence
    """
    body = await request.body()
    if not x_shopify_hmac_sha256 or not verify_webhook_signature(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    order = json.loads(body)
    email = order.get("email")
    if not email:
        return Response(status_code=200)

    products = [item["title"] for item in order.get("line_items", [])]

    await track_event(
        event_name="product_purchased",
        email=email,
        properties={
            "order_id": str(order["id"]),
            "total_price": float(order["total_price"]),
            "products": products,
            "order_number": order.get("order_number"),
        },
        profile_properties={
            "first_name": order.get("billing_address", {}).get("first_name", ""),
            "last_name": order.get("billing_address", {}).get("last_name", ""),
        },
    )

    logger.info(f"Order paid: {order['id']} — {email}")
    return Response(status_code=200)


@app.post("/webhooks/shopify/customers-create")
async def shopify_customer_created(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
):
    """
    Fires on new customer creation.
    → Upserts profile in Klaviyo
    → Adds to main list → triggers welcome sequence
    """
    body = await request.body()
    if not x_shopify_hmac_sha256 or not verify_webhook_signature(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    customer = json.loads(body)
    email = customer.get("email")
    if not email:
        return Response(status_code=200)

    await upsert_profile(email, {
        "first_name": customer.get("first_name", ""),
        "last_name": customer.get("last_name", ""),
        "shopify_customer_id": str(customer["id"]),
    })
    await add_to_list(email)

    logger.info(f"New customer: {email}")
    return Response(status_code=200)


# ── TYPEFORM QUIZ WEBHOOK ─────────────────────────────────────────────────────

@app.post("/webhooks/typeform/quiz")
async def typeform_quiz_completed(
    request: Request,
    typeform_signature: str = Header(None),
):
    """
    Fires when quiz funnel is completed.
    → Extracts answers → tracks 'quiz_completed' event in Klaviyo
    → Routes to product recommendation flow
    """
    body = await request.body()
    if not _verify_typeform_signature(body, typeform_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(body)
    form_response = data.get("form_response", {})
    answers = form_response.get("answers", [])
    hidden = form_response.get("hidden", {})

    email = hidden.get("email") or _extract_email_from_answers(answers)
    if not email:
        logger.warning("Quiz completed without email — skipping")
        return Response(status_code=200)

    quiz_answers = _parse_typeform_answers(answers)
    recommendation = generate_product_recommendation(quiz_answers)

    await track_event(
        event_name="quiz_completed",
        email=email,
        properties={
            "quiz_answers": quiz_answers,
            "recommended_product": recommendation["recommended_product"],
            "recommendation_rationale": recommendation["rationale"],
        },
    )

    logger.info(f"Quiz completed: {email} → {recommendation['recommended_product']}")
    return Response(status_code=200)


# ── RECHARGE WEBHOOKS ─────────────────────────────────────────────────────────

@app.post("/webhooks/recharge/subscription-activated")
async def recharge_subscription_activated(
    request: Request,
    x_recharge_hmac_sha256: str = Header(None),
):
    """Subscription started → trigger onboarding flow in Klaviyo."""
    body = await request.body()
    if not _verify_recharge_signature(body, x_recharge_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(body)
    subscription = data.get("subscription", {})
    email = subscription.get("email")
    if not email:
        return Response(status_code=200)

    await track_event(
        event_name="subscription_started",
        email=email,
        properties={
            "product_title": subscription.get("product_title", ""),
            "price": subscription.get("price", ""),
            "frequency": f"{subscription.get('order_interval_frequency')} {subscription.get('order_interval_unit')}",
        },
    )

    _log_subscription_event("subscription_started", email, subscription.get("product_title", ""))
    logger.info(f"Subscription started: {email}")
    return Response(status_code=200)


@app.post("/webhooks/recharge/subscription-cancelled")
async def recharge_subscription_cancelled(
    request: Request,
    x_recharge_hmac_sha256: str = Header(None),
):
    """
    Subscription cancelled → track event → trigger win-back flow.
    Logs to local DB for weekly churn rate computation.
    """
    body = await request.body()
    if not _verify_recharge_signature(body, x_recharge_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(body)
    subscription = data.get("subscription", {})
    email = subscription.get("email")
    if not email:
        return Response(status_code=200)

    cancellation_reason = subscription.get("cancellation_reason", "not_provided")

    await track_event(
        event_name="subscription_cancelled",
        email=email,
        properties={
            "product_title": subscription.get("product_title", ""),
            "cancellation_reason": cancellation_reason,
        },
    )

    _log_subscription_event(
        "subscription_cancelled",
        email,
        subscription.get("product_title", ""),
        cancellation_reason,
    )
    logger.info(f"Subscription cancelled: {email}")
    return Response(status_code=200)


# ── HEALTH CHECK ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "blkphx-webhooks"}


# ── SIGNATURE VERIFICATION ────────────────────────────────────────────────────

def _verify_typeform_signature(data: bytes, sig_header: str | None) -> bool:
    """
    Typeform sends HMAC-SHA256 as base64 in the Typeform-Signature header.
    Format: sha256=<base64_digest>
    Confirm encoding against your Typeform webhook settings when configuring.
    """
    if not sig_header or not TYPEFORM_WEBHOOK_SECRET:
        return False
    raw_sig = sig_header.removeprefix("sha256=")
    digest = hmac.new(
        TYPEFORM_WEBHOOK_SECRET.encode("utf-8"), data, hashlib.sha256
    ).digest()
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, raw_sig)


def _verify_recharge_signature(data: bytes, hmac_header: str | None) -> bool:
    """Recharge sends HMAC-SHA256 as hexadecimal in X-Recharge-Hmac-Sha256 header."""
    if not hmac_header or not RECHARGE_WEBHOOK_SECRET:
        return False
    digest = hmac.new(
        RECHARGE_WEBHOOK_SECRET.encode("utf-8"), data, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(digest, hmac_header)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _extract_email_from_answers(answers: list[dict]) -> str | None:
    for answer in answers:
        if answer.get("type") == "email":
            return answer.get("email")
    return None


def _parse_typeform_answers(answers: list[dict]) -> dict:
    """Map Typeform answer refs to quiz_answers dict."""
    result = {}
    ref_map = {
        "primary_goal": "primary_goal",
        "when_do_you_use": "when_do_you_use",
        "caffeine_use": "current_caffeine_use",
        "biggest_challenge": "biggest_challenge",
    }
    for answer in answers:
        field_ref = answer.get("field", {}).get("ref", "")
        if field_ref in ref_map:
            choice = answer.get("choice", {})
            result[ref_map[field_ref]] = choice.get("label", choice.get("other", ""))
    return result


def _log_subscription_event(
    event_type: str,
    email: str,
    product_title: str,
    cancellation_reason: str = "",
) -> None:
    """Log subscription lifecycle event to local DB for churn rate tracking."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscription_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                email TEXT NOT NULL,
                product_title TEXT,
                cancellation_reason TEXT,
                occurred_at TEXT NOT NULL
            )
        """)
        conn.execute(
            """INSERT INTO subscription_events
               (event_type, email, product_title, cancellation_reason, occurred_at)
               VALUES (?, ?, ?, ?, ?)""",
            (event_type, email, product_title, cancellation_reason,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log subscription event: {e}")
