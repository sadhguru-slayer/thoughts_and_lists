from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery = Celery(
    "notifications",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "celery_tasks",
    ],
)

celery.conf.update(
    timezone="UTC",
    enable_utc=True,
)

celery.conf.beat_schedule = {
    "check-reminders-every-minute": {
        "task": "celery_tasks.check_all_reminders",
        "schedule": 60.0,
    }
}
