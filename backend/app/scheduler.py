import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from scheduler_tasks import check_all_reminders

# Ensure logging is configured to at least INFO level so it shows in the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the scheduler
scheduler = BackgroundScheduler()

def start_scheduler():
    logger.info("Starting APScheduler...")
    scheduler.add_job(
        check_all_reminders,
        trigger=CronTrigger(second=0),
        id="check_reminders_every_minute",
        name="Check and send reminders every minute",
        replace_existing=True,
    )
    scheduler.start()

def shutdown_scheduler():
    logger.info("Shutting down APScheduler...")
    scheduler.shutdown()
