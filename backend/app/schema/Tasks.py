from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ---------- Create ----------

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None


# ---------- Update ----------

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None


# ---------- Summary (for GET /tasks) ----------

class TaskSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: TaskStatus
    priority: TaskPriority
    completed: bool
    due_date: Optional[datetime] = None
    created_at: datetime


# ---------- Detail (for GET /tasks/{id}) ----------

class TaskDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None

    status: TaskStatus
    priority: TaskPriority

    completed: bool

    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    position: int
    is_archived: bool

    created_at: datetime
    updated_at: datetime

    user_id: int


# ---------- Bulk Delete ----------

class BulkDeleteTasks(BaseModel):
    ids: list[int]


# ---------- Reorder ----------

class TaskOrder(BaseModel):
    id: int
    position: int


class TaskReorder(BaseModel):
    tasks: list[TaskOrder]