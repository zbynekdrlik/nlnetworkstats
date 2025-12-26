import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.services.monitor import monitor

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def collect_data_job():
    """Background job to collect data from switches."""
    logger.info("Running scheduled data collection...")
    try:
        monitor.collect_data()
        logger.info("Data collection completed")
    except Exception as e:
        logger.error(f"Data collection failed: {e}")


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        collect_data_job,
        "interval",
        seconds=settings.poll_interval,
        id="collect_data",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started with {settings.poll_interval}s interval")

    # Run initial collection
    collect_data_job()


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
