"""
BLK PHX LABS — Test Suite
Run: pytest tests/
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


# ── PIPELINE TESTS ────────────────────────────────────────────────────────────

def test_init_db(tmp_path):
    """Database initializes without error."""
    import sqlite3
    import sys
    sys.path.insert(0, ".")

    # Patch DB_PATH to temp location
    with patch("src.pipeline.run.DB_PATH", str(tmp_path / "test.db")):
        from src.pipeline.run import init_db, get_db
        with patch("src.pipeline.run.DB_PATH", str(tmp_path / "test.db")):
            init_db()
            conn = sqlite3.connect(str(tmp_path / "test.db"))
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = [t[0] for t in tables]
            assert "orders" in table_names
            assert "customers" in table_names
            assert "daily_metrics" in table_names
            conn.close()


def test_check_phase_triggers_no_data(tmp_path):
    """Phase trigger check returns empty list with no orders."""
    with patch("src.pipeline.run.DB_PATH", str(tmp_path / "test.db")):
        from src.pipeline.run import init_db, check_phase_triggers
        init_db()
        triggers = check_phase_triggers()
        assert isinstance(triggers, list)
        assert len(triggers) == 0


# ── AI SUPPORT TESTS ──────────────────────────────────────────────────────────

def test_classify_inquiry_order():
    from src.ai.support import classify_inquiry
    assert classify_inquiry("Where is my order?") == "order"
    assert classify_inquiry("My package hasn't arrived") == "order"


def test_classify_inquiry_subscription():
    from src.ai.support import classify_inquiry
    assert classify_inquiry("I want to cancel my subscription") == "subscription"
    assert classify_inquiry("How do I skip a month?") == "subscription"


def test_classify_inquiry_product():
    from src.ai.support import classify_inquiry
    assert classify_inquiry("What ingredients are in the focus stack?") == "product"
    assert classify_inquiry("How does lion's mane work?") == "product"


def test_classify_inquiry_general():
    from src.ai.support import classify_inquiry
    assert classify_inquiry("Hi, I have a question") == "general"


def test_generate_recommendation_focus():
    from src.ai.support import generate_product_recommendation
    result = generate_product_recommendation({
        "primary_goal": "focus",
        "biggest_challenge": "distraction",
    })
    assert result["recommended_product"] == "Focus & Clarity Stack"
    assert "rationale" in result
    assert "disclaimer" in result
    assert "FDA" in result["disclaimer"]


def test_generate_recommendation_recovery():
    from src.ai.support import generate_product_recommendation
    result = generate_product_recommendation({
        "primary_goal": "recovery",
        "biggest_challenge": "fatigue",
    })
    assert result["recommended_product"] == "Cognitive Recovery Stack"


def test_no_health_claims_in_recommendation():
    """Ensure generated recommendations don't contain prohibited claim language."""
    from src.ai.support import generate_product_recommendation
    prohibited = ["treats", "cures", "prevents", "heals", "guaranteed", "will improve"]

    for goal in ["focus", "recovery", "sleep", "stress"]:
        result = generate_product_recommendation({"primary_goal": goal})
        rationale_lower = result["rationale"].lower()
        for term in prohibited:
            assert term not in rationale_lower, (
                f"Prohibited term '{term}' found in recommendation for goal '{goal}'"
            )


# ── WEBHOOK SIGNATURE TESTS ───────────────────────────────────────────────────

def test_shopify_signature_verification():
    """Valid HMAC signature passes verification."""
    import hmac as hmac_lib
    import hashlib
    import base64
    import os

    secret = "test_secret"
    body = b'{"id": 12345}'

    digest = hmac_lib.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    valid_hmac = base64.b64encode(digest).decode("utf-8")

    with patch.dict(os.environ, {"SHOPIFY_WEBHOOK_SECRET": secret}):
        from src.automation.webhooks import _verify_shopify_signature
        assert _verify_shopify_signature(body, valid_hmac) is True
        assert _verify_shopify_signature(body, "invalid_hmac") is False


def test_llm_provider_google(monkeypatch):
    """LLM_PROVIDER=google routes to Google without error."""
    monkeypatch.setenv("LLM_PROVIDER", "google")
    # Re-import to pick up env change
    import importlib
    import src.ai.llm_client as llm
    importlib.reload(llm)
    info = llm.get_provider_info()
    assert info["provider"] == "Google Gemini"
    assert info["tier"] == "free"
    assert info["cost_per_inquiry"] == "$0.00"


def test_llm_provider_anthropic(monkeypatch):
    """LLM_PROVIDER=anthropic routes to Anthropic without error."""
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    import importlib
    import src.ai.llm_client as llm
    importlib.reload(llm)
    info = llm.get_provider_info()
    assert info["provider"] == "Anthropic Claude"
    assert info["tier"] == "paid"


def test_llm_provider_invalid(monkeypatch):
    """Unknown LLM_PROVIDER raises ValueError."""
    import asyncio
    import importlib
    import src.ai.llm_client as llm
    importlib.reload(llm)

    async def run():
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            await llm.chat("system", [{"role": "user", "content": "hi"}], provider="unknown_provider")

    asyncio.run(run())


def test_typeform_answer_parsing():
    """Typeform answers parsed correctly into quiz dict."""
    from src.automation.webhooks import _parse_typeform_answers
    answers = [
        {"field": {"ref": "primary_goal"}, "type": "choice", "choice": {"label": "focus"}},
        {"field": {"ref": "biggest_challenge"}, "type": "choice", "choice": {"label": "distraction"}},
    ]
    result = _parse_typeform_answers(answers)
    assert result["primary_goal"] == "focus"
    assert result["biggest_challenge"] == "distraction"
