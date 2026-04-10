"""APScheduler for recurring pipeline jobs."""
from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import structlog

logger = structlog.get_logger()

_scheduler = BackgroundScheduler()


def _run_daily_validation():
    from app.config.loader import get_products
    from app.services.report_generator import report_generator

    logger.info("Running scheduled daily validation reports")
    for product_id in get_products():
        try:
            result = report_generator.generate(product_id=product_id, report_type="daily_validation")
            logger.info("Daily report generated", product=product_id, report_id=result["report_id"])
        except Exception as e:
            logger.error("Daily report failed", product=product_id, error=str(e))


def _run_weekly_trend():
    from app.config.loader import get_products
    from app.services.report_generator import report_generator
    from datetime import timedelta

    logger.info("Running scheduled weekly trend reports")
    for product_id in get_products():
        try:
            date_from = datetime.utcnow() - timedelta(days=7)
            result = report_generator.generate(
                product_id=product_id,
                report_type="weekly_trend",
                date_from=date_from,
            )
            logger.info("Weekly report generated", product=product_id, report_id=result["report_id"])
        except Exception as e:
            logger.error("Weekly report failed", product=product_id, error=str(e))


def _run_drift_detection():
    from app.config.loader import get_products
    import app.services.ml_service as ml_service

    logger.info("Running scheduled drift detection")
    for product_id in get_products():
        try:
            result = ml_service.check_drift(product_id)
            if result.get("drift_detected"):
                logger.warning(
                    "Process drift detected",
                    product=product_id,
                    drifting_features=result.get("drifting_features", []),
                )
            else:
                logger.info("No drift detected", product=product_id)
        except Exception as e:
            logger.error("Drift detection failed", product=product_id, error=str(e))


def _invalidate_query_cache():
    import asyncio
    from app.services.cache_service import cache_invalidate
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(cache_invalidate("soc:query:*"))
        loop.close()
    except Exception as e:
        logger.warning("Cache invalidation failed", error=str(e))


def start_scheduler():
    _scheduler.add_job(_run_daily_validation, CronTrigger(hour=6, minute=0), id="daily_validation", replace_existing=True)
    _scheduler.add_job(_run_weekly_trend, CronTrigger(day_of_week="mon", hour=8, minute=0), id="weekly_trend", replace_existing=True)
    _scheduler.add_job(_invalidate_query_cache, CronTrigger(minute=0), id="cache_invalidation", replace_existing=True)
    _scheduler.add_job(_run_drift_detection, CronTrigger(minute=0), id="drift_detection", replace_existing=True)
    _scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
