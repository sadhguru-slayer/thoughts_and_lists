from datetime import datetime, timezone, timedelta
import pytz
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import joinedload
import logging

from database_sync import SessionLocal
from models.models import User
from models.journal import Journal
from models.tasks import Task, TaskStatus, TaskRecurrence
from services.email import send_reminder_email

logger = logging.getLogger(__name__)


def check_all_reminders():
    now_utc = datetime.now(timezone.utc)
    # Add a 10s grace window so sub-second microsecond offsets don't miss the current minute run
    now_check = now_utc + timedelta(seconds=10)

    with SessionLocal() as db:

        # -------------------------
        # Journal Reminders
        # -------------------------
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
                    time_val = datetime.strptime(
                        time_val[:5], "%H:%M"
                    ).time()

                reminder_dt = tz.localize(
                    datetime.combine(local_now.date(), time_val)
                )

                if local_now < reminder_dt:
                    continue

                if user.last_journal_reminder_date == local_now.date():
                    continue

                journal_today = db.execute(
                    select(Journal).where(
                        Journal.user_id == user.id,
                        or_(
                            func.date(Journal.date)
                            == local_now.date(),
                            func.date(Journal.created_at)
                            == local_now.date(),
                        ),
                    )
                ).scalars().first()

                if journal_today:
                    user.last_journal_reminder_date = (
                        local_now.date()
                    )
                    continue

                send_reminder_email(
                    user.email,
                    "Daily Journal Reminder",
                    "Write Your Journal",
                    "Don't forget to write your progress!",
                    "Every day counts. Keep up the good work and jot down your thoughts today.",
                    icon="📓",
                )

                user.last_journal_reminder_date = (
                    local_now.date()
                )

            except Exception:
                logger.exception(
                    "[Journal] Error preparing reminder for user %s",
                    user.id,
                )

        # -------------------------
        # Task Reminders
        # -------------------------
        tasks = db.execute(
            select(Task)
            .options(joinedload(Task.user))
            .where(
                Task.is_archived.is_(False),
                Task.status.notin_(
                    [
                        TaskStatus.COMPLETED,
                        TaskStatus.CANCELLED,
                    ]
                ),
                or_(
                    Task.reminder_at <= now_check,
                    and_(
                        Task.reminder_at.is_(None),
                        Task.due_date <= now_check,
                    ),
                ),
            )
        ).scalars().all()

        for task in tasks:
            if not task.user:
                logger.warning(
                    "[Task] Task #%s has no user",
                    task.id,
                )
                continue

            is_recurring = task.recurrence_interval != TaskRecurrence.NONE
            should_send = False
            email_subject = f"Task Reminder: {task.title}"
            email_title = "Task Reminder"
            
            if not is_recurring:
                if not task.reminder_sent:
                    should_send = True
            else:
                # For recurring/overdue tasks, remind based on interval with a 5-60s grace period
                delay = 86340 # slightly less than 24h
                # if task.recurrence_interval == TaskRecurrence.TESTING_SEC:
                #     delay = 55

                if not task.last_reminder_sent_at or (now_utc - task.last_reminder_sent_at).total_seconds() >= delay:
                    should_send = True
                    email_title = "Recurring Task Reminder"
                    email_subject = f"Overdue Task: {task.title}"

            if not should_send:
                continue

            send_reminder_email(
                task.user.email,
                email_subject,
                email_title,
                task.title,
                task.description or "You have a task that requires your attention.",
                icon="🚨" if is_recurring else "✅",
                task_id=task.uuid,
            )

            task.reminder_sent = True
            task.last_reminder_sent_at = now_utc

        db.commit()