# BLK PHX LABS — E-Commerce Infrastructure

Science-backed cognitive performance brand. Automation-first stack.
Built for ~100 min/week active management.

## Stack
- **Storefront**: Shopify
- **Email**: Klaviyo
- **Subscriptions**: Recharge  
- **Fulfillment**: Supliful (Phase 1) → 3PL (Phase 2)
- **Quiz Funnel**: Typeform
- **Data Pipeline**: Python + SQLite/Postgres
- **Dashboard**: Streamlit
- **AI Support**: Claude API
- **Webhooks**: FastAPI

## Setup

```bash
# 1. Clone and enter
git clone <repo> blkphx-labs && cd blkphx-labs

# 2. Create virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Fill in all API keys in .env

# 5. Initialize database
python src/pipeline/run.py

# 6. Start webhook server
uvicorn src.automation.webhooks:app --host 0.0.0.0 --port 8000

# 7. Launch dashboard
streamlit run src/dashboard/app.py
```

## Claude Code Commands
- `/run-pipeline` — sync data and compute metrics
- `/add-flow` — add a new Klaviyo automation flow
- `/compliance-check` — scan for FTC/FDA violations

## Project Structure
```
blkphx-labs/
├── CLAUDE.md                    # Claude Code instructions (read every session)
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
├── .claude/
│   └── commands/                # Custom Claude Code slash commands
├── src/
│   ├── store/
│   │   └── shopify_client.py    # Shopify API client
│   ├── automation/
│   │   ├── klaviyo_client.py    # Klaviyo events + profiles
│   │   └── webhooks.py          # FastAPI webhook server
│   ├── pipeline/
│   │   └── run.py               # ETL pipeline + phase triggers
│   ├── ai/
│   │   └── support.py           # Claude API support layer
│   └── dashboard/
│       └── app.py               # Streamlit analytics dashboard
├── docs/                        # Architecture notes
├── scripts/                     # Setup + migration scripts
└── tests/                       # pytest test suite
```

## Automation Map
| What | Tool | Human time |
|------|------|-----------|
| Order fulfillment | Supliful auto-ships | 0 min |
| Email sequences | Klaviyo flows | 0 min (set once) |
| Subscriptions | Recharge | 0 min |
| Customer support (tier 1) | Claude API | 0 min |
| Analytics | Pipeline + Streamlit | 10 min/week review |
| Content scheduling | Buffer | 15 min/week batch |
| **Total** | | **~100 min/week** |

## Phase Triggers (auto-detected by pipeline)
- **Phase 2**: Any product > 50 units/month → private label evaluation
- **Phase 3**: $5,000/month gross sustained 60 days → custom formulation + paid acquisition

## Compliance
- No health claims in any generated content
- All product language: mechanism-only, research-cited
- FDA disclaimer required on all product content
- Run `/compliance-check` before any content deployment
