# BLK PHX LABS — Engineering Handoff
**Date:** 2026-06-17 (updated)
**Commit:** `e2ac45e` (main)
**Status:** Phase 1 code complete. Pending: entity formation, logo, service accounts, credentials, deployment.

---

## Session Notes — 2026-06-17

### Broader context (from BLK_PHX_BUILD_PLAN_v2.md)
This repo is one of three tracks under **BLK PHX, INC.** (Delaware C-Corp — pending formation):
- **Track 1:** Entity formation (registered agent → C-Corp → EIN → Mercury bank → Bylaws/shares)
- **Track 2:** Web presence — `blkphx.com` (Framer), `labops.ai` (React + Vercel), this e-commerce store
- **Track 3:** This repo — e-commerce backend, pending service accounts + deploy

Reference `BLK_PHX_BUILD_PLAN_v2.md` for full timeline, costs, and corporate structure.

### Decisions made
- **C-Corp confirmed** over LLC. Rationale: LabOps.AI will likely need institutional/VC capital (LLC is a non-starter for that), QSBS Section 1202 protects up to $10M in gains on exit, and the holdco + subsidiaries structure requires it. Double taxation is not a meaningful concern at this stage.
- **Entity formation is the prerequisite** for everything else — do not open service accounts or sign contracts under a personal name if avoidable.

