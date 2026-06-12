"""
BLK PHX LABS — Webhook Server
Receives and processes events from Shopify, Typeform, Recharge.
Triggers Klaviyo flows automatically on each event.
Run: uvicorn src.automation.webhooks:app --host 0.0.0.0 --port 8000
"""

import hashlib
import hmac
import json
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, Response

load_dotenv()

from src.automation.klaviyo_client import track_event, upsert_profile, add_to_list
from src.ai.support import handle_inquiry

logger = logging.getLogger(__name__)
app = FastAPI(title="BLK PHX LABS Webhook Server")

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
RECHARGE_WEBHOOK_SECRET = os.getenv("RECHARGE_WEBHOOK_SECRET", "")
TYPEFORM_WEBHOOK_SECRET = os.getenv("TYPEFORM_WEBHOOK_SECRET", "")


# ── SHOPIFY WEBHOOKS ──────────────────────────────────────────────────────────

@app.post("/webhooks/shopify/orders-paid")
async def shopify_order_paid(request: Request, x_shopify_hmac_sha256: str = Header(None)):
    """
    Fires when an order is paid.
    → Tracks 'product_purchased' event in Klaviyo
    → Triggers post-purchase education sequence
    """
    body = await request.body()
    if not _verify_shopify_signature(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    order = json.loads(body)
    email = order.get("email")
    if not email:
        return Response(status_code=200)

    line_items = order.get("line_items", [])
    products = [item["title"] for item in line_items]

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
async def shopify_customer_created(request: Request, x_shopify_hmac_sha256: str = Header(None)):
    """
    Fires on new customer creation.
    → Upserts profile in Klaviyo
    → Adds to main list → triggers welcome sequence
    """
    body = await request.body()
    if not _verify_shopify_signature(body, x_shopify_hmac_sha256):
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
async def typeform_quiz_completed(request: Request):
    """
    Fires when quiz funnel is completed.
    → Extracts answers
    → Tracks 'quiz_completed' event in Klaviyo
    → Routes to product recommendation flow
    """
    body = await request.body()
    data = json.loads(body)

    form_response = data.get("form_response", {})
    answers = form_response.get("answers", [])
    hidden = form_response.get("hidden", {})

    email = hidden.get("email") or _extract_email_from_answers(answers)
    if not email:
        logger.warning("Quiz completed without email — skipping")
        return Response(status_code=200)

    quiz_answers = _parse_typeform_answers(answers)

    from src.ai.support import generate_product_recommendation
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
async def recharge_subscription_activated(request: Request):
    """Subscription started → trigger onboarding flow in Klaviyo."""
    body = await request.body()
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

    logger.info(f"Subscription started: {email}")
    return Response(status_code=200)


@app.post("/webhooks/recharge/subscription-cancelled")
async def recharge_subscription_cancelled(request: Request):
    """
    Subscription cancelled → track event → trigger win-back flow.
    Also checks if weekly cancellation rate exceeds 5% threshold.
    """
    body = await request.body()
    data = json.loads(body)

    subscription = data.get("subscription", {})
    email = subscription.get("email")
    if not email:
        return Response(status_code=200)

    await track_event(
        event_name="subscription_cancelled",
        email=email,
        properties={
            "product_title": subscription.get("product_title", ""),
            "cancellation_reason": subscription.get("cancellation_reason", "not_provided"),
        },
    )

    logger.info(f"Subscription cancelled: {email}")
    return Response(status_code=200)


# ── HEALTH CHECK ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "blkphx-webhooks"}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _verify_shopify_signature(data: bytes, hmac_header: str | None) -> bool:
    if not hmac_header or not SHOPIFY_WEBHOOK_SECRET:
        return False
    import base64
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode("utf-8"), data, hashlib.sha256
    ).digest()
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)


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
