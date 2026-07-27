from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from core.dependencies import db_session
from core.config import oauth2_scheme
from services.auth import get_current_user
from models import journal, models as thoughts_models, tasks

app = APIRouter()

@app.get("/dashboard")
async def get_dashboard_data(
    db: db_session,
    token: str = Depends(oauth2_scheme)
):
    current_user = await get_current_user(db, token)
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fast Counts
    total_journals = await db.scalar(select(func.count(journal.Journal.id)).where(journal.Journal.user_id == current_user.id))
    total_thoughts = await db.scalar(select(func.count(thoughts_models.Thought.id)).where(thoughts_models.Thought.user_id == current_user.id))
    total_tasks = await db.scalar(select(func.count(tasks.Task.id)).where(tasks.Task.user_id == current_user.id))
    completed_tasks = await db.scalar(select(func.count(tasks.Task.id)).where(
        tasks.Task.user_id == current_user.id,
        tasks.Task.status == tasks.TaskStatus.COMPLETED
    ))

    # Fetch only the Top 5 of each
    recent_journals = (await db.execute(
        select(journal.Journal)
        .where(journal.Journal.user_id == current_user.id)
        .order_by(journal.Journal.date.desc())
        .limit(5)
    )).scalars().all()

    recent_thoughts = (await db.execute(
        select(thoughts_models.Thought)
        .where(thoughts_models.Thought.user_id == current_user.id)
        .order_by(thoughts_models.Thought.created_at.desc())
        .limit(5)
    )).scalars().all()

    # Get pending tasks
    pending_tasks_result = await db.execute(
        select(tasks.Task)
        .where(
            tasks.Task.user_id == current_user.id,
            tasks.Task.status != tasks.TaskStatus.COMPLETED,
            tasks.Task.completed == False,
            tasks.Task.is_archived == False
        )
    )
    pending_tasks = pending_tasks_result.scalars().all()
    
    # Sort pending tasks by priority and date in python to match previous logic
    def task_sort_key(t):
        priority_map = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        p_score = priority_map.get(t.priority, 99)
        d_score = t.due_date.timestamp() if t.due_date else 9999999999
        return (p_score, d_score)
        
    pending_tasks.sort(key=task_sort_key)
    recent_tasks = pending_tasks[:5]

    # Calculate streak using only dates
    journal_dates = (await db.execute(
        select(journal.Journal.date)
        .where(journal.Journal.user_id == current_user.id)
        .order_by(journal.Journal.date.desc())
    )).scalars().all()

    def _to_day_str(dt_value):
        if not dt_value:
            return None
        if hasattr(dt_value, "strftime"):
            return dt_value.strftime("%Y-%m-%d")
        return str(dt_value)[:10]

    unique_journal_dates = sorted(list({_to_day_str(d) for d in journal_dates if d}), reverse=True)
    current_streak = 0
    longest_streak = 0
    if unique_journal_dates:
        temp_longest = 1
        for i in range(len(unique_journal_dates) - 1):
            d1 = datetime.strptime(unique_journal_dates[i], "%Y-%m-%d")
            d2 = datetime.strptime(unique_journal_dates[i+1], "%Y-%m-%d")
            if (d1 - d2).days == 1:
                temp_longest += 1
            else:
                longest_streak = max(longest_streak, temp_longest)
                temp_longest = 1
        longest_streak = max(longest_streak, temp_longest)

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        tomorrow_str = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        date_candidates = [tomorrow_str, today_str, yesterday_str]
        
        if unique_journal_dates[0] in date_candidates:
            current_streak = 1
            for i in range(len(unique_journal_dates) - 1):
                d1 = datetime.strptime(unique_journal_dates[i], "%Y-%m-%d")
                d2 = datetime.strptime(unique_journal_dates[i+1], "%Y-%m-%d")
                if (d1 - d2).days == 1:
                    current_streak += 1
                else:
                    break

    has_journaled_today = (today_str in unique_journal_dates)

    return {
        "stats": {
            "total_journals": total_journals,
            "total_words": 0, # Optimization: Dropped full text fetch for word count
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_thoughts": total_thoughts,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
        },
        "daily_activity": [],
        "has_journaled_today": has_journaled_today,
        "recent_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "priority": getattr(t.priority, "value", t.priority),
                "due_date": t.due_date,
            } for t in recent_tasks
        ],
        "recent_notes": [
            {
                "id": t.id,
                "title": t.title,
                "content_preview": t.content[:150] if t.content else "",
                "created_at": t.created_at,
            } for t in recent_thoughts
        ],
        "recent_journals": [
            {
                "id": j.id,
                "title": j.title,
                "date": j.date,
                "content_preview": j.content[:150] if j.content else "",
            } for j in recent_journals
        ]
    }
