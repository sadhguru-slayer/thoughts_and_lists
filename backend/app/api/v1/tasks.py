from datetime import datetime, timezone, timedelta
from math import ceil
from typing import List
from uuid import UUID

from fastapi import HTTPException, Path, Depends, APIRouter, Query
from sqlalchemy import func, select, or_

from core.dependencies import db_session
from core.config import oauth2_scheme
from services.auth import get_current_user
from models.tasks import Task, TaskPriority, TaskStatus, TaskRecurrence
from schema.UserAndThought import UserOut
from schema.Tasks import (
    TaskCreate,
    TaskDetail,
    TaskSummary,
    TaskUpdate,
)

app = APIRouter()

async def get_tasks(
    db: db_session,
    user: UserOut,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    completed: bool | None = None,
    today: bool = False,
    overdue: bool = False,
    search: str | None = None,
    archived: bool = False,
    page: int = 1,
    per_page: int = 20,
):
    base_filter = [
        Task.user_id == user.id,
        Task.is_archived == archived,
    ]

    if status:
        base_filter.append(Task.status == status)

    if priority:
        base_filter.append(Task.priority == priority)

    if completed is not None:
        if completed:
            base_filter.append(Task.status == TaskStatus.COMPLETED)
        else:
            base_filter.append(Task.status != TaskStatus.COMPLETED)

    if today:
        today_date = datetime.now(timezone.utc).date()
        base_filter.extend([
            Task.due_date.is_not(None),
            Task.due_date >= datetime.combine(today_date, datetime.min.time(), tzinfo=timezone.utc),
            Task.due_date < datetime.combine(today_date, datetime.max.time(), tzinfo=timezone.utc),
        ])

    if overdue:
        base_filter.extend([
            Task.due_date.is_not(None),
            Task.due_date < datetime.now(timezone.utc),
            Task.status != TaskStatus.COMPLETED,
        ])

    if search:
        base_filter.append(
            or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count(Task.id)).where(*base_filter)
    total = (await db.scalar(count_query)) or 0

    query = (
        select(
            Task.uuid,
            Task.title,
            Task.status,
            Task.priority,
            Task.completed,
            Task.due_date,
            Task.created_at,
            Task.recurrence_interval,
        )
        .where(*base_filter)
        .order_by(Task.position.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await db.execute(query)
    rows = result.all()

    items = [
        TaskSummary(
            uuid=row.uuid,
            title=row.title,
            status=row.status,
            priority=row.priority,
            completed=row.completed,
            due_date=row.due_date,
            created_at=row.created_at,
            recurrence_interval=row.recurrence_interval,
        )
        for row in rows
    ]

    total_pages = ceil(total / per_page) if per_page else 1
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


async def get_task(db: db_session, task_uuid: UUID, user: UserOut):
    result = await db.execute(
        select(Task).where(
            Task.uuid == task_uuid,
            Task.user_id == user.id,
        )
    )

    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with uuid {task_uuid} not found."
        )

    return task


async def create_task(
    db: db_session,
    task_data: TaskCreate,
    user: UserOut,
):
    reminder_at = task_data.reminder_at or task_data.due_date
    task = Task(
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        due_date=task_data.due_date,
        reminder_at=reminder_at,
        reminder_sent=False,
        recurrence_interval=task_data.recurrence_interval,
        user_id=user.id,
    )

    db.add(task)

    await db.commit()
    await db.refresh(task)

    return task


async def update_task(
    db: db_session,
    task_uuid: UUID,
    task_data: TaskUpdate,
    user: UserOut,
):
    result = await db.execute(
        select(Task).where(
            Task.uuid == task_uuid,
            Task.user_id == user.id,
        )
    )

    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with uuid {task_uuid} not found."
        )

    updates = task_data.model_dump(exclude_unset=True)

    # Sync reminder_at with due_date if due_date is provided and reminder_at is missing or None
    if "due_date" in updates and updates.get("due_date") is not None:
        if "reminder_at" not in updates or updates.get("reminder_at") is None:
            updates["reminder_at"] = updates["due_date"]

    # Reset reminder_sent when reminder_at or due_date changes
    if "due_date" in updates or "reminder_at" in updates:
        updates["reminder_sent"] = False
        updates["last_reminder_sent_at"] = None

    for field, value in updates.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    return {
        "message": "Task updated successfully.",
        "task": task,
    }


