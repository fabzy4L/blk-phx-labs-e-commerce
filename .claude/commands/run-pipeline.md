# BLK PHX LABS — Pipeline Run Command
# Usage in Claude Code: /run-pipeline

Run the full data pipeline:

1. Initialize the database if it doesn't exist
2. Sync orders from Shopify (last 7 days)
3. Sync customers from Shopify (last 30 days)
4. Compute daily metrics for today
5. Check phase triggers and report any findings
6. Log all results

Command: `python src/pipeline/run.py`

After running, check the dashboard for updated metrics.
If any phase triggers fire, report them clearly with the product ID and unit count.
