
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .current_etl import run_current_etl


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def update_air_quality():
    logging.info("Starting scheduled air-quality update...")

    try:
        result = run_current_etl()
        logging.info("Scheduled update result: %s", result)

    except Exception:
        logging.exception("Scheduled air-quality update failed")


scheduler = BlockingScheduler(timezone="Asia/Karachi")

# Run once immediately when the scheduler starts
scheduler.add_job(
    update_air_quality,
    trigger="date",
    id="initial_update"
)

# Then repeat every hour
scheduler.add_job(
    update_air_quality,
    trigger=IntervalTrigger(hours=1),
    id="hourly_air_quality_update",
    max_instances=1,
    coalesce=True
)


if __name__ == "__main__":
    logging.info("Air Quality Scheduler started.")
    logging.info("Updates will run every hour.")

    try:
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler stopped.")
