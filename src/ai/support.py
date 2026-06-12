"""
BLK PHX LABS — AI Customer Support Layer
Powered by llm_client abstraction — defaults to Gemini free tier.
Switch provider anytime via LLM_PROVIDER in .env.
CRITICAL: Never makes health claims or disease treatment statements.
"""

import os
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

from src.ai.llm_client import chat, get_provider_info

SYSTEM_PROMPT = """You are the customer support assistant for BLK PHX LABS, a science-backed cognitive performance supplement brand.

BRAND VOICE: Direct, intelligent, science-grounded. No hype. No fluff. Founder has a PhD in computational biology — the brand communicates with intellectual integrity.

PRODUCTS YOU SUPPORT:
- Focus & Clarity Stack: nootropic blend for sustained cognitive performance
- Cognitive Recovery Stack: adaptogens for recovery and neuroplasticity support
- Digital guides: evidence-based cognitive optimization protocols

WHAT YOU CAN DO:
- Answer questions about ingredients and their mechanisms (cite published research, never make claims)
- Help with orders, shipping, subscriptions, returns
- Explain product usage and protocols
- Guide customers to the right product based on their goals

WHAT YOU MUST NEVER DO:
- Make health claims or disease treatment statements
- Promise specific cognitive or physical outcomes
- Diagnose any medical condition
- Recommend replacing medical treatment with supplements
- Make claims not supported by published research

ESCALATION: If a question involves medical conditions, adverse reactions, complex refund disputes, or anything you're uncertain about — respond with ESCALATE: [brief reason]. A human will follow up within 24 hours.

COMPLIANCE: Always include a brief disclaimer when discussing mechanisms: "These statements have not been evaluated by the FDA. This product is not intended to diagnose, treat, cure, or prevent any disease."

Be concise. Be precise. Respect the customer's intelligence."""


KNOWLEDGE_BASE = """
## BLK PHX LABS Product Knowledge Base

### Focus & Clarity Stack
Ingredients: Lion's Mane (500mg), Bacopa Monnieri (300mg), L-Theanine (200mg), Rhodiola Rosea (200mg), Alpha-GPC (150mg)
Mechanism notes:
- Lion's Mane: NGF synthesis support, studied for neuroplasticity
- Bacopa: Acetylcholinesterase inhibition, memory consolidation research
- L-Theanine: Alpha wave modulation, synergistic with caffeine (not included)
- Rhodiola: HPA axis modulation, studied for stress-related cognitive fatigue
- Alpha-GPC: Choline precursor, acetylcholine synthesis support

### Cognitive Recovery Stack
Ingredients: Ashwagandha KSM-66 (600mg), Magnesium L-Threonate (2g), L-Glycine (3g), Phosphatidylserine (100mg)
Mechanism notes:
- Ashwagandha KSM-66: Cortisol modulation studies, adaptogenic classification
- Magnesium L-Threonate: BBB-crossing magnesium form, synaptic plasticity research
- L-Glycine: Glycine receptor agonism, sleep architecture studies
- Phosphatidylserine: Membrane phospholipid, neuronal function research

### Shipping & Fulfillment
- Standard shipping: 5-7 business days (US)
- Orders processed within 1-2 business days
- Tracking provided via email upon shipment

### Subscriptions
- Monthly auto-renewal, cancel anytime
- Skip a month available in customer portal
- Cancel: customer portal or contact support

### Returns
- 30-day satisfaction guarantee on first order
- Opened product eligible for return within 30 days
- Process: email support with order number
"""


async def handle_inquiry(
    customer_message: str,
    conversation_history: list[dict] | None = None,
    customer_email: str | None = None,
) -> dict:
    """
    Handle a customer inquiry via active LLM provider.
    Returns response + escalation flag + provider used.
    """
    history = conversation_history or []
    messages = history + [{"role": "user", "content": customer_message}]

    full_system = f"{SYSTEM_PROMPT}\n\n{KNOWLEDGE_BASE}"
    if customer_email:
        full_system += f"\n\nCustomer email: {customer_email}"

    response = await chat(
        system_prompt=full_system,
        messages=messages,
        max_tokens=1000,
    )

    response_text = response.text

    # Check escalation signal
    escalate = response_text.startswith("ESCALATE:")
    escalation_reason = None
    if escalate:
        parts = response_text.split(":", 1)
        escalation_reason = parts[1].strip() if len(parts) > 1 else "Escalation requested"
        response_text = "Thank you for reaching out. I'm connecting you with our team for personalized assistance. You'll hear back within 24 hours."

    category = classify_inquiry(customer_message)

    return {
        "response": response_text,
        "escalate": escalate,
        "escalation_reason": escalation_reason,
        "category": category,
        "provider": response.provider,
        "tokens_used": response.input_tokens + response.output_tokens,
    }


def classify_inquiry(message: str) -> Literal["order", "product", "subscription", "general"]:
    """Keyword classification for routing and analytics."""
    message_lower = message.lower()
    if any(w in message_lower for w in ["order", "shipping", "track", "delivery", "arrived"]):
        return "order"
    if any(w in message_lower for w in ["subscribe", "subscription", "cancel", "skip", "billing", "charge"]):
        return "subscription"
    if any(w in message_lower for w in ["ingredient", "dose", "stack", "product", "take", "work", "effect"]):
        return "product"
    return "general"


def generate_product_recommendation(quiz_answers: dict) -> dict:
    """
    Generate personalized product recommendation from quiz funnel answers.
    Pure logic — no LLM call needed, no API cost.
    """
    primary_goal = quiz_answers.get("primary_goal", "focus")
    biggest_challenge = quiz_answers.get("biggest_challenge", "distraction")

    if primary_goal in ("focus", "creativity") or biggest_challenge in ("distraction", "motivation"):
        product = "Focus & Clarity Stack"
        rationale = (
            "Based on your goal of enhanced focus, the Focus & Clarity Stack addresses "
            "attention and cognitive stamina through multiple complementary mechanisms. "
            "Lion's Mane and Bacopa work on neuroplasticity and memory consolidation, "
            "while L-Theanine and Rhodiola support calm, sustained attention without stimulant dependency."
        )
    else:
        product = "Cognitive Recovery Stack"
        rationale = (
            "Based on your goals around recovery and stress resilience, the Cognitive Recovery Stack "
            "addresses the HPA axis and sleep architecture — the foundation of cognitive performance. "
            "KSM-66 Ashwagandha and Magnesium L-Threonate target the recovery side of the equation."
        )

    return {
        "recommended_product": product,
        "rationale": rationale,
        "disclaimer": "These statements have not been evaluated by the FDA. This product is not intended to diagnose, treat, cure, or prevent any disease.",
        "quiz_answers": quiz_answers,
    }
