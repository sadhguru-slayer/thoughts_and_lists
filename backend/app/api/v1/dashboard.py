from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
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

    # 1. Fetch all journals for stats and activity map
    journal_result = await db.execute(
        select(journal.Journal)
        .where(journal.Journal.user_id == current_user.id)
        .order_by(journal.Journal.date.desc())
    )
    journals = journal_result.scalars().all()

    # 2. Fetch all thoughts for stats and activity map
    thought_result = await db.execute(
        select(thoughts_models.Thought)
        .where(thoughts_models.Thought.user_id == current_user.id)
        .order_by(thoughts_models.Thought.created_at.desc())
    )
    thoughts = thought_result.scalars().all()

    # 3. Fetch all tasks for stats and activity map
    task_result = await db.execute(
        select(tasks.Task)
        .where(tasks.Task.user_id == current_user.id)
        .order_by(tasks.Task.created_at.desc())
    )
    all_tasks = task_result.scalars().all()

    # Calculate Stats
    total_journals = len(journals)
    total_words = sum(len(str(j.content).split()) for j in journals if j.content)
    total_thoughts = len(thoughts)
    total_tasks = len(all_tasks)
    completed_tasks = len([t for t in all_tasks if t.status == tasks.TaskStatus.COMPLETED or t.completed])

    # Calculate Daily Activity (Contributions)
    daily_map = defaultdict(
        lambda: {
            "journal_created": 0,
            "journal_edited": 0,
            "thought_created": 0,
            "thought_edited": 0,
            "task_completed": 0,
        }
    )

    def _to_day_str(dt_value):
        if not dt_value:
            return None
        if hasattr(dt_value, "strftime"):
            return dt_value.strftime("%Y-%m-%d")
        return str(dt_value)[:10]

    def _add_counter(day_str, key):
        if not day_str:
            return
        daily_map[day_str][key] += 1

    for j in journals:
        created_day = _to_day_str(getattr(j, "created_at", None) or j.date)
        edited_day = _to_day_str(getattr(j, "updated_at", None))
        _add_counter(created_day, "journal_created")
        if edited_day and edited_day != created_day:
            _add_counter(edited_day, "journal_edited")

    for t in thoughts:
        created_day = _to_day_str(getattr(t, "created_at", None))
        edited_day = _to_day_str(getattr(t, "updated_at", None))
        _add_counter(created_day, "thought_created")
        if edited_day and edited_day != created_day:
            _add_counter(edited_day, "thought_edited")

    for tk in all_tasks:
        if tk.completed_at:
            _add_counter(_to_day_str(tk.completed_at), "task_completed")
        elif tk.status == tasks.TaskStatus.COMPLETED and tk.updated_at:
            _add_counter(_to_day_str(tk.updated_at), "task_completed")

    daily_counts = []
    for day in sorted(daily_map.keys()):
        day_data = daily_map[day]
        total_actions = sum(day_data.values())
        daily_counts.append(
            {
                "date": day,
                "count": total_actions,
                "total_actions": total_actions,
                **day_data,
            }
        )

    # Streak Calculation for Journals
    unique_journal_dates = sorted(list({_to_day_str(j.date) for j in journals if j.date}), reverse=True)
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

    has_journaled_today = False
    today_date_str = datetime.utcnow().strftime("%Y-%m-%d")
    for j in journals:
        if _to_day_str(j.date) == today_date_str:
            has_journaled_today = True
            break

    # Top 5 Pending Tasks
    pending_tasks = [t for t in all_tasks if t.status != tasks.TaskStatus.COMPLETED and not t.completed and not t.is_archived]
    
    # Simple sort: high priority first, then due_date if exists
    def task_sort_key(t):
        priority_map = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        p_score = priority_map.get(t.priority, 99)
        d_score = t.due_date.timestamp() if t.due_date else 9999999999
        return (p_score, d_score)
        
    pending_tasks.sort(key=task_sort_key)
    recent_tasks = pending_tasks[:5]

    # Top 5 Recent Thoughts
    recent_thoughts = thoughts[:5]

    return {
        "stats": {
            "total_journals": total_journals,
            "total_words": total_words,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_thoughts": total_thoughts,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
        },
        "daily_activity": daily_counts,
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
        ]
    }
