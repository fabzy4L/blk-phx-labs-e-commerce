# BLK PHX — Master Build Plan v2
**Company:** BLK PHX, INC. (Delaware C-Corp — pending formation)  
**Founder:** Fabian Alvarez-Primo  
**Updated:** June 17, 2026  
**Repo commit baseline:** `e2ac45e` (main) — Phase 1 code complete

---

## Corporate Structure

```
BLK PHX, INC.                    ← Delaware C-Corp (Holdco) [PENDING FORMATION]
│
├── BLK PHX LABS                 ← Subsidiary (science & biotech arm)
│   ├── LabOps.AI                ← Flagship product (AI biomanufacturing intelligence)
│   └── E-Commerce Store         ← Science-backed cognitive performance supplements
│
└── [Future ventures]            ← Open slots under parent brand
```

---

## Track 1 — Entity Formation [PENDING]

All steps below are sequential. Do not skip.

### Step 1 — Registered Agent (~10 min, free yr 1)
- Go to **northwestregisteredagent.com**
- Select Delaware → sign up
- Save the registered agent name + Delaware street address
- Cost: Free year 1, $125/yr after

### Step 2 — File Certificate of Incorporation (~20 min, $110)
- Go to **corp.delaware.gov** → File Online → Incorporate
- Entity name: `BLK PHX, INC.`
- Registered agent: use address from Step 1
- Authorized shares: `10,000,000` at `$0.0001` par value (9M Common, 1M Preferred)
- Incorporator: Fabian Alvarez-Primo, Savannah, GA
- Pay $110 filing fee by card
- **Save the stamped Certificate of Incorporation permanently**

### Step 3 — Obtain EIN (~10 min, free)
- Go to **irs.gov** → Apply for EIN Online → select "Corporation"
- Complete the form
- **Print/save the EIN confirmation letter immediately** — banks require this

### Step 4 — Open Business Bank Account (~15 min, free)
- Go to **mercury.com**
- Required: Certificate of Incorporation + EIN letter + personal ID
- Free, no minimums, founder-friendly API
- Approval: 1–3 business days

### Step 5 — Corporate Records (~30 min, free)
- Sign the Bylaws (document already generated — `BLK_PHX_Bylaws.docx`)
- Execute written organizational consent (in lieu of first Board meeting)
- Issue founder shares via Stock Purchase Agreement
  - **File 83(b) election within 30 days of share issuance** — do not miss this window
- Initialize cap table (Carta free tier or Google Sheet)

### Step 6 — Domain Registration (~10 min, ~$70–100)
- Registrar: **Namecheap** or **Cloudflare Registrar** (no markup)
- Domains to acquire:
  - `blkphx.com` — parent brand (~$10–15/yr)
  - `blkphxlabs.com` — biotech subsidiary (~$10–15/yr)
  - `labops.ai` — product site (~$50–70/yr)
- Check availability before filing anything — grab these immediately

---

## Track 2 — Web Presence

### Site 1 — blkphx.com (Parent Brand)
**Status:** Not started  
**Tool:** Framer (framer.com) — dark, motion-forward, no-code React output  
**Cost:** ~$10–15/mo  
**Audience:** Investors, partners, press, talent

#### Pages
- `/` — Hero: BLK PHX identity, tagline, mission
- `/about` — Founder story, phoenix mythology, philosophy
- `/ventures` — Portfolio cards: BLK PHX LABS, e-commerce, future
- `/contact` — Inquiry form

#### Design Direction
- Black background, fire accent (amber/orange)
- Bold grotesque headline, clean body type
- Motion-only, no stock photos

#### Steps
1. Sign up for Framer
2. Select dark/minimal base template
3. Input copy (see copywriting section below)
4. Connect `blkphx.com`
5. Publish

---

### Site 2 — labops.ai (Product Site)
**Status:** Not started  
**Tool:** React + Tailwind + Vercel (free tier) — consistent with existing dev stack  
**Audience:** CGT/biopharma operators, lab directors, investors

#### Pages
- `/` — Hero + waitlist CTA
- `/product` — Features: RAG pipeline, 21 CFR Part 11 audit trail, dashboard
- `/about` — BLK PHX LABS mission + founder credentials
- `/waitlist` — Tally.so embed (free)

#### Tech Stack
```
Frontend:    React + Tailwind CSS
Deployment:  Vercel (free tier)
Forms:       Tally.so (free)
Analytics:   Vercel Analytics or Plausible
Domain:      labops.ai → Vercel custom domain
```

#### Hero Copy (draft)
```
Headline:    Intelligence for Biomanufacturing
Sub:         LabOps.AI brings AI-native process intelligence to cell and gene 
             therapy manufacturing. 21 CFR Part 11 compliant. Built for 
             regulated environments.
CTA:         Join the Waitlist →
```

