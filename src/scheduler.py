"""
BLK PHX LABS — Task Scheduler
Runs the data pipeline and content generation on a cron schedule.
Run: python src/scheduler.py

Jobs:
  pipeline  — daily sync + metrics + churn detection
  content   — weekly social content generation + Buffer scheduling
"""

import asyncio
import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

PIPELINE_HOUR = int(os.getenv("PIPELINE_SCHEDULE_HOUR", "6"))
PIPELINE_MINUTE = int(os.getenv("PIPELINE_SCHEDULE_MINUTE", "0"))
CONTENT_DAY = os.getenv("CONTENT_SCHEDULE_DAY", "mon")
CONTENT_HOUR = int(os.getenv("CONTENT_SCHEDULE_HOUR", "7"))
CONTENT_ENABLED = os.getenv("CONTENT_SCHEDULE_ENABLED", "true").lower() == "true"


def run_pipeline_job():
    """Daily: sync orders/customers, compute metrics, detect churn, check phase triggers."""
    from src.pipeline.run import run_pipeline
    try:
        result = asyncio.run(run_pipeline())
        logger.info(f"Pipeline job complete: {result}")
    except Exception as e:
        logger.error(f"Pipeline job failed: {e}", exc_info=True)


def run_content_job():
    """Weekly: generate compliant social content and schedule via Buffer."""
    from src.ai.content import generate_weekly_content_plan
    from src.automation.buffer_client import schedule_weekly_content

    async def _run():
        posts = await generate_weekly_content_plan()
        clean = [p for p in posts if p.get("compliance_ok", True)]
        skipped = len(posts) - len(clean)
        if skipped:
            logger.warning(f"Content compliance: {skipped} post(s) filtered before scheduling")
        result = await schedule_weekly_content(clean)
        logger.info(f"Content job complete: {result}")

    try:
        asyncio.run(_run())
    except Exception as e:
        logger.error(f"Content job failed: {e}", exc_info=True)


def build_scheduler() -> BlockingScheduler:
    """Construct and configure the scheduler. Separated for testability."""
    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        run_pipeline_job,
        trigger=CronTrigger(hour=PIPELINE_HOUR, minute=PIPELINE_MINUTE),
        id="pipeline",
        name="Daily data pipeline",
        max_instances=1,       # prevent overlapping runs
        misfire_grace_time=3600,
    )

    if CONTENT_ENABLED:
        scheduler.add_job(
            run_content_job,
            trigger=CronTrigger(day_of_week=CONTENT_DAY, hour=CONTENT_HOUR),
            id="content",
            name="Weekly content generation",
            max_instances=1,
            misfire_grace_time=3600,
        )

    return scheduler


def main():
    scheduler = build_scheduler()

    job_names = [j.name for j in scheduler.get_jobs()]
    logger.info(f"Scheduler starting — jobs: {job_names}")
    logger.info(f"Pipeline: daily at {PIPELINE_HOUR:02d}:{PIPELINE_MINUTE:02d} UTC")
    if CONTENT_ENABLED:
        logger.info(f"Content:  {CONTENT_DAY}s at {CONTENT_HOUR:02d}:00 UTC")
    logger.info("Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
