"""
BLK PHX LABS — Test Suite
Run: pytest tests/
"""

import asyncio
import json
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch


# ── PIPELINE TESTS ────────────────────────────────────────────────────────────

def test_init_db(tmp_path):
    """Database initializes with all required tables."""
    with patch("src.pipeline.run.DB_PATH", str(tmp_path / "test.db")):
        from src.pipeline.run import init_db
        init_db()
        conn = sqlite3.connect(str(tmp_path / "test.db"))
        tables = {t[0] for t in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "orders" in tables
        assert "customers" in tables
        assert "daily_metrics" in tables
        assert "cohort_metrics" in tables
        assert "subscription_events" in tables


def test_check_phase_triggers_no_data(tmp_path):
    """Phase trigger check returns empty list with no orders."""
    with patch("src.pipeline.run.DB_PATH", str(tmp_path / "test.db")):
        from src.pipeline.run import init_db, check_phase_triggers
        init_db()
        triggers = check_phase_triggers()
        assert isinstance(triggers, list)
        assert len(triggers) == 0


def test_check_phase_triggers_fires(tmp_path):
    """Phase 2 trigger fires when a product exceeds 50 units/month."""
    db_path = str(tmp_path / "test.db")
    with patch("src.pipeline.run.DB_PATH", db_path):
        from src.pipeline.run import init_db, check_phase_triggers
        init_db()

        conn = sqlite3.connect(db_path)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        line_items = json.dumps([{"product_id": "999", "quantity": 55}])
        conn.execute(
            "INSERT INTO orders (id, created_at, total_price, customer_email, financial_status, fulfillment_status, line_items, synced_at) VALUES (?,?,?,?,?,?,?,?)",
            ("o1", now, 99.0, "test@test.com", "paid", "fulfilled", line_items, now),
        )
        conn.commit()
        conn.close()

        triggers = check_phase_triggers()
        assert len(triggers) == 1
        assert triggers[0]["trigger"] == "phase_2"
        assert triggers[0]["product_id"] == "999"


def test_check_weekly_churn_rate_below_threshold(tmp_path):
    """Churn rate below threshold does not alert."""
    db_path = str(tmp_path / "test.db")
    with patch("src.pipeline.run.DB_PATH", db_path):
        from src.pipeline.run import init_db, check_weekly_churn_rate
        init_db()

        conn = sqlite3.connect(db_path)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        for i in range(100):
            conn.execute(
                "INSERT INTO subscription_events (event_type, email, product_title, cancellation_reason, occurred_at) VALUES (?,?,?,?,?)",
                ("subscription_started", f"user{i}@test.com", "Focus Stack", "", now),
            )
        conn.execute(
            "INSERT INTO subscription_events (event_type, email, product_title, cancellation_reason, occurred_at) VALUES (?,?,?,?,?)",
            ("subscription_cancelled", "user0@test.com", "Focus Stack", "too_expensive", now),
        )
        conn.commit()
        conn.close()

        result = check_weekly_churn_rate()
        assert result["alert"] is False
        assert result["cancellations_this_week"] == 1
        assert result["total_subscribers"] == 100


def test_check_weekly_churn_rate_above_threshold(tmp_path):
    """Churn rate above 5% triggers alert."""
    db_path = str(tmp_path / "test.db")
    with patch("src.pipeline.run.DB_PATH", db_path):
        from src.pipeline.run import init_db, check_weekly_churn_rate
        init_db()

        conn = sqlite3.connect(db_path)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        for i in range(10):
            conn.execute(
                "INSERT INTO subscription_events (event_type, email, product_title, cancellation_reason, occurred_at) VALUES (?,?,?,?,?)",
                ("subscription_started", f"user{i}@test.com", "Focus Stack", "", now),
            )
        for i in range(2):
            conn.execute(
                "INSERT INTO subscription_events (event_type, email, product_title, cancellation_reason, occurred_at) VALUES (?,?,?,?,?)",
                ("subscription_cancelled", f"user{i}@test.com", "Focus Stack", "no_results", now),
            )
        conn.commit()
        conn.close()

        result = check_weekly_churn_rate()
        assert result["alert"] is True
        assert result["weekly_churn_rate"] == 0.2


def test_compute_cohort_metrics(tmp_path):
    """Cohort metrics computed correctly from order data."""
    db_path = str(tmp_path / "test.db")
    with patch("src.pipeline.run.DB_PATH", db_path):
        from src.pipeline.run import init_db, compute_cohort_metrics
        init_db()

        conn = sqlite3.connect(db_path)
        orders = [
            ("o1", "2025-01-05T10:00:00+00:00", 50.0, "a@test.com", "paid", "", "[]", ""),
            ("o2", "2025-02-10T10:00:00+00:00", 60.0, "a@test.com", "paid", "", "[]", ""),
            ("o3", "2025-01-08T10:00:00+00:00", 40.0, "b@test.com", "paid", "", "[]", ""),
        ]
        conn.executemany(
            "INSERT INTO orders (id, created_at, total_price, customer_email, financial_status, fulfillment_status, line_items, synced_at) VALUES (?,?,?,?,?,?,?,?)",
            orders,
        )
        conn.commit()
        conn.close()

        compute_cohort_metrics()

        conn = sqlite3.connect(db_path)
        rows = conn.execute("SELECT * FROM cohort_metrics").fetchall()
        conn.close()

        assert len(rows) > 0
        cohort_months = {r[0] for r in rows}
        assert "2025-01" in cohort_months


def test_detect_churn_risks_no_inactive(tmp_path):
    """No churn risks flagged when all customers ordered recently."""
    db_path = str(tmp_path / "test.db")
    with patch("src.pipeline.run.DB_PATH", db_path):
        from src.pipeline.run import init_db, detect_churn_risks
        init_db()

        conn = sqlite3.connect(db_path)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO orders (id, created_at, total_price, customer_email, financial_status, fulfillment_status, line_items, synced_at) VALUES (?,?,?,?,?,?,?,?)",
            ("o1", now, 50.0, "active@test.com", "paid", "", "[]", now),
        )
        conn.commit()
        conn.close()

        async def run():
            with patch("src.pipeline.run.track_event", new_callable=AsyncMock):
                return await detect_churn_risks(days_inactive=45)

        result = asyncio.run(run())
        assert result == []


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
    assert "FDA" in result["disclaimer"]


