# BLK PHX LABS — Engineering Handoff

**Date:** 2026-06-12  
**Phase:** 1 — Dropship Validation  
**Stack status:** Complete, tested, ready for API key configuration

---

## What Is This

Automation-first e-commerce backend for BLK PHX LABS, a science-backed cognitive performance supplement brand. Designed for ~100 min/week active management once live integrations are wired up.

---

## Repository Layout

```
blk-phx-labs-e-commerce/
├── CLAUDE.md                        # Claude Code session instructions (read every session)
├── HANDOFF.md                       # This document
├── README.md                        # Setup quickstart
├── .env.example                     # Environment variable template
├── .env                             # Local secrets — never committed
├── requirements.txt                 # Python dependencies (pip)
├── .claude/commands/                # Custom Claude Code slash commands
│   ├── run-pipeline.md              # /run-pipeline
│   ├── add-flow.md                  # /add-flow
│   └── compliance-check.md         # /compliance-check
└── src/
    ├── store/shopify_client.py      # Shopify REST API — orders, products, customers
    ├── automation/
    │   ├── klaviyo_client.py        # Klaviyo event tracking + profile management
    │   └── webhooks.py              # FastAPI server — Shopify/Typeform/Recharge events
    ├── pipeline/run.py              # ETL: Shopify + Klaviyo → SQLite, phase triggers
    ├── ai/
    │   ├── llm_client.py            # Provider-agnostic LLM abstraction
    │   └── support.py               # AI customer support + quiz recommendation engine
    └── dashboard/app.py             # Streamlit analytics dashboard
```

---

## Environment Setup (completed)

The following has already been done in this session:

- [x] Files extracted and moved to repo root
- [x] Virtual environment created at `.venv/`
- [x] All dependencies installed (Python 3.13-compatible versions)
- [x] `.env` created from `.env.example`
- [x] Test suite: **14/14 passing**

Dependency versions updated from original for Python 3.13 compatibility:

| Package | Original | Updated |
|---|---|---|
| `numpy` | 1.26.4 | 2.1.3 |
| `pandas` | 2.2.2 | 2.2.3 |
| `polars` | 0.20.31 | 1.0.0 |
| `pydantic` | 2.7.1 | 2.10.6 |
| `pydantic-settings` | 2.3.1 | 2.7.0 |
| `streamlit` | 1.35.0 | 1.41.0 |
| `anthropic` | 0.28.0 | >=0.40.0 |

---

## Before Going Live — Checklist

### 1. Fill in `.env`

Minimum viable for Phase 1:

```bash
# Required — data pipeline + webhooks
SHOPIFY_STORE_URL=https://your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...
SHOPIFY_WEBHOOK_SECRET=<generated when registering webhooks>

# Required — email automation
KLAVIYO_PRIVATE_API_KEY=pk_...
KLAVIYO_LIST_ID_MAIN=<list ID from Klaviyo>

# Required — AI support layer (free tier, Phase 1)
GOOGLE_AI_STUDIO_API_KEY=<from aistudio.google.com/apikey>

# Optional — Phase 2+ only
ANTHROPIC_API_KEY=sk-ant-...
RECHARGE_ACCESS_TOKEN=...
TYPEFORM_API_TOKEN=...
BUFFER_ACCESS_TOKEN=...
```

### 2. Register Shopify Webhooks

In Shopify Admin → Settings → Notifications → Webhooks, point these at your server:

| Event | Endpoint |
|---|---|
| Order payment | `POST /webhooks/shopify/orders-paid` |
| Customer creation | `POST /webhooks/shopify/customers-create` |

Copy the signing secret into `SHOPIFY_WEBHOOK_SECRET` in `.env`.

### 3. Register Typeform Webhook

In Typeform → quiz form → Connect → Webhooks → point to `POST /webhooks/typeform/quiz`  
Set `TYPEFORM_WEBHOOK_SECRET` in `.env`.

### 4. Register Recharge Webhooks

In Recharge → Settings → Notifications → Webhooks:

| Event | Endpoint |
|---|---|
| Subscription activated | `POST /webhooks/recharge/subscription-activated` |
| Subscription cancelled | `POST /webhooks/recharge/subscription-cancelled` |

### 5. Start the Services

```bash
# Activate venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux

# Initialize DB + first data sync
python src/pipeline/run.py

# Start webhook server (keep running — use a process manager in prod)
uvicorn src.automation.webhooks:app --host 0.0.0.0 --port 8000

# Launch dashboard
streamlit run src/dashboard/app.py
```

---

## LLM Provider Strategy

The AI layer (`src/ai/llm_client.py`) abstracts over providers — swap via `.env`, zero code changes.

| Phase | Provider | Config | Cost |
|---|---|---|---|
| Phase 1 | Google Gemini 2.5 Flash | `LLM_PROVIDER=google` | $0 (1,500 req/day free) |
| Phase 2+ | Claude Haiku 4.5 | `LLM_PROVIDER=anthropic` | ~$0.001/inquiry with caching |

The system prompt is cached on the Anthropic path — 90% token cost reduction on repeated calls.

---

## Automated Event Map

| Trigger | Source | Klaviyo Event | Flow |
|---|---|---|---|
| Order paid | Shopify webhook | `product_purchased` | Post-purchase education |
| New customer | Shopify webhook | *(profile upsert + list add)* | Welcome sequence |
| Quiz completed | Typeform webhook | `quiz_completed` | Product recommendation |
| Subscription started | Recharge webhook | `subscription_started` | Onboarding sequence |
| Subscription cancelled | Recharge webhook | `subscription_cancelled` | Win-back flow |

---

## Phase Triggers (auto-detected by pipeline)

The pipeline checks these on every run and logs warnings when hit:

| Trigger | Condition | Action |
|---|---|---|
| Phase 2 | Any product > 50 units/month | Flag for private label evaluation |
| Phase 3 | $5,000/month gross sustained 60 days | Custom formulation + paid acquisition |

Dashboard shows live phase progress under "Phase Status."

---

## Claude Code Slash Commands

These are wired into `.claude/commands/` and available in any Claude Code session:

- `/run-pipeline` — sync Shopify data, compute metrics, check phase triggers
- `/add-flow` — scaffold a new Klaviyo automation flow with brand-voice email copy
- `/compliance-check` — scan codebase for FTC/FDA violations before content deploy

---

## Compliance Rules (non-negotiable)

- **No health claims** — no "treats," "cures," "prevents," "heals," "guaranteed"
- **Mechanism-only language** — "studied for," "research suggests," "may support"
- **FDA disclaimer required** on all product-facing content: *"These statements have not been evaluated by the FDA. This product is not intended to diagnose, treat, cure, or prevent any disease."*
- Run `/compliance-check` before any content deployment

These rules are enforced in `src/ai/support.py` (LLM system prompt) and tested in `tests/test_core.py`.

---

## Known Issues / Notes

- `python_multipart` deprecation warning from Starlette — cosmetic, does not affect functionality
- Shopify API version pinned to `2025-01` in `.env.example` — update deliberately, never automatically
- `polars` is imported in `requirements.txt` but not yet used in pipeline code — reserved for future high-performance transforms
- GA4 integration (`google-analytics-data`) is wired in `requirements.txt` but not yet implemented in the pipeline — placeholder for Phase 2 funnel analytics
