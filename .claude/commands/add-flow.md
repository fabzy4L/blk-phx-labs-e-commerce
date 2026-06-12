# BLK PHX LABS — Add Klaviyo Flow Command
# Usage in Claude Code: /add-flow

When asked to add a new Klaviyo automation flow:

1. Ask what event triggers the flow (e.g., quiz_completed, product_purchased)
2. Ask how many emails in the sequence and what each covers
3. Add the event tracking call to the appropriate webhook in src/automation/webhooks.py
4. Document the flow in docs/klaviyo-flows.md
5. Never write email copy that makes health claims or disease treatment statements
6. Always include FDA disclaimer in any product-related email content

Brand voice for email copy:
- Direct and intelligent — no hype
- Science-grounded — cite mechanisms, not outcomes  
- Respect the reader's intelligence
- Short sentences. No filler words.
- Subject lines: specific and curious, never clickbait