#### Claude Code Prompt
```
I am building the LabOps.AI product landing page — React + Tailwind, deployed to Vercel.
LabOps.AI is an AI-native biomanufacturing intelligence platform for cell and gene therapy.
21 CFR Part 11 compliant. Parent company: BLK PHX LABS (subsidiary of BLK PHX, INC.)
Build:
1. Hero section (headline, sub, waitlist CTA button)
2. Features section (3–4 cards: RAG pipeline, audit trail, dashboard, compliance)
3. Tally.so waitlist form embed
4. Minimal dark theme (black + blue-accent for science/tech positioning)
5. Footer with BLK PHX LABS branding
Deploy config: vercel.json with production settings
Reference: BLK_PHX_BUILD_PLAN_v2.md for full context
```

---

### Site 3 — BLK PHX E-Commerce Store
**Status:** Phase 1 code COMPLETE (`e2ac45e`) — pending credentials + deployment  
**Tool:** Shopify storefront + custom Python backend  
**Cost:** $39/mo Shopify Basic + Klaviyo + Recharge (see stack below)

#### What's Built (do not rebuild)
```
src/
├── store/
│   ├── shopify_client.py       ✅ Shopify REST API: orders, customers, webhook HMAC
│   ├── supliful_client.py      ✅ Dropship order submission + fulfillment status
│   └── ga4_client.py           ✅ GA4 traffic + funnel metrics
├── automation/
│   ├── klaviyo_client.py       ✅ Event tracking, profile upsert, list management
│   ├── webhooks.py             ✅ FastAPI webhook server
│   ├── buffer_client.py        ✅ Social scheduling via Buffer API
│   └── recharge_client.py      ✅ Recharge subscription sync
├── pipeline/
│   └── run.py                  ✅ ETL + cohort metrics + churn detection + phase triggers
├── scheduler.py                ✅ APScheduler: daily pipeline + weekly content jobs
├── ai/
│   ├── llm_client.py           ✅ Provider-agnostic LLM (Gemini Phase 1 / Claude Phase 2+)
│   ├── support.py              ✅ Customer support + quiz product recommendation
│   └── content.py              ✅ FTC-compliant content generation
└── dashboard/
    └── app.py                  ✅ Streamlit: revenue, cohort heatmap, subscription health
```

#### What's Pending (actual remaining work)

**A. Credentials — fill `.env`**
```env
SHOPIFY_STORE_URL=https://your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...
SHOPIFY_WEBHOOK_SECRET=           # generated by Shopify post-webhook registration
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

**B. Platform Setup (UI config — not code)**

| Platform | What to do |
|---|---|
| Shopify | Create store, add products (cognitive performance supplements), set up checkout + payment gateway |
| Supliful | Connect to Shopify, find variant IDs for each product, populate `SUPLIFUL_VARIANT_MAP` |
| Klaviyo | Create flows: welcome series, post-purchase, win-back, quiz recommendation |
| Recharge | Set up subscription plans (pricing, billing cadence) |
| Buffer | Connect TikTok, Instagram, LinkedIn — paste profile IDs into `.env` |
| GA4 | Create property + service account → download JSON key to `credentials/ga4-service-account.json` |
| Typeform | Build quiz funnel → get form ID + webhook secret |

**C. Deployment**

Deploy webhook server (must be publicly reachable over HTTPS):

```bash
# Option A — Railway (easiest)
# Connect repo to Railway → set env vars → deploy → copy public URL to WEBHOOK_BASE_URL

# Option B — Fly.io
fly launch   # from repo root

# Option C — Local dev only
ngrok http 8000
# Paste https:// URL into WEBHOOK_BASE_URL
```

Register webhooks after deployment:
```bash
python scripts/setup_webhooks.py --dry-run   # preview
python scripts/setup_webhooks.py             # register with Shopify, Typeform, Recharge
python scripts/setup_webhooks.py --list      # verify
```

**D. Start All Services**
```bash
# 1. Initialize DB + first sync
python src/pipeline/run.py

# 2. Webhook server (keep running — process manager or platform worker)
uvicorn src.automation.webhooks:app --host 0.0.0.0 --port 8000

# 3. Scheduler (separate worker)
python src/scheduler.py

