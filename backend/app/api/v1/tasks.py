from datetime import datetime, timezone
from sqlalchemy import select, or_

from fastapi import HTTPException, Path, Depends, APIRouter

from core.dependencies import db_session
from core.config import oauth2_scheme
from services.auth import get_current_user

from models.tasks import Task,TaskPriority,TaskStatus

from typing import List

from schema.UserAndThought import UserOut
from schema.Tasks import (
    TaskCreate,
    TaskDetail,
    TaskSummary,
    TaskUpdate,
)

app = APIRouter()


# ------------------------------------------------------------------
# Service Functions
# ------------------------------------------------------------------

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
):
    query = select(Task).where(
        Task.user_id == user.id,
        Task.is_archived == archived,
    )

    if status:
        query = query.where(Task.status == status)

    if priority:
        query = query.where(Task.priority == priority)

    if completed is not None:
        if completed:
            query = query.where(Task.status == TaskStatus.COMPLETED)
        else:
            query = query.where(Task.status != TaskStatus.COMPLETED)

    if today:
        today_date = datetime.now(timezone.utc).date()
        query = query.where(Task.due_date.is_not(None))
        query = query.where(Task.due_date >= datetime.combine(today_date, datetime.min.time(), tzinfo=timezone.utc))
        query = query.where(Task.due_date < datetime.combine(today_date, datetime.max.time(), tzinfo=timezone.utc))

    if overdue:
        query = query.where(
            Task.due_date.is_not(None),
            Task.due_date < datetime.now(timezone.utc),
            Task.status != TaskStatus.COMPLETED,
        )

    if search:
        query = query.where(
            or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(Task.position.asc())

    result = await db.execute(query)

    return result.scalars().all()


async def get_task(db: db_session, task_id: int, user: UserOut):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == user.id,
        )
    )

    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with id {task_id} not found."
        )

    return task


async def create_task(
    db: db_session,
    task_data: TaskCreate,
    user: UserOut,
):
    task = Task(
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        due_date=task_data.due_date,
        reminder_at=task_data.reminder_at,
        user_id=user.id,
    )

    db.add(task)

    await db.commit()
    await db.refresh(task)

    return task


async def update_task(
    db: db_session,
    task_id: int,
    task_data: TaskUpdate,
    user: UserOut,
):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == user.id,
        )
    )

    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with id {task_id} not found."
        )

    updates = task_data.model_dump(exclude_unset=True)

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
    task_id: int,
    user: UserOut,
):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == user.id,
        )
    )

    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with id {task_id} not found."
        )

    await db.delete(task)
    await db.commit()

    return {
        "message": "Task deleted successfully."
    }

async def complete_task(db: db_session, task_id: int, user: UserOut):
    task = await get_task(db, task_id, user)

    task.status = TaskStatus.COMPLETED
    task.completed = True
    task.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)

    return task

async def uncomplete_task(db: db_session, task_id: int, user: UserOut):
    task = await get_task(db, task_id, user)

    task.status = TaskStatus.TODO
    task.completed = False
    task.completed_at = None

    await db.commit()
    await db.refresh(task)

    return task

async def archive_task(db: db_session, task_id: int, user: UserOut):
    task = await get_task(db, task_id, user)

    task.is_archived = True

    await db.commit()
    await db.refresh(task)

    return task



# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/tasks", response_model=List[TaskSummary])
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
    )


@app.get("/tasks/{id}", response_model=TaskDetail)
async def read_task(
    db: db_session,
    id: int = Path(..., description="Task ID"),
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await get_task(db, id, user)


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


@app.patch("/tasks/{id}")
async def edit_task(
    id: int,
    task: TaskUpdate,
    db: db_session,
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await update_task(db, id, task, user)


@app.delete("/tasks/{id}")
async def remove_task(
    db: db_session,
    id: int = Path(..., description="Task ID"),
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await delete_task(db, id, user)

@app.patch("/tasks/{id}/complete", response_model=TaskDetail)
async def mark_complete(
    id: int,
    db: db_session,
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await complete_task(db, id, user)

@app.patch("/tasks/{id}/uncomplete", response_model=TaskDetail)
async def mark_uncomplete(
    id: int,
    db: db_session,
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await uncomplete_task(db, id, user)

@app.patch("/tasks/{id}/archive", response_model=TaskDetail)
async def archive(
    id: int,
    db: db_session,
    token: str = Depends(oauth2_scheme),
):
    user = await get_current_user(db, token)

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")

    return await archive_task(db, id, user)