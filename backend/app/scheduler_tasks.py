# scheduler_tasks.py

from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import logging
import pytz

from sqlalchemy import select, or_, func
from sqlalchemy.orm import joinedload

from database_sync import SessionLocal
from models.models import User
from models.journal import Journal
from models.tasks import Task, TaskStatus, TaskRecurrence
from services.email import send_reminder_email


logger = logging.getLogger(__name__)


def check_all_reminders():
    now_utc = datetime.now(timezone.utc)
    # Small grace window because APScheduler runs once per minute.
    now_check = now_utc + timedelta(seconds=10)

    with SessionLocal() as db:

        # ============================================================
        # Journal reminders
        # ============================================================
        users = db.execute(
            select(User).where(
                User.journal_reminder_active.is_(True),
                User.journal_reminder_time.is_not(None),
            )
        ).scalars().all()

        for user in users:
            try:
                tz = pytz.timezone(user.timezone or "Asia/Kolkata")
                local_now = now_utc.astimezone(tz)
                time_val = user.journal_reminder_time

                if isinstance(time_val, str):
                    time_val = datetime.strptime(time_val[:5], "%H:%M").time()

                reminder_dt = tz.localize(datetime.combine(local_now.date(), time_val))

                if local_now < reminder_dt or user.last_journal_reminder_date == local_now.date():
                    continue

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

                send_reminder_email(
                    user.email,
                    "Daily Journal Reminder",
                    "Write Your Journal",
                    "Don't forget to write your progress!",
                    "Every day counts. Keep up the good work and jot down your thoughts today.",
                    icon="📓",
                )

                user.last_journal_reminder_date = local_now.date()

            except Exception:
                logger.exception("[Journal] Error for user %s", user.id)

        # ============================================================
        # Task reminders
        # ============================================================
        # reminder_at is the reminder time for THIS task occurrence.
        # It does NOT move forward when the reminder is sent.
        #
        # A recurring task stays active until the user completes it.
        # complete_task() then creates the next occurrence.
        tasks = db.execute(
            select(Task).options(joinedload(Task.user)).where(
                Task.is_archived.is_(False),
                Task.status.notin_([
                    TaskStatus.COMPLETED,
                    TaskStatus.CANCELLED,
                ]),
                Task.reminder_at.is_not(None),
                Task.reminder_at <= now_check,
            )
        ).scalars().all()

        for task in tasks:
            if not task.user:
                logger.warning("[Task] Task #%s has no user", task.id)
                continue

            # Non-recurring tasks: send once only (reminder_at is never advanced).
            if task.recurrence_interval == TaskRecurrence.NONE:
                if task.last_reminder_sent_at is not None:
                    continue

            recurring = task.recurrence_interval != TaskRecurrence.NONE

            try:
                send_reminder_email(
                    task.user.email,
                    f"{'Recurring Task Reminder' if recurring else 'Task Reminder'}: {task.title}",
                    "Recurring Task Reminder" if recurring else "Task Reminder",
                    task.title,
                    task.description or "You have a task that requires your attention.",
                    icon="🚨" if recurring else "✅",
                    task_id=task.uuid,
                )

                task.last_reminder_sent_at = now_utc

                # Advance reminder_at to the next occurrence so the task won't
                # appear in the query again until the correct future time.
                # The SQL condition (reminder_at <= now_check) is now the sole gate.
                if task.recurrence_interval == TaskRecurrence.DAILY:
                    task.reminder_at += timedelta(days=1)
                elif task.recurrence_interval == TaskRecurrence.WEEKLY:
                    task.reminder_at += timedelta(weeks=1)
                elif task.recurrence_interval == TaskRecurrence.MONTHLY:
                    task.reminder_at += relativedelta(months=1)

            except Exception:
                # If email fails, reminder_at and last_reminder_sent_at are not
                # updated, so the next scheduler run will retry.
                logger.exception("[Task] Error sending reminder for task %s", task.id)

        db.commit()
