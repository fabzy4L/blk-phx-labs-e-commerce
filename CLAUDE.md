# BLK PHX LABS — Claude Code Project Instructions

## Project Overview
BLK PHX LABS is a science-backed cognitive performance e-commerce brand.
Founder: PhD computational biologist, CGT/AI background.
Stack is built for automation-first operations on minimal weekly time input (~100 min/week active).

## Architecture Summary
- **Storefront**: Shopify (REST + GraphQL Admin API)
- **Email/SMS**: Klaviyo (flows, segments, events)
- **Subscriptions**: Recharge
- **Fulfillment**: Supliful (Phase 1 dropship) → private label 3PL (Phase 2)
- **Quiz Funnel**: Typeform → webhook → Klaviyo
- **Data Pipeline**: Python (custom ETL — Shopify + Klaviyo + GA4 → unified store)
- **Dashboard**: Streamlit
- **AI Support Layer**: llm_client.py abstraction — Gemini 2.5 Flash free tier (Phase 1), Claude Haiku 4.5 (Phase 2+). Swap via LLM_PROVIDER in .env.
- **Content Scheduling**: Buffer API
- **Automation**: Python scripts + cron jobs

## Project Structure
- `src/store/` — Shopify API clients, product sync, order management
- `src/pipeline/` — ETL jobs: revenue, conversion, retention metrics
- `src/automation/` — Klaviyo flows, email triggers, Recharge webhooks
- `src/ai/` — Claude API customer support layer, content generation helpers
- `src/dashboard/` — Streamlit dashboard: funnel analytics, cohort analysis, churn prediction
- `docs/` — Architecture decisions, API references, compliance notes
- `scripts/` — One-off setup scripts, data migrations
- `tests/` — Unit + integration tests

## Tech Stack
- Language: Python 3.11+
- Package manager: pip + requirements.txt
- API clients: httpx (async), requests (sync)
- Data: pandas, polars for transforms; SQLite local dev, Postgres prod
- Dashboard: Streamlit
- Scheduling: APScheduler or cron
- Secrets: python-dotenv (.env never committed)
- Testing: pytest

## Key Conventions
- All API keys via environment variables — never hardcoded
- Async-first for all external API calls (httpx)
- Every ETL job is idempotent — safe to re-run
- Webhooks validate signatures before processing
- All Klaviyo events use snake_case property names
- Shopify API version pinned — update deliberately, never automatically
- Error handling: log + alert, never silent failures
- Data pipeline outputs always timestamped

## Commands
- Run dashboard: `streamlit run src/dashboard/app.py`
- Run pipeline: `python src/pipeline/run.py`
- Run tests: `pytest tests/`
- Lint: `ruff check .`
- Format: `ruff format .`

## Business Rules (critical context)
- NO health claims in any generated content — FTC compliance required
- All supplement claims must reference published research by mechanism only
- Customer data: GDPR + CCPA compliant handling required
- Subscription cancellation must always be honored immediately — no dark patterns
- Churn threshold alert: fire when weekly cancellation rate exceeds 5%

## Phase Context
Currently in Phase 1 (Months 1–3): dropship validation.
Phase 2 trigger: any single product exceeds 50 units/month → flag for private label evaluation.
Phase 3 trigger: $5,000/month gross revenue sustained for 60 days.

## Do Not
- Do not use synchronous requests inside async functions
- Do not commit .env or any file containing API keys
- Do not make direct database writes from dashboard code
- Do not generate health claims or disease treatment language
- Do not use deprecated Shopify API versions