# 4. Dashboard
streamlit run src/dashboard/app.py
```

**E. Run Tests**
```bash
pip install apscheduler   # gets all 33 tests passing (30/33 pass without it)
pytest tests/
ruff check .
ruff format .
```

---

## Automation Map (once live)

| What | Tool | Human time/week |
|---|---|---|
| Order fulfillment | Supliful auto-ships | 0 min |
| Email sequences | Klaviyo flows | 0 min (set once) |
| Subscriptions | Recharge | 0 min |
| Customer support tier 1 | Claude API | 0 min |
| Analytics | Pipeline + Streamlit | ~10 min review |
| Content scheduling | Buffer | ~15 min batch |
| **Total** | | **~100 min/week** |

---

## Phase Triggers (auto-detected by pipeline)

| Trigger | Condition | Action |
|---|---|---|
| Phase 2 | Any product >50 units/month | Private label evaluation, source 3PL |
| Phase 3 | $5k/month gross sustained 60 days | Custom formulation, paid LLM tier, expand SKUs |
| Churn alert | Weekly cancel rate >5% | Review Klaviyo win-back, investigate feedback |

Monitor logs for strings: `PHASE 2 TRIGGER` and `CHURN ALERT`

---

## LLM Provider Switchover

Currently set to Gemini 2.5 Flash (free, Phase 1). When Phase 2 triggers:

```env
# Switch in .env — zero code changes required
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
# Model: claude-haiku-4-5-20251001 (~$0.001/call)
```

---

## Compliance (non-negotiable)

- No health claims: no "treats," "cures," "prevents," "heals," "guaranteed"
- Mechanism-only language: "studied for," "research suggests," "may support"
- FDA disclaimer required on all product-facing content
- Enforced in code via `_check_compliance()` in `src/ai/content.py`
- Enforced in LLM system prompts
- Tested in `tests/test_core.py`
- Run `/compliance-check` before any content deployment

---

## Full Timeline & Status

| # | Task | Status | Est. Time | Cost |
|---|---|---|---|---|
| 1 | Northwest Registered Agent | ⬜ Pending | 10 min | Free yr 1 |
| 2 | File Delaware C-Corp | ⬜ Pending | 20 min | $110 |
| 3 | EIN from IRS | ⬜ Pending | 10 min | Free |
| 4 | Mercury bank account | ⬜ Pending | 15 min | Free |
| 5 | Domain registration (all 3) | ⬜ Pending | 10 min | ~$70–100 |
| 6 | Sign Bylaws + issue founder shares | ⬜ Pending | 30 min | Free |
| 7 | Fill `.env` with all credentials | ⬜ Pending | 1–2 hrs | — |
| 8 | Platform UI config (Shopify, Klaviyo, etc.) | ⬜ Pending | 3–5 hrs | — |
| 9 | Deploy webhook server (Railway) | ⬜ Pending | 30 min | ~$5/mo |
| 10 | Register webhooks via script | ⬜ Pending | 10 min | — |
| 11 | Run tests (33/33) | ⬜ Pending | 15 min | — |
| 12 | blkphx.com in Framer | ⬜ Pending | 2–4 hrs | $10–15/mo |
| 13 | labops.ai (React + Vercel) | ⬜ Pending | 3–6 hrs | Free |
| 14 | Shopify store live | ⬜ Pending | — | $39/mo |

**Total est. first-month cost: ~$235–275**  
**Estimated time to live: 1–2 focused days (entity) + 1 weekend (sites)**

---

## Claude Code Session Instructions

Drop this file in the repo root as `BLK_PHX_BUILD_PLAN_v2.md` alongside `CLAUDE.md`.

### For e-commerce work (current priority):
```
Read CLAUDE.md and BLK_PHX_BUILD_PLAN_v2.md before starting.
Phase 1 code is complete at commit e2ac45e.
Current task: [specify — e.g., "help me fill .env and deploy to Railway"]
Do not rebuild what already exists. Reference HANDOFF.md for what's done.
```

### For labops.ai site:
```
Read BLK_PHX_BUILD_PLAN_v2.md before starting.
Build the LabOps.AI product landing page — React + Tailwind + Vercel.
LabOps.AI is an AI-native biomanufacturing intelligence platform for CGT manufacturing.
21 CFR Part 11 compliant. Parent: BLK PHX LABS under BLK PHX, INC.
Use the hero copy and component spec in BLK_PHX_BUILD_PLAN_v2.md.
```

### For blkphx.com:
```
Read BLK_PHX_BUILD_PLAN_v2.md before starting.
Build the BLK PHX parent brand site in Framer.
Dark, minimal, fire-accented (black + amber). Bold grotesque type. Motion-forward.
Pages: home, about, ventures, contact.
BLK PHX is a holding company — ventures include BLK PHX LABS (biotech + LabOps.AI) 
and a cognitive performance supplement store.
```

---

*Generated by Claude — June 17, 2026*  
*BLK PHX, INC. | blkphx.com | labops.ai*
