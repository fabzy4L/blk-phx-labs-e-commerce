"""
BLK PHX LABS — AI Content Generation
Generates compliant social copy, email subjects, and product descriptions.
All output is mechanism-based only — no health claims, FTC compliant.
"""

from dotenv import load_dotenv

load_dotenv()

from src.ai.llm_client import chat

_COMPLIANCE_RULES = """
STRICT CONTENT RULES (non-negotiable):
1. No health claims or disease treatment statements
2. No outcome promises: never use "will improve", "cures", "treats", "prevents", "heals"
3. Describe mechanisms, not benefits — e.g. "studied for neuroplasticity support" NOT "improves your brain"
4. Use research language: "studied for", "investigated for", "associated with in research"
5. No superlatives without research backing
6. Brand voice: Direct, intelligent, science-grounded. No hype. No fluff.
"""

_PRODUCT_INFO = """
Products:
- Focus & Clarity Stack: Lion's Mane 500mg, Bacopa 300mg, L-Theanine 200mg, Rhodiola 200mg, Alpha-GPC 150mg
- Cognitive Recovery Stack: Ashwagandha KSM-66 600mg, Magnesium L-Threonate 2g, L-Glycine 3g, Phosphatidylserine 100mg
"""

_PLATFORM_SPECS = {
    "tiktok": "Under 150 chars. Hook-first. Conversational. Hashtag-friendly.",
    "instagram": "Under 220 chars. Science credibility. Minimal emoji use.",
    "linkedin": "Under 280 chars. Professional tone. Lead with the mechanism. No emojis.",
}

_PROHIBITED_TERMS = [
    "treats", "cures", "prevents", "heals", "diagnoses",
    "guaranteed", "will improve", "will enhance", "will boost",
    "medical treatment", "disease", "disorder",
]


async def generate_social_post(
    product_name: str,
    platform: str,
    angle: str = "general",
) -> dict:
    """
    Generate a compliance-checked social post for one platform.

    Args:
        product_name: 'Focus & Clarity Stack' or 'Cognitive Recovery Stack'
        platform: 'tiktok', 'instagram', or 'linkedin'
        angle: 'general', 'ingredient_spotlight', 'routine', or 'science'

    Returns:
        {text, platform, product, angle, compliance_ok, provider}
    """
    platform_spec = _PLATFORM_SPECS.get(platform, _PLATFORM_SPECS["instagram"])

    system = f"You are a science-based copywriter for BLK PHX LABS.\n{_COMPLIANCE_RULES}\n{_PRODUCT_INFO}"
    messages = [{
        "role": "user",
        "content": (
            f"Write a {platform} post for {product_name}. "
            f"Angle: {angle}. "
            f"Platform spec: {platform_spec}. "
            f"Output only the post text."
        ),
    }]

    response = await chat(system_prompt=system, messages=messages, max_tokens=300)
    text = response.text.strip()

    return {
        "text": text,
        "platform": platform,
        "product": product_name,
        "angle": angle,
        "compliance_ok": _check_compliance(text),
        "provider": response.provider,
    }


async def generate_email_subject(
    campaign_type: str,
    product_name: str | None = None,
) -> dict:
    """
    Generate 3 A/B-testable email subject line variants.

    Args:
        campaign_type: 'welcome', 'post_purchase', 'win_back', 'newsletter', 'flash_sale'
        product_name: Optional product to feature

    Returns:
        {subjects (list of 3), campaign_type, product, compliance_ok, provider}
    """
    system = f"You are an email marketing specialist for BLK PHX LABS.\n{_COMPLIANCE_RULES}"
    product_context = f" featuring {product_name}" if product_name else ""

    messages = [{
        "role": "user",
        "content": (
            f"Write 3 subject line variants for a {campaign_type} email{product_context}. "
            f"Each under 60 characters. One per line, no numbering or labels."
        ),
    }]

    response = await chat(system_prompt=system, messages=messages, max_tokens=200)
    subjects = [s.strip() for s in response.text.strip().split("\n") if s.strip()][:3]

    return {
        "subjects": subjects,
        "campaign_type": campaign_type,
        "product": product_name,
        "compliance_ok": all(_check_compliance(s) for s in subjects),
        "provider": response.provider,
    }


async def generate_product_blurb(
    product_name: str,
    length: str = "medium",
) -> dict:
    """
    Generate a product description.

    Args:
        product_name: Product to describe
        length: 'short' (1-2 sentences), 'medium' (1 paragraph), 'long' (2-3 paragraphs)

    Returns:
        {text, product, length, compliance_ok, provider}
    """
    length_guide = {
        "short": "1-2 sentences for product cards",
        "medium": "1 paragraph (3-4 sentences) for product pages",
        "long": "2-3 paragraphs for landing pages",
    }

    system = f"You are a science-based product copywriter for BLK PHX LABS.\n{_COMPLIANCE_RULES}\n{_PRODUCT_INFO}"
    messages = [{
        "role": "user",
        "content": (
            f"Write a {length} product description for {product_name}. "
            f"Length: {length_guide.get(length, length_guide['medium'])}. "
            f"Focus on formulation rationale and who it's for. Output only the description."
        ),
    }]

    response = await chat(system_prompt=system, messages=messages, max_tokens=600)
    text = response.text.strip()

    return {
        "text": text,
        "product": product_name,
        "length": length,
        "compliance_ok": _check_compliance(text),
        "provider": response.provider,
    }


async def generate_weekly_content_plan(
    platforms: list[str] | None = None,
) -> list[dict]:
    """
    Generate a full week of social content (~7 posts across platforms).
    Returns structured list ready for buffer_client.schedule_weekly_content().
    """
    if platforms is None:
        platforms = ["instagram", "linkedin", "tiktok"]

    products = ["Focus & Clarity Stack", "Cognitive Recovery Stack"]
    angles = ["ingredient_spotlight", "routine", "science", "general"]

    posts = []
    # ~2-3 posts per platform across the week
    schedule = (platforms * 3)[:7]
    for i, platform in enumerate(schedule):
        product = products[i % len(products)]
        angle = angles[i % len(angles)]
        post = await generate_social_post(product, platform, angle)
        posts.append(post)

    return posts


def _check_compliance(text: str) -> bool:
    """Return False if text contains any FTC-prohibited claim language."""
    text_lower = text.lower()
    return not any(term in text_lower for term in _PROHIBITED_TERMS)