async def delete_task(
    db: db_session,
    task_uuid: UUID,
    user: UserOut,
):
    result = await db.execute(
        select(Task).where(
            Task.uuid == task_uuid,
            Task.user_id == user.id,
        )
    )

    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with uuid {task_uuid} not found."
        )

    await db.delete(task)
    await db.commit()

    return {
        "message": "Task deleted successfully."
    }

async def complete_task(db: db_session, task_uuid: UUID, user: UserOut):
    task = await get_task(db, task_uuid, user)

    if task.recurrence_interval in (
        TaskRecurrence.DAILY, 
        TaskRecurrence.WEEKLY, 
        TaskRecurrence.MONTHLY, 
        # TaskRecurrence.TESTING_SEC
    ):
        new_due_date = None
        new_reminder_at = None
        
        delta = None
        if task.recurrence_interval == TaskRecurrence.DAILY:
            delta = timedelta(days=1)
        elif task.recurrence_interval == TaskRecurrence.WEEKLY:
            delta = timedelta(weeks=1)
        elif task.recurrence_interval == TaskRecurrence.MONTHLY:
            delta = timedelta(days=30)
        # elif task.recurrence_interval == TaskRecurrence.TESTING_SEC:
        #     delta = timedelta(seconds=60)
            
        if delta:
            if task.due_date:
                new_due_date = task.due_date + delta
            if task.reminder_at:
                new_reminder_at = task.reminder_at + delta


        new_task = Task(
            title=task.title,
            description=task.description,
            priority=task.priority,
            due_date=new_due_date,
            reminder_at=new_reminder_at,
            reminder_sent=False,
            recurrence_interval=task.recurrence_interval,
            user_id=user.id,
        )
        db.add(new_task)
        task.recurrence_interval = TaskRecurrence.NONE

    task.status = TaskStatus.COMPLETED
    task.completed = True
    task.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)

    return task

async def uncomplete_task(db: db_session, task_uuid: UUID, user: UserOut):
    task = await get_task(db, task_uuid, user)

    task.status = TaskStatus.TODO
    task.completed = False
    task.completed_at = None

    await db.commit()
    await db.refresh(task)

    return task

async def archive_task(db: db_session, task_uuid: UUID, user: UserOut):
    task = await get_task(db, task_uuid, user)

    task.is_archived = True

    await db.commit()
    await db.refresh(task)

    return task



# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/tasks")
async def read_tasks(
    db: db_session,
    token: str = Depends(oauth2_scheme),

    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    completed: bool | None = None,
    today: bool = False,
    overdue: bool = False,
    search: str | None = None,
    archived: bool = False,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await get_tasks(
        db,
        user,
        status=status,
        priority=priority,
        completed=completed,
        today=today,
        overdue=overdue,
        search=search,
        archived=archived,
        page=page,
        per_page=per_page,
    )


@app.get("/tasks/{task_uuid}", response_model=TaskDetail)
async def read_task(
    db: db_session,
    task_uuid: UUID = Path(..., description="Task UUID"),
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await get_task(db, task_uuid, user)


@app.post("/tasks", response_model=TaskDetail)
async def add_task(
    task: TaskCreate,
    db: db_session,
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await create_task(db, task, user)


@app.patch("/tasks/{task_uuid}")
async def edit_task(
    task_uuid: UUID,
    task: TaskUpdate,
    db: db_session,
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await update_task(db, task_uuid, task, user)


@app.delete("/tasks/{task_uuid}")
async def remove_task(
    db: db_session,
    task_uuid: UUID = Path(..., description="Task UUID"),
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await delete_task(db, task_uuid, user)

@app.patch("/tasks/{task_uuid}/complete", response_model=TaskDetail)
async def mark_complete(
    task_uuid: UUID,
    db: db_session,
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await complete_task(db, task_uuid, user)

@app.patch("/tasks/{task_uuid}/uncomplete", response_model=TaskDetail)
async def mark_uncomplete(
    task_uuid: UUID,
    db: db_session,
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await uncomplete_task(db, task_uuid, user)

@app.patch("/tasks/{task_uuid}/archive", response_model=TaskDetail)
async def archive(
    task_uuid: UUID,
    db: db_session,
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await archive_task(db, task_uuid, user)