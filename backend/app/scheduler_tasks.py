from datetime import datetime, timezone
import pytz
from sqlalchemy import select, or_, func
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
    # logger.info(f"[SCHEDULER] check_all_reminders running at UTC {now_utc}")

    with SessionLocal() as db:

        # -------------------------
        # Journal Reminders
        # -------------------------
        users = db.execute(
            select(User).where(User.journal_reminder_active == True)
        ).scalars().all()

        for user in users:
            # logger.info(f"[Journal] Checking user {user.email}")
            if not user.journal_reminder_time:
                # logger.info(f"[Journal] User {user.email} has no journal_reminder_time")
                continue

            tz = pytz.timezone(user.timezone or "Asia/Kolkata")
            local_now = now_utc.astimezone(tz)
            # logger.info(f"[Journal] User {user.email} local time: {local_now}")

            try:
                time_val = user.journal_reminder_time
                if isinstance(time_val, str):
                    time_val = datetime.strptime(time_val[:5], "%H:%M").time()

                # Combine today's date with the reminder time to create a full datetime
                reminder_dt = datetime.combine(local_now.date(), time_val).replace(tzinfo=tz)
                
                # If current time is before the reminder time, skip.
                # If it's past, we proceed (and last_journal_reminder_date prevents duplicates)
                if local_now < reminder_dt:
                    # logger.info(f"[Journal] User {user.email} reminder time {reminder_dt} is in the future")
                    continue

                if user.last_journal_reminder_date == local_now.date():
                    # logger.info(f"[Journal] User {user.email} already reminded today ({local_now.date()})")
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
                    # logger.info(f"[Journal] User {user.email} already wrote journal today, skipping reminder")
                    user.last_journal_reminder_date = local_now.date()
                    continue

                # logger.info(f"[Journal] Sending reminder → {user.email}")
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
                print("[Journal] Error for user %s: %s", user.id, e)

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
            # logger.info(f"[Task] Checking task #{task.id} '{task.title}' for user {task.user.email if task.user else 'None'}")
            if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                # logger.info(f"[Task] Task #{task.id} is {task.status}, skipping")
                continue
            if task.reminder_sent:
                # logger.info(f"[Task] Task #{task.id} reminder already sent, skipping")
                continue

            reminder_time = task.reminder_at or task.due_date
            if not reminder_time:
                # logger.info(f"[Task] Task #{task.id} has no reminder_time, skipping")
                continue

            if reminder_time.tzinfo is None:
                user_tz_str = (task.user.timezone if task.user and task.user.timezone else "Asia/Kolkata")
                reminder_time = pytz.timezone(user_tz_str).localize(reminder_time).astimezone(timezone.utc)
            
            # logger.info(f"[Task] Task #{task.id} reminder time: {reminder_time}, now UTC: {now_utc}")

            if reminder_time <= now_utc:
                if task.user:
                    # logger.info("[Task] Sending reminder for task #%s → %s", task.id, task.user.email)
                    send_reminder_email(
                        task.user.email,
                        f"Task Reminder: {task.title}",
                        "Task Reminder",
                        task.title,
                        task.description or "You have a task that requires your attention.",
                        icon="✅",
                    )
                else:
                    logger.warning(f"[Task] Task #{task.id} has no user, cannot send email")
                task.reminder_sent = True
            else:
                # logger.info(f"[Task] Task #{task.id} reminder time is in the future, skipping")
                pass

        db.commit()