### Current status by workstream
| Workstream | Status |
|---|---|
| Phase 1 backend code | ✅ Complete (`e2ac45e`) |
| Logo | 🔄 In progress (on founder's laptop) |
| Entity formation (C-Corp) | ⬜ Not started |
| Domains (blkphx.com, blkphxlabs.com, labops.ai) | ⬜ Not started |
| Service accounts (Shopify, Klaviyo, Recharge, etc.) | ⬜ Not started — no accounts yet |
| `.env` credentials | ⬜ Blocked on service accounts |
| Railway deployment | ⬜ Blocked on credentials |
| blkphx.com (Framer) | ⬜ Not started |
| labops.ai (React + Vercel) | ⬜ Not started |

### Known code gap
`recharge_client.py` is listed in the repo layout below but **does not exist** in `src/automation/`. Recharge webhook handlers are in `webhooks.py` but the dedicated sync client module was never created. Flag this before any Recharge integration work.

### Recommended next actions (in order)
1. Grab domains immediately (before or alongside entity filing — check availability first)
2. File Delaware C-Corp + get EIN + open Mercury account
3. Sign Bylaws + issue founder shares → **83(b) election within 30 days**
4. Open service accounts once entity is formed
5. Fill `.env`, deploy to Railway, register webhooks

---

## What This Is

Automation-first e-commerce backend for BLK PHX LABS — a science-backed cognitive performance supplement brand. Designed for ~100 min/week active management once live integrations are wired up.

Stack: Shopify (storefront) → FastAPI webhooks → Klaviyo (email/SMS) → Supliful (dropship fulfillment) → SQLite/Postgres (metrics) → Streamlit (dashboard). LLM layer routes to Gemini free tier (Phase 1) or Claude Haiku (Phase 2+).

---

## Repository Layout

```
blk-phx-labs-e-commerce/
├── CLAUDE.md                          # Project instructions — read every session
├── HANDOFF.md                         # This document
├── .env.example                       # Environment variable template
├── requirements.txt
├── src/
│   ├── store/
│   │   ├── shopify_client.py          # Shopify REST API: orders, customers, webhook HMAC
│   │   ├── supliful_client.py         # Dropship order submission + fulfillment status
│   │   └── ga4_client.py              # GA4 traffic sources, funnel metrics, top pages
│   ├── automation/
│   │   ├── klaviyo_client.py          # Event tracking, profile upsert, list management
│   │   ├── webhooks.py                # FastAPI webhook server (Shopify/Typeform/Recharge)
│   │   ├── buffer_client.py           # Social post scheduling via Buffer API
│   │   └── recharge_client.py         # Recharge subscription sync [FILE MISSING — not yet created]
│   ├── pipeline/
│   │   └── run.py                     # ETL + cohort metrics + churn detection + phase triggers
│   ├── scheduler.py                   # APScheduler: daily pipeline + weekly content jobs
│   ├── ai/
│   │   ├── llm_client.py              # Provider-agnostic LLM abstraction (Gemini / Claude)
│   │   ├── support.py                 # Customer support + quiz product recommendation
│   │   └── content.py                 # FTC-compliant social posts, email subjects, blurbs
│   └── dashboard/
│       └── app.py                     # Streamlit: revenue, cohort heatmap, subscription health
├── scripts/
│   └── setup_webhooks.py              # One-time: register webhooks with all three platforms
└── tests/
    └── test_core.py                   # 33 tests (30 pass locally; 3 need apscheduler installed)
```

---

## Database

SQLite locally (`blkphx.db`). Set `DATABASE_URL=postgresql://...` for prod. Schema auto-created on first `run_pipeline()` call.

| Table | Purpose |
|---|---|
| `orders` | Shopify paid orders |
| `customers` | Shopify customer records |
| `daily_metrics` | Revenue, AOV, new customers, email list size |
| `cohort_metrics` | Monthly cohort retention rates + cumulative LTV |
| `subscription_events` | Recharge lifecycle events (start / cancel) |
| `fulfillment_jobs` | Supliful submission status per Shopify order |

---

## Automated Event Map

| Trigger | Webhook | Klaviyo Event | Downstream |
|---|---|---|---|
| Order paid | `POST /webhooks/shopify/orders-paid` | `product_purchased` | Post-purchase flow + auto-fulfillment |
| New customer | `POST /webhooks/shopify/customers-create` | *(profile upsert + list add)* | Welcome sequence |
| Quiz completed | `POST /webhooks/typeform/quiz` | `quiz_completed` | Product recommendation flow |
| Subscription started | `POST /webhooks/recharge/subscription-activated` | `subscription_started` | Onboarding sequence |
| Subscription cancelled | `POST /webhooks/recharge/subscription-cancelled` | `subscription_cancelled` | Win-back flow |

---

## Auto-Fulfillment

On `orders/paid`, the webhook fires `_auto_fulfill_order()` as a FastAPI `BackgroundTask` (non-blocking — Shopify gets 200 immediately, Supliful call happens after).

- **Mapping:** `SUPLIFUL_VARIANT_MAP` env var — JSON string of `{"SHOPIFY_SKU": "supliful_variant_id"}`. Get variant IDs from Supliful dashboard → Products.
- **Idempotency:** checks `fulfillment_jobs` table before calling Supliful. Orders already marked `submitted` are skipped.
- **No mapping:** logs `no_mapping` status and skips — requires manual fulfillment. Check Supliful dashboard.
- **Disabled:** leave `SUPLIFUL_VARIANT_MAP={}` until variant IDs are confirmed.

---

## Scheduler

`python src/scheduler.py` runs two jobs:

| Job | Default schedule | What it does |
|---|---|---|
| `run_pipeline_job` | Daily at 06:00 UTC | Syncs orders/customers, computes metrics, detects churn, checks phase triggers |
| `run_content_job` | Mondays at 07:00 UTC | Generates weekly social content plan via `content.py`, schedules to Buffer |

Override via env vars: `PIPELINE_SCHEDULE_HOUR`, `PIPELINE_SCHEDULE_MINUTE`, `CONTENT_SCHEDULE_DAY`, `CONTENT_SCHEDULE_HOUR`, `CONTENT_SCHEDULE_ENABLED`.

---

## Phase Triggers

The pipeline checks these on every run and logs `WARNING` when hit.

| Trigger | Condition | Required action |
|---|---|---|
| Phase 2 | Any product >50 units/month | Evaluate private label, source 3PL, update `SUPLIFUL_VARIANT_MAP` |
| Phase 3 | $5k/month gross sustained 60 days | Custom formulation, expand SKUs, switch to paid LLM tier |
| Churn alert | Weekly cancel rate >5% | Review Klaviyo win-back flow, investigate product feedback |

Set up log monitoring or email alerts on the strings `PHASE 2 TRIGGER` and `CHURN ALERT`.

---

## LLM Provider

`src/ai/llm_client.py` abstracts provider — swap via `.env`, zero code changes.

| Phase | Provider | Setting | Cost |
|---|---|---|---|
| Phase 1 | Gemini 2.5 Flash | `LLM_PROVIDER=google` | $0 (1,500 req/day) |
| Phase 2+ | Claude Haiku 4.5 | `LLM_PROVIDER=anthropic` | ~$0.001/call |

---

## Compliance (non-negotiable)

All content generation enforces FTC/FDA rules in code via `_check_compliance()` in `src/ai/content.py`.

- No health claims: no "treats," "cures," "prevents," "heals," "guaranteed"
- Mechanism-only language: "studied for," "research suggests," "may support"
- FDA disclaimer required on all product-facing content
- These rules are also enforced in the LLM system prompts and tested in `tests/test_core.py`

---

## Deploy Checklist

### 1. Fill `.env`

```
SHOPIFY_STORE_URL=https://your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...
SHOPIFY_WEBHOOK_SECRET=    # generated by Shopify when you register webhooks
KLAVIYO_PRIVATE_API_KEY=pk_...
KLAVIYO_LIST_ID_MAIN=
RECHARGE_ACCESS_TOKEN=
RECHARGE_WEBHOOK_SECRET=
TYPEFORM_API_TOKEN=
TYPEFORM_QUIZ_FORM_ID=
TYPEFORM_WEBHOOK_SECRET=
SUPLIFUL_API_KEY=
SUPLIFUL_VARIANT_MAP={"YOUR-SKU": "supliful_variant_id"}
GOOGLE_AI_STUDIO_API_KEY=
WEBHOOK_BASE_URL=https://your-deployed-url.com
BUFFER_ACCESS_TOKEN=
BUFFER_PROFILE_IDS_TIKTOK=
BUFFER_PROFILE_IDS_INSTAGRAM=
BUFFER_PROFILE_IDS_LINKEDIN=
GA4_PROPERTY_ID=
```

### 2. Deploy the webhook server

The server must be publicly reachable over HTTPS. Easiest options:
- **Railway:** connect this repo, set env vars, deploy. Public URL auto-assigned.
- **Fly.io:** `fly launch` from repo root.
- **Local dev only:** `ngrok http 8000` → paste the `https://` URL into `WEBHOOK_BASE_URL`.

Set `WEBHOOK_BASE_URL` to whatever URL you get.

### 3. Register webhooks (automated)

```bash
python scripts/setup_webhooks.py --dry-run   # preview first
python scripts/setup_webhooks.py             # register
python scripts/setup_webhooks.py --list      # verify

# If URL changes (e.g., new deployment):
python scripts/setup_webhooks.py --clean
```

This registers with Shopify, Typeform, and Recharge via their APIs in one command. Copy `SHOPIFY_WEBHOOK_SECRET` from Shopify admin after registration.

### 4. Start services

```bash
# Initialize DB + first sync
python src/pipeline/run.py

# Webhook server (keep running — use a process manager or platform worker)
uvicorn src.automation.webhooks:app --host 0.0.0.0 --port 8000

# Scheduler (blocks — run as a separate worker)
python src/scheduler.py

# Dashboard
streamlit run src/dashboard/app.py
```

---

## Running Tests

```bash
pytest tests/                 # 30/33 pass locally (3 need apscheduler installed)
pip install apscheduler        # then all 33 pass
ruff check .
ruff format .
```

---

## Platform Config Still Required (not code)

These must be set up in each platform's UI — the code handles the automation after they exist:

- **Klaviyo flows:** welcome series, post-purchase, win-back, quiz recommendation — create in Klaviyo UI, triggered by the events this stack fires
- **Recharge subscription plans** — pricing, billing cadence in Recharge dashboard
- **Shopify products + checkout** — catalog, pricing, payment gateway in Shopify admin
- **Buffer social profiles** — connect TikTok/Instagram/LinkedIn in Buffer; paste profile IDs into `.env`
- **GA4 property + service account** — create in Google Cloud Console; download JSON key to `credentials/ga4-service-account.json`