def test_generate_recommendation_recovery():
    from src.ai.support import generate_product_recommendation
    result = generate_product_recommendation({
        "primary_goal": "recovery",
        "biggest_challenge": "fatigue",
    })
    assert result["recommended_product"] == "Cognitive Recovery Stack"


def test_no_health_claims_in_recommendation():
    """Generated recommendations must not contain prohibited claim language."""
    from src.ai.support import generate_product_recommendation
    prohibited = ["treats", "cures", "prevents", "heals", "guaranteed", "will improve"]

    for goal in ["focus", "recovery", "sleep", "stress"]:
        result = generate_product_recommendation({"primary_goal": goal})
        rationale_lower = result["rationale"].lower()
        for term in prohibited:
            assert term not in rationale_lower, (
                f"Prohibited term '{term}' found in recommendation for goal '{goal}'"
            )


# ── CONTENT GENERATION COMPLIANCE ────────────────────────────────────────────

def test_content_compliance_check_clean():
    from src.ai.content import _check_compliance
    assert _check_compliance("Studied for neuroplasticity support via NGF synthesis.") is True
    assert _check_compliance("Investigated for cortisol modulation in stress research.") is True


def test_content_compliance_check_blocked():
    from src.ai.content import _check_compliance
    assert _check_compliance("This product treats anxiety and prevents cognitive decline.") is False
    assert _check_compliance("Guaranteed to improve your focus.") is False
    assert _check_compliance("Cures brain fog.") is False


# ── WEBHOOK SIGNATURE TESTS ───────────────────────────────────────────────────

def test_shopify_signature_verification():
    """Valid Shopify HMAC signature passes; invalid fails."""
    import base64
    import hashlib
    import hmac as hmac_lib

    secret = "test_secret"
    body = b'{"id": 12345}'
    digest = hmac_lib.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    valid_hmac = base64.b64encode(digest).decode("utf-8")

    # Patch the already-imported module-level constant directly
    with patch("src.store.shopify_client.SHOPIFY_WEBHOOK_SECRET", secret):
        from src.store.shopify_client import verify_webhook_signature
        assert verify_webhook_signature(body, valid_hmac) is True
        assert verify_webhook_signature(body, "invalid_hmac") is False


