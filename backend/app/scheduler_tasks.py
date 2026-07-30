from datetime import datetime, timezone
import pytz
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import joinedload
import logging

from database_sync import SessionLocal
from models.models import User
from models.journal import Journal
from models.tasks import Task, TaskStatus
from services.email import send_reminder_email

logger = logging.getLogger(__name__)


def check_all_reminders():
    now_utc = datetime.now(timezone.utc)

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
                Task.reminder_sent.is_(False),
                Task.is_archived.is_(False),
                Task.status.notin_(
                    [
                        TaskStatus.COMPLETED,
                        TaskStatus.CANCELLED,
                    ]
                ),
                or_(
                    Task.reminder_at <= now_utc,
                    and_(
                        Task.reminder_at.is_(None),
                        Task.due_date <= now_utc,
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

            send_reminder_email(
                task.user.email,
                f"Task Reminder: {task.title}",
                "Task Reminder",
                task.title,
                task.description
                or "You have a task that requires your attention.",
                icon="✅",
            )

            task.reminder_sent = True

        db.commit()
