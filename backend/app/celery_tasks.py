from datetime import datetime, timezone
import pytz
from sqlalchemy import select, or_, func
from sqlalchemy.orm import joinedload
from celery.utils.log import get_task_logger

from celery_app import celery
from database_sync import SessionLocal
from models.models import User
from models.journal import Journal
from models.tasks import Task, TaskStatus
from services.email import send_reminder_email

logger = get_task_logger(__name__)


@celery.task
def check_all_reminders():
    now_utc = datetime.now(timezone.utc)
    logger.info("[CELERY] check_all_reminders running at UTC %s", now_utc)

    with SessionLocal() as db:

        # -------------------------
        # Journal Reminders
        # -------------------------
        users = db.execute(
            select(User).where(User.journal_reminder_active == True)
        ).scalars().all()

        for user in users:
            if not user.journal_reminder_time:
                continue

            tz = pytz.timezone(user.timezone or "Asia/Kolkata")
            local_now = now_utc.astimezone(tz)

            try:
                time_val = user.journal_reminder_time
                if isinstance(time_val, str):
                    time_val = datetime.strptime(time_val[:5], "%H:%M").time()

                if local_now.hour != time_val.hour or local_now.minute != time_val.minute:
                    continue

                if user.last_journal_reminder_date == local_now.date():
                    continue

                # Skip if journal already written today
                journal_today = db.execute(
                    select(Journal).where(
                        Journal.user_id == user.id,
                        or_(
                            func.date(Journal.date) == local_now.date(),
                            func.date(Journal.created_at) == local_now.date(),
                        ),
                    )
                ).scalars().first()

                if journal_today:
                    user.last_journal_reminder_date = local_now.date()
                    continue

                logger.info("[Journal] Sending reminder → %s", user.email)
                send_reminder_email(
                    user.email,
                    "Daily Journal Reminder",
                    "Write Your Journal",
                    "Don't forget to write your progress!",
                    "Every day counts. Keep up the good work and jot down your thoughts today.",
                    icon="📓",
                )
                user.last_journal_reminder_date = local_now.date()

            except Exception as e:
                logger.error("[Journal] Error for user %s: %s", user.id, e)

        # -------------------------
        # Task Reminders
        # -------------------------
        tasks = db.execute(
            select(Task)
            .options(joinedload(Task.user))
            .where(
                or_(
                    Task.reminder_at.is_not(None),
                    Task.due_date.is_not(None),
                )
            )
        ).scalars().all()

        for task in tasks:
            if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                continue
            if task.reminder_sent:
                continue

            reminder_time = task.reminder_at or task.due_date
            if not reminder_time:
                continue

            if reminder_time.tzinfo is None:
                user_tz_str = (task.user.timezone if task.user and task.user.timezone else "Asia/Kolkata")
                reminder_time = pytz.timezone(user_tz_str).localize(reminder_time).astimezone(timezone.utc)

            if reminder_time <= now_utc:
                if task.user:
                    logger.info("[Task] Sending reminder for task #%s → %s", task.id, task.user.email)
                    send_reminder_email(
                        task.user.email,
                        f"Task Reminder: {task.title}",
                        "Task Reminder",
                        task.title,
                        task.description or "You have a task that requires your attention.",
                        icon="✅",
                    )
                task.reminder_sent = True

        db.commit()