def test_typeform_signature_verification():
    """Valid Typeform HMAC signature passes; invalid fails."""
    import base64
    import hashlib
    import hmac as hmac_lib

    secret = "tf_secret"
    body = b'{"form_response": {}}'
    digest = hmac_lib.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    valid_sig = "sha256=" + base64.b64encode(digest).decode("utf-8")

    with patch("src.automation.webhooks.TYPEFORM_WEBHOOK_SECRET", secret):
        from src.automation.webhooks import _verify_typeform_signature
        assert _verify_typeform_signature(body, valid_sig) is True
        assert _verify_typeform_signature(body, "sha256=invalid") is False
        assert _verify_typeform_signature(body, None) is False


def test_recharge_signature_verification():
    """Valid Recharge HMAC (hex) signature passes; invalid fails."""
    import hashlib
    import hmac as hmac_lib

    secret = "rc_secret"
    body = b'{"subscription": {}}'
    valid_hmac = hmac_lib.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    with patch("src.automation.webhooks.RECHARGE_WEBHOOK_SECRET", secret):
        from src.automation.webhooks import _verify_recharge_signature
        assert _verify_recharge_signature(body, valid_hmac) is True
        assert _verify_recharge_signature(body, "deadbeef") is False
        assert _verify_recharge_signature(body, None) is False


# ── LLM PROVIDER ROUTING TESTS ───────────────────────────────────────────────

def test_llm_provider_google(monkeypatch):
    """LLM_PROVIDER=google routes to Google."""
    monkeypatch.setenv("LLM_PROVIDER", "google")
    import importlib
    import src.ai.llm_client as llm
    importlib.reload(llm)
    info = llm.get_provider_info()
    assert info["provider"] == "Google Gemini"
    assert info["tier"] == "free"
    assert info["cost_per_inquiry"] == "$0.00"


def test_llm_provider_anthropic(monkeypatch):
    """LLM_PROVIDER=anthropic routes to Anthropic."""
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    import importlib
    import src.ai.llm_client as llm
    importlib.reload(llm)
    info = llm.get_provider_info()
    assert info["provider"] == "Anthropic Claude"
    assert info["tier"] == "paid"


def test_llm_provider_invalid(monkeypatch):
    """Unknown LLM_PROVIDER raises ValueError."""
    import importlib
    import src.ai.llm_client as llm
    importlib.reload(llm)

    async def run():
        import pytest
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            await llm.chat("system", [{"role": "user", "content": "hi"}], provider="unknown_provider")

    asyncio.run(run())


# ── TYPEFORM ANSWER PARSING ───────────────────────────────────────────────────

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


def test_typeform_email_extraction():
    """Email extracted from Typeform answer when not in hidden fields."""
    from src.automation.webhooks import _extract_email_from_answers
    answers = [
        {"type": "text", "text": "some text"},
        {"type": "email", "email": "user@example.com"},
    ]
    assert _extract_email_from_answers(answers) == "user@example.com"
    assert _extract_email_from_answers([{"type": "text", "text": "no email"}]) is None


# ── SHOPIFY CLIENT TESTS ──────────────────────────────────────────────────────

def test_get_revenue_summary_passes_date_bounds():
    """get_revenue_summary passes both created_at_min and created_at_max to get_orders."""
    captured = {}

    async def mock_get_orders(**kwargs):
        captured.update(kwargs)
        return []

    async def run():
        with patch("src.store.shopify_client.get_orders", side_effect=mock_get_orders):
            from src.store.shopify_client import get_revenue_summary
            await get_revenue_summary("2025-01-01T00:00:00Z", "2025-01-31T23:59:59Z")

    asyncio.run(run())
    assert captured.get("created_at_min") == "2025-01-01T00:00:00Z"
    assert captured.get("created_at_max") == "2025-01-31T23:59:59Z"
